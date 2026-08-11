# Order Matching

The agent should treat one customer project as one order.

Important exception: the same sign company can have multiple unrelated end-customer projects. Different projects from the same sign company are separate orders unless the project name, address, invoice number, or project number clearly indicates they are the same job.

The permanent `Project ID` is the primary key. Project names and subjects may change; the `Project ID` must not.

## Match Signals

Strong signals, in priority order:

1. Existing `Project ID`.
2. Same project name.
3. Same customer email plus another project-specific signal.
4. Same customer name plus another project-specific signal.
5. Same company name plus another project-specific signal.
6. Same design type plus another project-specific signal.
7. Same address or project location.
8. Same email thread.
9. Similar subject line.

Very strong direct signals:

- Same invoice number.
- Same project number.
- Same exact project address.

Weak signals:

- Similar subject line.
- Similar contact name.
- Similar city or landlord.
- Same sign company email without a matching end-customer project.

## Matching Policy

1. Match by existing `Project ID` if present.
2. Match by invoice number if available.
3. Match by project number if available.
4. Match by project/business name.
5. Match by email + project/business name.
6. Match by address.
7. If only weak signals exist, mark as a new candidate for review instead of merging.

For trade partners and sign companies, never merge solely because the sender email is the same. Require a shared project name, address, invoice number, or project number.

## Safety Rules

- Never create duplicate orders when a reliable match exists.
- Never create a new `Project ID` when the email belongs to an existing project.
- Never overwrite manually entered notes.
- Preserve existing status history.
- If conflicting information exists, keep the existing value and add a review note.
