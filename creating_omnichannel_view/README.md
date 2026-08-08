# Omnichannel Customer View — SQL Graph Matching

Companion files for *Analytics Playbook — Issue 07 — Building an Omnichannel Customer View With SQL Graph Matching*.

This folder shows how to resolve customer records scattered across a CRM (loyalty) export, an online orders table, and a POS (till) feed into one canonical `customer_360` view, using graph matching instead of a hand-maintained mapping file or a single hard-coded "best" identifier.

## Files

| File | Description |
|---|---|
| `omnichannel.sql` | The full annotated query. Written for T-SQL; portable to Postgres/Snowflake/BigQuery with the dialect notes called out inline (`STRING_AGG`, `STRING_SPLIT`, `RIGHT`/`LEFT` padding). |
| `crm_data.csv` | 11 loyalty records. Columns: `loyalty_id, first_name, last_name, email, phone, address, city, postcode, country, date_of_birth, signup_channel, signup_date, email_consent, sms_consent`. |
| `online_order_data.csv` | 12 online order records. Columns: `customer_id, first_name, last_name, email, phone, address, city, postcode, country, accepts_marketing, loyalty_id, total_orders, total_spent_gbp, created_at, tags`. |
| `instore_pos_data.csv` | 11 POS transactions (10 sales, 1 return). Columns: `transaction_id, store_location, transaction_date, first_name, last_name, email, phone, loyalty_id, staff_discount, transaction_type, amount_gbp, order_reference`. |

Running the query against these three files resolves 34 raw rows into **16 canonical customers**: 6 Omnichannel, 6 Online only, 4 In-store only.

## How the query works

The core idea: every record from every source is a **node**. Two nodes get an **edge** between them if they share a non-null `loyalty_id`, `email`, or `phone` (after normalisation). A recursive CTE finds **connected components** — groups of nodes transitively linked by shared edges — and each component becomes one canonical customer. This is what lets a chain of matches (A↔B via email, B↔C via phone) merge A, B and C together even when A and C share nothing directly.

The query is built as a sequence of CTEs:

1. **`stg_online` / `stg_pos_raw` / `stg_crm`** — normalise each source: email lowercased and trimmed, phone stripped of spaces/dashes/`+`, blank-string `loyalty_id` converted to a real `NULL`.
2. **`pos_return_fix`** — a return transaction often has no identity fields captured at the till. This step finds the original sale sharing the same `order_reference` and backfills the return's identity from it, so it can still be matched and correctly net off against the sale.
3. **`stg_pos`** — unions the non-return sales with the identity-repaired returns.
4. **`all_records`** — stacks CRM, online, and POS into one list, keeping only the four columns needed to decide who matches whom.
5. **`edges_loyalty` / `edges_email` / `edges_phone` / `all_edges` / `edges_bidirectional`** — self-joins that draw an edge between any two records sharing a non-null key.
6. **`component_paths`** (recursive) / **`canonical_map`** — every record starts out reaching only itself; the recursive step follows edges outward. `MIN(reachable_id)` gives every record in the same group an identical "root" value.
7. **`canonical_ids`** / **`record_to_canonical`** — turns the (arbitrary-looking) component root into a clean, sequential `omni_lookup_id` like `OID-00001` via `DENSE_RANK()`.
8. **`match_quality`** — counts distinct emails and phones per canonical group, so a merge with conflicting contact details gets flagged for review instead of silently trusted.
9. **`all_records_detail` / `best_fields`** — picks the best-available name/contact details per customer, using `source_priority` (CRM = 1, online = 2, POS = 3) — CRM is treated as the identity master.
10. **`online_activity` / `instore_activity` / `source_crosswalk`** — rolls up spend and order counts per canonical customer, and keeps an auditable list of every native source record ID that was matched into it.
11. **Final `SELECT`** — one row per canonical customer, with `channel_segment` (Omnichannel / Online only / In-store only / Unknown), `segment_flag` (wholesale tags → "Possible corporate/bulk — review", `staff_discount = Yes` → "Staff purchase"), and `match_confidence` ("OK" or "Review: conflicting contact details across matched records").

A second query at the bottom of the file (**Part 2: ID crosswalk**) explodes `matched_source_record_ids` back out into a lookup table mapping each `omni_lookup_id` to its native `loyalty_id`, `online_customer_id`, and every matched `pos_transaction_id` — the table any downstream system uses to answer "which POS transactions belong to this customer" without re-running the matching logic.

