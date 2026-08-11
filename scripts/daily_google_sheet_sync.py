#!/usr/bin/env python3
"""Incrementally sync new Gmail project conversations into the live Google Sheet."""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import subprocess
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

from common import ROOT, load_settings, norm, now_iso, read_json, write_json


OUR_EMAILS = {
    "topchannelletters@gmail.com",
    "topchannellettersorders@gmail.com",
    "sales@topchannelletters.com",
    "topchannelletters@topchannelletters.com",
    "info.qaprints@gmail.com",
    "job.qaprints@gmail.com",
}

NOISE_SENDERS = [
    "mailer-daemon",
    "noreply",
    "no-reply",
    "notification",
    "news@",
    "marketing@",
    "google",
    "brevo",
    "cloudhq",
    "adobesign",
    "southloopchamberofcommerce.com",
    "building@",
    "buildinginspections@",
    "cityof",
    "karstensfinancial.com",
]

NOISE_SUBJECTS = [
    "delivery status notification",
    "security alert",
    "campaign",
    "api key",
    "welcome to",
    "newsletter",
    "cid test",
    "automatic reply",
    "open invoices are over due",
    "contractor registration",
    "coi",
    "bond",
    "copied you on",
    "sign permit applicaiton question",
    "sign permit application question",
    "midwest film festival",
]

PROMO_SUBJECTS = [
    "channel letter fabrication support in chicago",
    "wholesale channel letters from top channel letters",
    "wholesale channel letters",
]

PROJECT_HINTS = [
    "quote",
    "estimate",
    "pricing",
    "price",
    "install",
    "drawing",
    "artwork",
    "measurement",
    "dimensions",
    "permit",
    "project",
    "rfq",
    "rendering",
    "sign",
    "channel",
    "awning",
    "vinyl",
    "monument",
]

ESTIMATE_TERMS = ["estimate", "quote", "quotation", "pricing", "price", "rfq", "request for quote", "inquiry"]
PRICE_SENT_TERMS = ["estimate price", "$", "total:", "price is", "quoted", "quote is", "pricing is"]
PROGRESS_TERMS = ["approved", "approve", "go ahead", "proceed", "deposit", "payment received", "production file", "permit submitted", "scheduled install"]

STATUS_RULES = [
    ("Withdraw", ["cancel", "cancelled", "rejected", "give it to the other vendor", "could not handle", "can't handle"]),
    ("Completed", ["completed", "certificate of completion", "final inspection", "installed", "installation complete", "finished", "完工"]),
    ("Payment Awaiting", ["invoice", "payment request", "open invoices", "over due", "final payment", "deposit"]),
    ("Production", ["production file", "sign production", "materials ordered", "ul sticker", "disconnect switch"]),
    ("Permit", ["permit", "landlord approval", "building department", "city approval", "contractor registration", "coi", "bond"]),
    ("Design", ["revision", "approval drawing", "final artwork", "mockup", "rendering"]),
]

GENERIC_PROJECT_NAMES = {
    "inquiry",
    "get a quote",
    "request for quote",
    "quote",
    "estimate",
    "pricing",
    "rfq",
    "follow up",
    "wholesale channel letters from top channel letters",
    "channel letter fabrication support in chicago",
}

FURTHEST = {
    "Awaiting Estimate": 0,
    "Estimate": 1,
    "Design": 2,
    "Permit": 3,
    "Production": 4,
    "Installtion": 5,
    "Installation": 5,
    "Payment Awaiting": 6,
    "Completed": 7,
    "Withdraw": 99,
}

MONTH_MARKERS = [
    ("January", "一月"),
    ("February", "二月"),
    ("March", "三月"),
    ("April", "四月"),
    ("May", "五月"),
    ("June", "六月"),
    ("July", "七月"),
    ("August", "八月"),
    ("September", "九月"),
    ("October", "十月"),
    ("November", "十一月"),
    ("December", "十二月"),
]


def resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    return p if p.is_absolute() else ROOT / p


def curl_json(args: list[str]) -> dict:
    proc = subprocess.run(args, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"curl failed: {proc.returncode}")
    if not proc.stdout.strip():
        return {}
    return json.loads(proc.stdout)


def load_client(settings: dict) -> dict:
    data = json.loads(resolve_path(settings["gmail"]["client_secret_file"]).read_text())
    return data.get("installed") or data.get("web") or data


def access_token(settings: dict, token_file: Path) -> str:
    token = json.loads(token_file.read_text())
    refresh = token.get("refresh_token")
    if not refresh:
        return token["access_token"]
    client = load_client(settings)
    body = urllib.parse.urlencode(
        {
            "client_id": client["client_id"],
            "client_secret": client.get("client_secret", ""),
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        }
    )
    refreshed = curl_json(
        [
            "curl",
            "-sS",
            "-X",
            "POST",
            "-H",
            "Content-Type: application/x-www-form-urlencoded",
            "--data",
            body,
            client.get("token_uri", "https://oauth2.googleapis.com/token"),
        ]
    )
    token.update(refreshed)
    token_file.write_text(json.dumps(token, indent=2))
    token_file.chmod(0o600)
    return token["access_token"]


def google_get(settings: dict, token_file: Path, url: str, params: dict | None = None) -> dict:
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    return curl_json(["curl", "-sS", "-H", f"Authorization: Bearer {access_token(settings, token_file)}", url])


def google_post(settings: dict, token_file: Path, url: str, payload: dict) -> dict:
    return curl_json(
        [
            "curl",
            "-sS",
            "-X",
            "POST",
            "-H",
            f"Authorization: Bearer {access_token(settings, token_file)}",
            "-H",
            "Content-Type: application/json",
            "--data",
            json.dumps(payload),
            url,
        ]
    )


def gmail_get(settings: dict, token_file: Path, path: str, params: dict | None = None) -> dict:
    return google_get(settings, token_file, "https://gmail.googleapis.com/gmail/v1/users/me/" + path, params)


def sheets_get(settings: dict, path: str, params: dict | None = None) -> dict:
    token_file = resolve_path(settings["gmail"]["accounts"][0]["token_file"])
    return google_get(settings, token_file, "https://sheets.googleapis.com/v4/spreadsheets/" + path, params)


def sheets_post(settings: dict, path: str, payload: dict) -> dict:
    token_file = resolve_path(settings["gmail"]["accounts"][0]["token_file"])
    return google_post(settings, token_file, "https://sheets.googleapis.com/v4/spreadsheets/" + path, payload)


def header(headers: list[dict], name: str) -> str:
    for item in headers:
        if item.get("name", "").lower() == name.lower():
            return item.get("value", "")
    return ""


def parse_email(value: str) -> tuple[str, str]:
    name, email = parseaddr(value or "")
    return name.strip().strip('"'), email.strip().lower()


def parse_gmail_date(value: str) -> datetime:
    try:
        return parsedate_to_datetime(value).astimezone()
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def local_date(value: str) -> str:
    dt = parse_gmail_date(value)
    if dt.year < 2000:
        return value or ""
    return dt.strftime("%Y-%m-%d %H:%M %Z")


def walk_parts(part: dict):
    children = part.get("parts", []) or []
    if children:
        for child in children:
            yield from walk_parts(child)
    else:
        yield part


def body_text(msg: dict, limit: int = 1600) -> str:
    chunks = []
    for part in walk_parts(msg.get("payload", {})):
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if not data or mime not in {"text/plain", "text/html"}:
            continue
        try:
            text = base64.urlsafe_b64decode(data + "=" * ((4 - len(data) % 4) % 4)).decode("utf-8", "ignore")
        except Exception:
            continue
        if mime == "text/html":
            text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = html.unescape(text)
        chunks.append(text)
    return re.sub(r"\s+", " ", "\n".join(chunks)).strip()[:limit]


