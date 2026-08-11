from __future__ import annotations

from collections import Counter
from datetime import datetime

from common import ROOT, load_settings, now_iso, read_json, write_json


def main() -> None:
    settings = load_settings()
    cache = ROOT / settings["cache_dir"]
    updates = read_json(cache / "updates.json", {"updates": []})["updates"]
    groups = read_json(cache / "classified_orders.json", {"groups": []})["groups"]
    counts = Counter(item.get("status") for item in updates)
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = ROOT / settings["reports_dir"] / f"{today}.md"
    lines = [
        f"# Daily Order Sync Report - {today}",
        "",
        f"Conversation groups reviewed: {len(groups)}",
        f"Rows changed or created: {len(updates)}",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- {status}: {count}")
    lines += ["", "## Updates", ""]
    for item in updates:
        project_id = item.get("project_id") or "Project ID missing"
        lines.append(f"- {project_id}: {item['type']} row {item['row']}: {item['status']} ({item['confidence']}%)")
    report_path.write_text("\n".join(lines) + "\n")

    state_path = ROOT / settings["sync_state"]
    state = read_json(state_path, {})
    state["last_successful_sync"] = now_iso()
    state["last_report"] = str(report_path.relative_to(ROOT))
    write_json(state_path, state)


if __name__ == "__main__":
    main()