## Worked examples from the dummy data

**Same loyalty_id, different people — Ryan Cooper / "Megan Hughes" (`L10008`).**
Ryan Cooper's CRM and online records both use phone `+447900332211`. POS transaction `T20006` is rung up under the name "Megan Hughes," phone `+447855667788` — but carries loyalty_id `L10008`. The shared loyalty_id is enough evidence to merge the transaction into Ryan's canonical customer, but `match_quality` counts two distinct phone numbers in the group, so `match_confidence` comes back `"Review: conflicting contact details across matched records"` instead of passing silently.

**Bridged by phone alone, not loyalty_id — Jane Smith.**
Jane's CRM (`L10005`, email `jane.s.1990@hotmail.com`) and POS (`T20005`, same loyalty_id and email) match directly. Her online order record (`7451201045`) has **no loyalty_id at all** and a **different** email (`jane.smith84@gmail.com`) — but the same phone number, `+447744556677`, appears on all three. The phone edge alone is what pulls her online record into the same canonical customer. A naive "pick the best single key" approach — loyalty_id if present, else email — would never have connected this record, because her CRM/POS "best key" is a loyalty_id her online record doesn't have.

**Online only — Daniel Wright, Charlotte Evans, Bright Futures Ltd, Grace Thompson.**
Daniel Wright has a CRM record and an online order (both loyalty_id `L10002`) but zero POS transactions — `channel_segment = 'Online only'`. Charlotte Evans and Grace Thompson exist only in `online_order_data.csv`, with no CRM or POS match at all — proof that a single-source customer still gets its own `omni_lookup_id`, not a phantom "no match" row. Bright Futures Ltd is also online-only, and its `wholesale` tag trips the `segment_flag = 'Possible corporate/bulk — review'` rule.

**In-store only — Priya Patel, Sarah Jenkins, Tom Harris.**
Priya Patel has a CRM record and a POS sale (`T20002`) but no online order — `channel_segment = 'In-store only'`. Sarah Jenkins (`T20009`) exists only in the POS file, with `staff_discount = Yes`, so she's also flagged `segment_flag = 'Staff purchase'`. Tom Harris (`T20011`) has no name, email, phone, or loyalty_id captured at all on his POS row — he has no shared key with anything, so he correctly stays an unmatched singleton with his own `omni_lookup_id`.

**Same address, correctly NOT matched — Olivia & Sophie Bennett.**
Both live at `18 Fairview Terrace, Glasgow, G1 2AB`, but have completely different `loyalty_id`, `email`, and `phone`. Address is deliberately never used as a matching key, so they correctly stay two separate customers — merging on address would falsely combine roommates, couples, or family members who happen to share a home.

**Return transaction, identity backfilled — Liam O'Connor.**
POS return `T20004` (`−£89.00`) arrives with every identity field blank, but shares `order_reference = 'RCT-90112'` with the original sale `T20003` (`+£89.00`, Liam O'Connor). `pos_return_fix` backfills the return's identity from the sale before matching runs, so the return correctly nets into Liam's canonical customer instead of becoming an untraceable orphan row — his net in-store spend for that item is £0, not a phantom −£89.00 from nowhere.

## Common mistakes this design avoids

- **Picking one "best" key instead of matching on all of them** — breaks on Jane Smith's data, since her online "best key" (email) and her CRM "best key" (loyalty_id) are different strings.
- **Matching on raw, un-normalised fields** — an un-stripped `+44 7911 223344` vs `07911223344` fails to match even though they're the same number.
- **Trusting every merge silently** — the Ryan/Megan case shows why a distinct-emails/distinct-phones check per group matters.
- **Using address as a person-level matching key** — the Bennett sisters show why it produces false positives.
- **Losing identity on returns/refunds** — without `pos_return_fix`, Liam's return becomes an orphan instead of netting correctly.
- **Treating this as a one-off script** — at production scale, this logic should live as tested, version-controlled dbt models (`stg_online`, `stg_pos`, `stg_crm` → `int_customer_edges` → `int_customer_components` → `customer_360`), with tests like "no duplicate `omni_lookup_id` per source record" as a standing data-quality gate.

## Notes on scale

This is exact-match graph matching, appropriate for a clean practice dataset. A production version at real scale would likely add fuzzy/probabilistic matching (e.g. a tool like Splink) for near-duplicate names, typos, and partial address matches — the graph-matching structure here is the foundation that approach builds on top of, not a replacement for it.
