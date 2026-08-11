# Project ID And Design Type Rules

## Permanent Project ID

Every real-world project must have one permanent `Project ID` that never changes.

The `Project ID` is the primary identifier for matching, updating, merging, and reporting orders. It must remain constant even when the project name, email subject, customer contact, status, or design revisions change.

### Format

Use:

```text
YYYY-NNNN
```

Examples:

- `2026-0001`
- `2026-0002`
- `2026-0145`

### Generation Rules

- Generate a `Project ID` only once, when a new project is first created.
- Never regenerate an existing `Project ID`.
- Never reuse an old `Project ID`.
- Never change a `Project ID` because the project name changes.
- Every spreadsheet row must have exactly one `Project ID`.
- Every Daily Report, Decision Log, and GitHub update must reference the `Project ID`.

### Merge Rules

When a new email belongs to an existing project, reuse the existing `Project ID`.

If multiple email threads describe the same real-world project, merge them under the existing `Project ID`.

Example:

```text
Jimmy John's Sign Design
RE: Permit
FW: City Comments
Production Update
Installation Schedule

Project ID: 2026-0034
```

Do not create `2026-0035` for the same project.

### Matching Priority

When matching a new email to an existing order, use this priority:

1. Existing `Project ID`
2. Existing `Project Name`
3. Customer Email
4. Customer Name
5. Company Name
6. Design Type
7. Project Location
8. Email Thread
9. Subject Similarity

Only create a new `Project ID` if no reliable match exists.

### Lifecycle

The status changes through the project lifecycle. The `Project ID` does not.

Valid statuses:

- Awaiting Estimate
- Estimate
- Design
- Permit
- Production
- Installation
- Payment Awaiting
- Completed
- Withdraw

## Design Type

`Design Type` describes what is being produced, not who the customer is.

Every order should have one primary standardized `Design Type`.

### Controlled Vocabulary

Use these standard terms unless a new repeated category is manually approved:

- Storefront Sign
- Channel Letters
- Window Graphics
- Monument Sign
- Lobby Sign
- Wayfinding
- Vinyl Graphics
- Cabinet Sign
- Pylon Sign
- ADA Signage
- Awning
- Blade Sign
- Canopy
- Menu Board
- LED Retrofit
- Unknown / Review

### Normalization Rules

Before saving `Design Type`:

- Convert synonyms into the standardized vocabulary.
- Ignore capitalization differences.
- Ignore plural/singular differences.
- Do not include customer name, location, status, or email subject.

Examples:

- `window decal` -> `Window Graphics`
- `3d metal letters` -> `Channel Letters`
- `front building signage` -> `Storefront Sign`
- `vinyl decals` -> `Vinyl Graphics`

### Multiple Products

If a project contains multiple products, assign the primary `Design Type` and record additional products in `Notes`.

Example:

```text
Design Type: Storefront Sign
Notes: Includes Window Graphics, Door Vinyl, Interior Lobby Sign.
```

### Future Learning

If a new `Design Type` appears repeatedly and cannot be mapped to an existing category, flag it for review instead of creating a new category automatically.

## Golden Rule

One real-world project = one permanent `Project ID`.

One project should have one primary `Design Type`.

Project names may change. Email subjects may change. Statuses may change.

The `Project ID` never changes.
