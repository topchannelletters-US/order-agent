# AGENTS.md

## Daily Order Synchronization Agent

**Schedule:** Every weekday at **5:00 PM (local time)** or manually via GitHub Actions.

### Workflow

1. Read only Gmail emails received/sent **after the last successful sync timestamp**.
2. Ignore spam, newsletters, automated notifications and unrelated mail.
3. Group emails by **Customer + Project + Thread**.
4. Match each conversation to an existing spreadsheet order using the permanent **Project ID** rules.
5. If a match exists, merge new information into the existing order.
6. Read historical status + today's emails and determine the newest confirmed status.
7. Update only if status changed; otherwise update Last Activity and notes.
8. Generate a Daily Report.
9. Save the latest sync timestamp.
10. Commit updated files back to GitHub.

### Statuses

Awaiting Estimate
Estimate
Design
Permit
Production
Installation
Payment Awaiting
Completed
Withdraw

Additional Flags:
- Need to Issue Invoice
- Need to Process
- Follow Up

### Rules

- Every real project must have exactly one permanent `Project ID` in `YYYY-NNNN` format.
- Never regenerate, rename, or reuse a `Project ID`.
- Project names must describe the real sign job, not the email subject or workflow label.
- Every order must have one primary standardized `Design Type`.
- Never create duplicate orders.
- Never overwrite manual notes.
- Always preserve history.
- Always cite email evidence.
- Never guess.
- Use newest confirmed information only.

See:

- `docs/PROJECT_ID_AND_DESIGN_TYPE.md`
- `docs/ORDER_NAMING_RULES.md`
- `docs/ORDER_MATCHING.md`
