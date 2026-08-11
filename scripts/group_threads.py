from __future__ import annotations

from collections import defaultdict
from email.utils import parseaddr
import re

from common import ROOT, extract_project_id, load_settings, norm, normalize_design_type, read_json, write_json


OUR_DOMAINS = {"topchannelletters.com"}
OUR_EMAILS = {"topchannelletters@gmail.com", "sales@topchannelletters.com"}
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


def external_email(message: dict) -> str:
    for field in ["from", "to", "cc"]:
        for raw in (message.get(field) or "").split(","):
            _name, email = parseaddr(raw)
            email = email.lower()
            if email and email not in OUR_EMAILS and email.split("@")[-1] not in OUR_DOMAINS:
                return email
    return ""


def infer_project(messages: list[dict]) -> str:
    subjects = " ".join(m.get("subject", "") for m in messages)
    body = " ".join(m.get("body", "") for m in messages)
    clean = re.sub(r"^(re|fw|fwd):\s*", "", subjects, flags=re.I).strip()
    clean = re.sub(r"^\(?\s*(estimate|quote|rfq|pricing|request for quote|get a quote)\s*[:\\-]?\s*", "", clean, flags=re.I).strip()
    if norm(clean) in GENERIC_PROJECT_NAMES or len(clean) < 3:
        quoted = re.findall(r"[\"“”']([A-Za-z0-9][A-Za-z0-9 &'.\\-]{2,50})[\"“”']", body)
        if quoted:
            return quoted[0].strip()[:120]
        product = normalize_design_type(subjects + " " + body)
        return product if product != "Unknown / Review" else "Uncertain Project"
    return clean[:120] or "Uncertain Project"


def main() -> None:
    settings = load_settings()
    cache = ROOT / settings["cache_dir"]
    data = read_json(cache / "emails.json", {"messages": []})
    by_thread = defaultdict(list)
    for msg in data["messages"]:
        by_thread[msg["thread_id"]].append(msg)

    grouped = []
    for thread_id, messages in by_thread.items():
        messages = sorted(messages, key=lambda m: m.get("date", ""))
        email = external_email(messages[-1]) or external_email(messages[0])
        if not email:
            continue
        project = infer_project(messages)
        combined_text = " ".join((m.get("subject", "") + " " + m.get("body", "")) for m in messages)
        grouped.append(
            {
                "thread_id": thread_id,
                "customer_email": email,
                "project_key": norm(email + " " + project),
                "project_id": extract_project_id(combined_text),
                "project": project,
                "design_type": normalize_design_type(combined_text + " " + project),
                "match_text": norm(combined_text + " " + project + " " + email),
                "messages": messages,
                "latest_message": messages[-1],
            }
        )
    write_json(cache / "grouped_threads.json", {"groups": grouped})


if __name__ == "__main__":
    main()
