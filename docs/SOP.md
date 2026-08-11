# Daily Order Sync SOP

1. Read `data/sync_state.json`.
2. Fetch Gmail messages after `last_successful_sync`.
3. Filter spam, newsletters, automated notifications, ads, and unrelated mail.
4. Group messages by customer + project + thread.
5. Match grouped conversations to rows in `data/orders.xlsx`.
6. Determine the latest confirmed status using all historical order data and new email evidence.
7. Update changed status, last activity, and notes.
8. Create new order rows only when no reliable match exists.
9. Generate a Markdown report in `reports/`.
10. Save updated `sync_state.json`.
11. Commit changes.

Stop and flag for manual review when confidence is below 80%.