def clean_subject(subject: str) -> str:
    clean = re.sub(r"^(re|fw|fwd):\s*", "", subject or "", flags=re.I).strip()
    return re.sub(r"^\(?\s*(estimate|quote|rfq|pricing|request for quote|get a quote|inquiry)\s*[:\-]?\s*", "", clean, flags=re.I).strip()


def is_noise(headers: list[dict]) -> bool:
    sender = header(headers, "From").lower()
    subject = header(headers, "Subject").lower()
    return any(x in sender for x in NOISE_SENDERS) or any(x in subject for x in NOISE_SUBJECTS)


def is_admin_only(subject: str, text: str, sender: str) -> bool:
    blob = f"{subject} {text} {sender}".lower()
    admin_terms = [
        "automatic reply",
        "contractor registration",
        "coi",
        "certificate of insurance",
        " bond",
        "bond needed",
        "open invoices are over due",
        "copied you on",
        "adobesign",
        "delivery status notification",
        "sign permit applicaiton question",
        "sign permit application question",
        "midwest film festival",
    ]
    return any(term in blob for term in admin_terms)


def is_promo_subject(subject: str) -> bool:
    low = clean_subject(subject).lower()
    return any(part in low for part in PROMO_SUBJECTS)


def has_project_hint(text: str) -> bool:
    low = text.lower()
    return any(hint in low for hint in PROJECT_HINTS)


def external_people(messages: list[dict]) -> dict[str, str]:
    people = {}
    for msg in messages:
        headers = msg.get("payload", {}).get("headers", [])
        for field in ["From", "To", "Cc"]:
            raw = header(headers, field)
            for part in raw.split(","):
                name, email = parse_email(part)
                if email and email not in OUR_EMAILS and "@" in email:
                    people[email] = name
    return people


def infer_status(text: str) -> tuple[str, list[str], int]:
    low = text.lower()
    if "completed sign permit application" in low or "sign permit application" in low:
        return "Permit", ["sign permit application"], 85
    estimate_matches = [term for term in ESTIMATE_TERMS if term in low]
    price_sent_matches = [term for term in PRICE_SENT_TERMS if term in low]
    progress_matches = [term for term in PROGRESS_TERMS if term in low]
    if estimate_matches and not progress_matches:
        if not price_sent_matches:
            return "Awaiting Estimate", estimate_matches, 85
        return "Estimate", estimate_matches, 85
    for status, terms in STATUS_RULES:
        matches = [term for term in terms if term in low]
        if matches:
            confidence = 80 if len(matches) == 1 else 90
            return status, matches, confidence
    return "Uncertain", [], 50


def infer_project(subject: str, text: str) -> str:
    clean = clean_subject(subject)
    if norm(clean) and norm(clean) not in GENERIC_PROJECT_NAMES and len(clean) > 2:
        return clean[:80]
    quoted = re.findall(r"[\"“”']([A-Za-z0-9][A-Za-z0-9 &'.\-]{2,50})[\"“”']", text)
    if quoted:
        return quoted[0].strip()[:80]
    for term, label in [
        ("awning", "Awning"),
        ("channel", "Channel Letters"),
        ("letter", "Channel Letters"),
        ("monument", "Monument Sign"),
        ("vinyl", "Vinyl Graphics"),
        ("window", "Window Graphics"),
    ]:
        if term in text.lower():
            return label
    return "Uncertain Project"


def extract_address(text: str) -> str:
    patterns = [
        r"\b\d{1,6}\s+[A-Za-z0-9'.\- ]+\s+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Lane|Ln|Way|Ct|Court|Hwy|US-41)[^,\n]*(?:,\s*[A-Za-z .]+,\s*[A-Z]{2}\s*\d{5})?",
        r"\b\d{1,6}\s+[A-Za-z0-9'.\- ]+,\s*[A-Za-z .]+,\s*[A-Z]{2}\s*\d{5}",
    ]
    for pat in patterns:
        m = re.search(pat, text or "", re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(0)).strip()
    return ""


