from __future__ import annotations

from common import ROOT, contains_any, load_settings, read_json, write_json


ESTIMATE_TERMS = ["estimate", "quote", "quotation", "pricing", "price", "rfq", "request for quote", "inquiry"]
PRICE_SENT_TERMS = ["estimate price", "$", "total:", "price is", "quoted", "quote is", "pricing is"]
PROGRESS_TERMS = ["approved", "approve", "go ahead", "proceed", "deposit", "payment received", "production file", "permit submitted", "scheduled install"]

RULES = [
    ("Withdraw", ["cancel", "cancelled", "rejected", "abandoned"]),
    ("Completed", ["completed", "installed", "finished", "final inspection passed", "payment received"]),
    ("Payment Awaiting", ["invoice", "payment request", "deposit", "final payment", "overdue"]),
    ("Estimate", ESTIMATE_TERMS),
    ("Awaiting Estimate", ESTIMATE_TERMS),
    ("Installation", ["install", "installation", "scheduled", "crew"]),
    ("Production", ["production", "fabrication", "materials ordered", "trim cap", "return", "ul sticker"]),
    ("Permit", ["permit", "landlord approval", "city approval", "contractor registration", "coi", "bond"]),
    ("Design", ["rendering", "mockup", "artwork", "drawing", "revision", "logo"]),
]


def classify(text: str) -> tuple[str, int, list[str]]:
    low = text.lower()
    estimate_matches = [term for term in ESTIMATE_TERMS if term in low]
    price_sent_matches = [term for term in PRICE_SENT_TERMS if term in low]
    progress_matches = [term for term in PROGRESS_TERMS if term in low]
    if estimate_matches and not progress_matches:
        if not price_sent_matches:
            return "Awaiting Estimate", min(95, 80 + len(estimate_matches) * 5), estimate_matches
        confidence = min(95, 80 + len(estimate_matches) * 5)
        return "Estimate", confidence, estimate_matches
    for status, terms in RULES:
        matched = [term for term in terms if term in low]
        if matched:
            confidence = min(95, 75 + len(matched) * 5)
            return status, confidence, matched
    return "Estimate", 50, []


def main() -> None:
    settings = load_settings()
    cache = ROOT / settings["cache_dir"]
    groups = read_json(cache / "matched_orders.json", {"groups": []})["groups"]
    for group in groups:
        text = " ".join(m.get("subject", "") + " " + m.get("body", "") for m in group["messages"][-5:])
        status, confidence, terms = classify(text)
        group["suggested_status"] = status
        group["status_confidence"] = confidence
        group["evidence_terms"] = terms
    write_json(cache / "classified_orders.json", {"groups": groups})


if __name__ == "__main__":
    main()
