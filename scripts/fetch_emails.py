from __future__ import annotations

import base64
import html
import re
from email.utils import parsedate_to_datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from common import ROOT, load_settings, now_iso, read_json, write_json


NOISE_SUBJECTS = [
    "delivery status notification",
    "newsletter",
    "security alert",
    "campaign",
    "api key",
]


def gmail_service(settings):
    creds = Credentials.from_authorized_user_file(str(ROOT / settings["gmail"]["token_file"]))
    return build("gmail", "v1", credentials=creds)


def decode_part(part: dict) -> str:
    body = part.get("body", {})
    data = body.get("data")
    if not data:
        return ""
    text = base64.urlsafe_b64decode(data + "=" * ((4 - len(data) % 4) % 4)).decode("utf-8", "ignore")
    if part.get("mimeType") == "text/html":
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
    return text


def walk_parts(part: dict):
    children = part.get("parts", []) or []
    if children:
        for child in children:
            yield from walk_parts(child)
    else:
        yield part


def header(headers: list[dict], name: str) -> str:
    for item in headers:
        if item.get("name", "").lower() == name.lower():
            return item.get("value", "")
    return ""


def body_text(message: dict) -> str:
    chunks = []
    for part in walk_parts(message.get("payload", {})):
        if part.get("mimeType") in {"text/plain", "text/html"}:
            chunks.append(decode_part(part))
    return re.sub(r"\s+", " ", "\n".join(chunks)).strip()


def main() -> None:
    settings = load_settings()
    state_path = ROOT / settings["sync_state"]
    state = read_json(state_path, {})
    last_sync = state.get("last_successful_sync")
    query = settings["gmail"]["query_excludes"]
    if last_sync:
        date = parsedate_to_datetime(last_sync).strftime("%Y/%m/%d") if "," in last_sync else last_sync[:10].replace("-", "/")
        query = f"after:{date} {query}"
    else:
        query = f"newer_than:2d {query}"

    service = gmail_service(settings)
    user = settings["gmail"]["user_id"]
    messages = []
    page_token = None
    while True:
        resp = service.users().messages().list(userId=user, q=query, maxResults=100, pageToken=page_token).execute()
        for item in resp.get("messages", []):
            msg = service.users().messages().get(userId=user, id=item["id"], format="full").execute()
            headers = msg.get("payload", {}).get("headers", [])
            subject = header(headers, "Subject")
            if any(x in subject.lower() for x in NOISE_SUBJECTS):
                continue
            messages.append(
                {
                    "id": msg["id"],
                    "thread_id": msg["threadId"],
                    "date": header(headers, "Date"),
                    "from": header(headers, "From"),
                    "to": header(headers, "To"),
                    "cc": header(headers, "Cc"),
                    "subject": subject,
                    "snippet": msg.get("snippet", ""),
                    "body": body_text(msg)[:3000],
                    "labels": msg.get("labelIds", []),
                }
            )
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    cache = ROOT / settings["cache_dir"]
    write_json(cache / "emails.json", {"fetched_at": now_iso(), "query": query, "messages": messages})


if __name__ == "__main__":
    main()