def started_date(date_value: str) -> str:
    dt = parse_gmail_date(date_value)
    if dt.year < 2000:
        return ""
    return f"{dt.month}/{dt.day}"


def list_thread_ids(settings: dict, token_file: Path, query: str) -> set[str]:
    thread_ids = set()
    page = None
    while True:
        params = {"q": query, "maxResults": "100"}
        if page:
            params["pageToken"] = page
        data = gmail_get(settings, token_file, "messages", params)
        for msg in data.get("messages", []):
            if msg.get("threadId"):
                thread_ids.add(msg["threadId"])
        page = data.get("nextPageToken")
        if not page:
            break
    return thread_ids


def gmail_query(settings: dict, state: dict) -> tuple[str, int]:
    last = state.get("last_successful_sync")
    excludes = settings["gmail"].get("query_excludes", "")
    if last:
        dt = datetime.fromisoformat(last)
        after = dt.strftime("%Y/%m/%d")
        return f"after:{after} {excludes}", int(dt.timestamp() * 1000)
    return f"newer_than:1d {excludes}", 0


def collect_records(settings: dict, state: dict) -> list[dict]:
    query, last_ms = gmail_query(settings, state)
    records = []
    for account in settings["gmail"].get("accounts", []):
        token_file = resolve_path(account["token_file"])
        for thread_id in sorted(list_thread_ids(settings, token_file, query)):
            thread = gmail_get(settings, token_file, f"threads/{thread_id}", {"format": "full"})
            messages = thread.get("messages", [])
            if not messages:
                continue
            latest = max(messages, key=lambda m: int(m.get("internalDate", "0")))
            if last_ms and int(latest.get("internalDate", "0")) <= last_ms:
                continue
            headers_list = [m.get("payload", {}).get("headers", []) for m in messages]
            if all(is_noise(h) for h in headers_list):
                continue
            people = external_people(messages)
            if not people:
                continue
            latest_headers = latest.get("payload", {}).get("headers", [])
            if is_noise(latest_headers):
                continue
            subject = header(latest_headers, "Subject")
            combined = f"{subject}\n" + "\n".join(body_text(m, 900) for m in messages[-6:])
            _sender_name, sender_email = parse_email(header(latest_headers, "From"))
            if is_admin_only(subject, combined, sender_email):
                continue
            if is_promo_subject(subject) and not has_project_hint(combined):
                continue
            status, terms, confidence = infer_status(combined)
            if status == "Uncertain":
                continue
            email = sorted(people.keys())[0]
            records.append(
                {
                    "account": account["email"],
                    "thread_id": thread_id,
                    "primary_email": email,
                    "name": people.get(email, ""),
                    "latest_date": local_date(header(latest_headers, "Date")),
                    "raw_date": header(latest_headers, "Date"),
                    "latest_subject": subject,
                    "project": infer_project(subject, combined),
                    "address": extract_address(combined),
                    "suggested_status": status,
                    "confidence": confidence,
                    "evidence_terms": terms,
                    "latest_snippet": re.sub(r"\s+", " ", body_text(latest, 700)).strip(),
                }
            )
    return records


def group_records(records: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for record in records:
        key = norm(record["primary_email"] + " " + record["project"])
        grouped[key].append(record)
    rows = []
    for _key, items in grouped.items():
        items = sorted(items, key=lambda x: x["latest_date"], reverse=True)
        rows.append(items[0])
    return sorted(rows, key=lambda x: x["latest_date"], reverse=True)


def get_sheet_values(settings: dict) -> list[list[str]]:
    gs = settings["google_sheet"]
    range_name = urllib.parse.quote(f"{gs['sheet_name']}!{gs['data_range']}", safe="")
    data = sheets_get(settings, f"{gs['spreadsheet_id']}/values/{range_name}")
    return data.get("values", [])


def row_value(row: list[str], col_1_based: int) -> str:
    idx = col_1_based - 1
    return row[idx] if idx < len(row) else ""


def match_row(item: dict, rows: list[list[str]], settings: dict) -> int | None:
    gs = settings["google_sheet"]
    target = norm(" ".join([item["primary_email"], item["project"], item.get("address", ""), item["name"]]))
    best_row = None
    best_score = 0
    month_start, month_end = current_month_bounds(rows)
    for idx in range(month_start + 1, month_end + 1):
        if idx - 1 >= len(rows):
            continue
        row = rows[idx - 1]
        business = row_value(row, gs["business_col"])
        address = row_value(row, gs["address_col"])
        email_a = row_value(row, gs["phone_col"])
        email_b = row_value(row, gs["email_col"])
        haystack = norm(" ".join(row))
        score = 0
        if norm(item["project"]) and norm(item["project"]) in haystack:
            score += 35
        if item.get("address") and norm(item["address"]) in haystack:
            score += 15
        if item["primary_email"] and item["primary_email"] in {email_a.lower(), email_b.lower()}:
            score += 55
        if business and norm(business) in target:
            score += 20
        if address and norm(address) in target:
            score += 15
        if score > best_score:
            best_row = idx
            best_score = score
    return best_row if best_score >= 35 else None


def current_month_bounds(rows: list[list[str]]) -> tuple[int, int]:
    now = datetime.now()
    month_en, month_cn = MONTH_MARKERS[now.month - 1]
    start = None
    for idx, row in enumerate(rows, start=1):
        first = row_value(row, 1).lower()
        if month_en.lower() in first or month_cn in first:
            start = idx
            break
    if start is None:
        return len(rows) + 1, len(rows) + 1
    end = len(rows)
    for idx, row in enumerate(rows[start:], start=start + 1):
        first = row_value(row, 1)
        if any(en.lower() in first.lower() or cn in first for en, cn in MONTH_MARKERS):
            end = idx - 1
            break
    last_nonempty = start
    for idx in range(start + 1, end + 1):
        if idx - 1 < len(rows) and any(rows[idx - 1]):
            last_nonempty = idx
    return start, last_nonempty


def build_memo(item: dict) -> str:
    snippet = re.sub(r"\s+", " ", item.get("latest_snippet", "")).strip()[:220]
    return f"{item['latest_date']}: {item['suggested_status']}. {item['latest_subject']}. Evidence: {snippet}"


def plan_updates(settings: dict, rows: list[list[str]], items: list[dict]) -> dict:
    gs = settings["google_sheet"]
    updates = []
    creates = []
    for item in items:
        if item["confidence"] < settings.get("minimum_confidence_for_auto_update", 80):
            continue
        row_idx = match_row(item, rows, settings)
        memo = build_memo(item)
        if row_idx:
            row = rows[row_idx - 1]
            old_status = row_value(row, gs["status_col"])
            old_memo = row_value(row, gs["memo_col"])
            status = item["suggested_status"]
            if FURTHEST.get(status, 0) < FURTHEST.get(old_status, 0) and old_status not in {"Awaiting Estimate", "Estimate"}:
                status = old_status
            values = {
                "status": status,
                "memo": (old_memo + "\n" + memo).strip() if memo not in old_memo else old_memo,
            }
            updates.append({"row": row_idx, "item": item, "values": values, "old_status": old_status})
        else:
            if item["suggested_status"] not in {"Awaiting Estimate", "Estimate"}:
                continue
            creates.append(
                [
                    item["suggested_status"],
                    "",
                    item["name"],
                    item["project"],
                    item.get("address", ""),
                    started_date(item.get("raw_date", "")),
                    "",
                    memo,
                    item["primary_email"],
                    "",
                ]
            )
    return {"updates": updates, "creates": creates}


def apply_updates(settings: dict, rows: list[list[str]], plan: dict) -> None:
    gs = settings["google_sheet"]
    spreadsheet_id = gs["spreadsheet_id"]
    sheet_name = gs["sheet_name"]
    value_ranges = []
    for update in plan["updates"]:
        row = update["row"]
        value_ranges.append({"range": f"{sheet_name}!A{row}", "values": [[update["values"]["status"]]]})
        value_ranges.append({"range": f"{sheet_name}!H{row}", "values": [[update["values"]["memo"]]]})
        # If both legacy email columns are empty, keep new data in the true Email column.
        existing = rows[row - 1]
        if not row_value(existing, gs["phone_col"]) and not row_value(existing, gs["email_col"]):
            value_ranges.append({"range": f"{sheet_name}!I{row}", "values": [[update["item"]["primary_email"]]]})
    if value_ranges:
        sheets_post(
            settings,
            f"{spreadsheet_id}/values:batchUpdate",
            {"valueInputOption": "USER_ENTERED", "data": value_ranges},
        )
    if plan["creates"]:
        _month_start, insert_after = current_month_bounds(rows)
        start_index = insert_after
        requests = [
            {
                "insertDimension": {
                    "range": {
                        "sheetId": gs["sheet_id"],
                        "dimension": "ROWS",
                        "startIndex": start_index,
                        "endIndex": start_index + len(plan["creates"]),
                    },
                    "inheritFromBefore": True,
                }
            }
        ]
        sheets_post(settings, f"{spreadsheet_id}:batchUpdate", {"requests": requests})
        first_row = insert_after + 1
        sheets_post(
            settings,
            f"{spreadsheet_id}/values:batchUpdate",
            {
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {
                        "range": f"{sheet_name}!A{first_row}:J{first_row + len(plan['creates']) - 1}",
                        "values": plan["creates"],
                    }
                ],
            },
        )


def write_report(settings: dict, items: list[dict], plan: dict, dry_run: bool) -> Path:
    reports_dir = resolve_path(settings["reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    report = reports_dir / f"{today}-google-sheet-sync.md"
    lines = [
        f"# Google Sheet Daily Sync - {today}",
        "",
        f"Dry run: {dry_run}",
        f"New conversation groups reviewed: {len(items)}",
        f"Existing rows to update: {len(plan['updates'])}",
        f"New rows to create: {len(plan['creates'])}",
        "",
        "## Existing Row Updates",
    ]
    for update in plan["updates"]:
        item = update["item"]
        lines.append(f"- Row {update['row']}: {update['old_status']} -> {update['values']['status']} | {item['project']} | {item['primary_email']}")
    lines += ["", "## New Rows"]
    for row in plan["creates"]:
        lines.append(f"- {row[0]} | {row[2]} | {row[8]}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Plan changes without writing the Google Sheet or sync timestamp.")
    args = parser.parse_args()

    settings = load_settings()
    state_path = resolve_path(settings["sync_state"])
    state = read_json(state_path, {})
    state["last_attempted_sync"] = now_iso()
    write_json(state_path, state)

    items = group_records(collect_records(settings, state))
    cache_dir = resolve_path(settings["cache_dir"])
    write_json(cache_dir / "daily-google-sheet-items.json", {"items": items, "generated_at": now_iso()})
    rows = get_sheet_values(settings)
    plan = plan_updates(settings, rows, items)
    write_json(cache_dir / "daily-google-sheet-plan.json", plan)
    if not args.dry_run:
        apply_updates(settings, rows, plan)
        state["last_successful_sync"] = now_iso()
    report = write_report(settings, items, plan, args.dry_run)
    state["last_report"] = str(report.relative_to(ROOT))
    write_json(state_path, state)
    print(json.dumps({"dry_run": args.dry_run, "groups": len(items), "updates": len(plan["updates"]), "creates": len(plan["creates"]), "report": str(report)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
