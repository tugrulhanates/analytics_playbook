/* =====================================================================
   Build CUSTOMER_360 (Omnichannel view) table by using "Graph Matching"

   Matches records across online customers, instore customers (POS), and
   CRM (Loyalty) data into a single canonical customer, identified by a new
   surrogate key: omni_lookup_id.

   * Written for T-SQL syntax.
   * Portable to most modern warehouses (Snowflake, BigQuery, Postgres)
   with minor adjustments — noted inline where a function is dialect-
   specific (STRING_AGG, RIGHT/LEFT string padding).

   Matching logic: 
   ---------------
   Two records are the same customer if they share a
   non-null loyalty_id, OR a non-null email, OR a non-null phone
   number, after normalisation. 

   This is implemented as a graph:
   records are nodes, a shared key is an edge, and connected
   components (via recursive CTE) become one canonical customer —
   so a chain of matches (A~B via email, B~C via phone) still merges
   A, B and C together even though A and C share nothing directly.

   This is a simplified, exact-match version appropriate for the
   scenarios in this practice dataset. A production version at scale
   would likely add fuzzy/probabilistic matching (e.g. via a tool
   like Splink) and would live as tested, version-controlled dbt
   models rather than one ad hoc script — see the closing note.
   
   
   
   
    The approach: *GRAPH MATCHING*, not a simple priority key
    
	The naive way to do this — "pick loyalty_id if present, else email, else phone, then group by that" — actually breaks on your own data. Jane Smith's Online order record has no loyalty_id but does have an email, so its "best key" would be her email; her CRM/POS records have a loyalty_id, so their best key would be that loyalty_id. Those are different strings — a naive GROUP BY would never connect them, even though they share a phone number.
	
	So the script builds a proper graph: every record is a node, and an edge connects any two records sharing a non-null loyalty_id, email, or phone. A recursive CTE then finds connected components — groups of records transitively linked by shared edges — and each component gets one omni_lookup_id. This also future-proofs against chains (A matches B via email, B matches C via phone, so A and C merge even though they share nothing directly), which doesn't happen in this dataset but will in a real one.
	
	How it resolves each scenario:
	Jane Smith: no shared loyalty_id or email between Online order and CRM/POS, but the phone number matches → correctly merged into one customer.
	Olivia & Sophie Bennett: no shared loyalty_id, email, or phone at all (only the address, which is deliberately never used as a matching key) → correctly stay as two separate customers.
	Ryan Cooper & Megan Hughes: Megan's POS transaction carries Ryan's loyalty_id → gets merged into Ryan's record (matching by the strongest available key), but the script separately counts distinct phone numbers within the group and flags it Review: conflicting contact details — merged, but not silently trusted.
	Charlotte Evans/Turner: no shared key at all → correctly stay unmatched, demonstrating the real limitation.
	Liam O'Connor's return: the return row starts with blank identity fields, so a dedicated step (pos_return_fix) backfills them from the original sale using the shared order_reference before matching runs — meaning the -£89.00 return correctly nets against his +£89.00 sale, giving him a true net in-store spend of £0 for that item, not a phantom untracked return.
	Bright Futures Ltd: gets its own canonical ID and a Possible corporate/bulk — review flag from its wholesale tag.
	Sarah Jenkins: flagged Staff purchase from her staff_discount = Yes field.
	
    What the final table gives you:
	One row per omni_lookup_id, with best-available name/contact details (CRM treated as the identity master, falling back to Online order then POS), a channel_segment (Online only / In-store only / Omnichannel — literally the input to the Active Omnichannel Customers metric from earlier), combined lifetime spend, a match_confidence flag, and a matched_source_record_ids column showing exactly which source rows were merged.
	   
   
   ===================================================================== */

WITH

-- ---------------------------------------------------------------
-- STEP 1: Normalise each source. Casing, whitespace, and phone
-- formatting differences would otherwise silently break matching.
-- ---------------------------------------------------------------

stg_online AS (
    SELECT
        'ONLINE-' + CAST(customer_id AS VARCHAR(30))                         AS record_id,
        'online'                                                              AS source_system,
        NULLIF(LOWER(TRIM(email)), '')                                        AS email_norm,
        NULLIF(REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '+', ''), '') AS phone_norm,
        NULLIF(TRIM(loyalty_id), '')                                          AS loyalty_id_norm,
        first_name, last_name,
        email  AS raw_email,
        phone  AS raw_phone,
        loyalty_id AS raw_loyalty_id,
        address, city, postcode, country,
        total_orders, total_spent_gbp, tags
    FROM online_customers
),

stg_pos_raw AS (
    SELECT
        'POS-' + transaction_id                                               AS record_id,
        'pos'                                                                  AS source_system,
        NULLIF(LOWER(TRIM(email)), '')                                        AS email_norm,
        NULLIF(REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '+', ''), '') AS phone_norm,
        NULLIF(TRIM(loyalty_id), '')                                          AS loyalty_id_norm,
        first_name, last_name,
        email  AS raw_email,
        phone  AS raw_phone,
        loyalty_id AS raw_loyalty_id,
        transaction_type, staff_discount, amount_gbp, order_reference
    FROM teamwork_pos_data
),

-- A return transaction often has no identity fields captured at the
-- till, but shares the same order_reference as the original sale.
-- Backfill identity from the matching sale so the return can still
-- be matched and correctly net off against the original purchase.
pos_return_fix AS (
    SELECT
        r.record_id, r.source_system,
        COALESCE(r.email_norm, s.email_norm)               AS email_norm,
        COALESCE(r.phone_norm, s.phone_norm)                AS phone_norm,
        COALESCE(r.loyalty_id_norm, s.loyalty_id_norm)      AS loyalty_id_norm,
        COALESCE(NULLIF(r.first_name, ''), s.first_name)    AS first_name,
        COALESCE(NULLIF(r.last_name, ''), s.last_name)      AS last_name,
        r.raw_email, r.raw_phone, r.raw_loyalty_id,
        r.transaction_type, r.staff_discount, r.amount_gbp, r.order_reference
    FROM stg_pos_raw r
    LEFT JOIN stg_pos_raw s
        ON s.order_reference = r.order_reference
       AND s.transaction_type = 'Sale'
    WHERE r.transaction_type = 'Return'
),

stg_pos AS (
    SELECT record_id, source_system, email_norm, phone_norm, loyalty_id_norm,
           first_name, last_name, raw_email, raw_phone, raw_loyalty_id,
           transaction_type, staff_discount, amount_gbp, order_reference
    FROM stg_pos_raw
    WHERE transaction_type <> 'Return'

    UNION ALL

    SELECT record_id, source_system, email_norm, phone_norm, loyalty_id_norm,
           first_name, last_name, raw_email, raw_phone, raw_loyalty_id,
           transaction_type, staff_discount, amount_gbp, order_reference
    FROM pos_return_fix
),

stg_crm AS (
    SELECT
        'CRM-' + loyalty_id                                                   AS record_id,
        'crm'                                                                  AS source_system,
        NULLIF(LOWER(TRIM(email)), '')                                        AS email_norm,
        NULLIF(REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '+', ''), '') AS phone_norm,
        NULLIF(TRIM(loyalty_id), '')                                          AS loyalty_id_norm,
        first_name, last_name,
        email  AS raw_email,
        phone  AS raw_phone,
        loyalty_id AS raw_loyalty_id,
        address, city, postcode, country,
        signup_channel, email_consent, sms_consent
    FROM crm_data
),

-- ---------------------------------------------------------------
-- STEP 2: One row per record across all three sources, keeping
-- only the fields needed to decide who matches whom.
-- ---------------------------------------------------------------

all_records AS (
    SELECT record_id, source_system, email_norm, phone_norm, loyalty_id_norm FROM stg_online
    UNION ALL
    SELECT record_id, source_system, email_norm, phone_norm, loyalty_id_norm FROM stg_pos
    UNION ALL
    SELECT record_id, source_system, email_norm, phone_norm, loyalty_id_norm FROM stg_crm
),

-- ---------------------------------------------------------------
-- STEP 3: Build edges — pairs of records that share a non-null
-- loyalty_id, email, or phone. record_id_a < record_id_b avoids
-- duplicate/reversed pairs.
-- ---------------------------------------------------------------

edges_loyalty AS (
    SELECT a.record_id AS record_id_a, b.record_id AS record_id_b
    FROM all_records a
    JOIN all_records b
      ON a.loyalty_id_norm = b.loyalty_id_norm
     AND a.loyalty_id_norm IS NOT NULL
     AND a.record_id < b.record_id
),
edges_email AS (
    SELECT a.record_id AS record_id_a, b.record_id AS record_id_b
    FROM all_records a
    JOIN all_records b
      ON a.email_norm = b.email_norm
     AND a.email_norm IS NOT NULL
     AND a.record_id < b.record_id
),
edges_phone AS (
    SELECT a.record_id AS record_id_a, b.record_id AS record_id_b
    FROM all_records a
    JOIN all_records b
      ON a.phone_norm = b.phone_norm
     AND a.phone_norm IS NOT NULL
     AND a.record_id < b.record_id
),
all_edges AS (
    SELECT record_id_a, record_id_b FROM edges_loyalty
    UNION
    SELECT record_id_a, record_id_b FROM edges_email
    UNION
    SELECT record_id_a, record_id_b FROM edges_phone
),
edges_bidirectional AS (
    SELECT record_id_a AS node, record_id_b AS neighbor FROM all_edges
    UNION
    SELECT record_id_b AS node, record_id_a AS neighbor FROM all_edges
),

-- ---------------------------------------------------------------
-- STEP 4: Connected components. Each node starts only reaching
-- itself; the recursive step follows edges outward. Taking the
-- MIN of everything a node can reach gives every record in the
-- same connected group the same canonical "root" — this is what
-- correctly merges multi-hop chains, not just direct matches.
-- ---------------------------------------------------------------

component_paths AS (
    SELECT record_id AS node, record_id AS reachable_id
    FROM all_records

    UNION

    SELECT cp.node, e.neighbor AS reachable_id
    FROM component_paths cp
    JOIN edges_bidirectional e ON e.node = cp.reachable_id
),

canonical_map AS (
    SELECT node AS record_id, MIN(reachable_id) AS component_root
    FROM component_paths
    GROUP BY node
),

-- ---------------------------------------------------------------
-- STEP 5: Turn the (arbitrary-looking) component root into a
-- clean, sequential omni_lookup_id.
-- ---------------------------------------------------------------

canonical_ids AS (
    SELECT
        component_root,
        'OID-' + RIGHT('00000' + CAST(DENSE_RANK() OVER (ORDER BY component_root) AS VARCHAR(5)), 5) AS omni_lookup_id
    FROM (SELECT DISTINCT component_root FROM canonical_map) x
),

record_to_canonical AS (
    SELECT cm.record_id, ci.omni_lookup_id
    FROM canonical_map cm
    JOIN canonical_ids ci ON ci.component_root = cm.component_root
),

-- ---------------------------------------------------------------
-- STEP 6: Flag low-confidence groups for human review — e.g. two
-- different phone numbers merged under one loyalty_id (a partner
-- using someone else's card), rather than silently trusting it.
-- ---------------------------------------------------------------

match_quality AS (
    SELECT
        rtc.omni_lookup_id,
        COUNT(DISTINCT ar.email_norm) AS distinct_emails,
        COUNT(DISTINCT ar.phone_norm) AS distinct_phones
    FROM all_records ar
    JOIN record_to_canonical rtc ON rtc.record_id = ar.record_id
    GROUP BY rtc.omni_lookup_id
),

-- ---------------------------------------------------------------
-- STEP 7: Pick the best-available name/contact details per
-- canonical customer. CRM is treated as the identity master,
-- falling back to online, then POS, when a field is missing.
-- ---------------------------------------------------------------

all_records_detail AS (
    SELECT record_id, 1 AS source_priority, first_name, last_name,
           raw_email AS email, raw_phone AS phone, raw_loyalty_id AS loyalty_id,
           address, city, postcode, country, signup_channel, email_consent, sms_consent
    FROM stg_crm

    UNION ALL

    SELECT record_id, 2 AS source_priority, first_name, last_name,
           raw_email, raw_phone, raw_loyalty_id,
           address, city, postcode, country, NULL, NULL, NULL
    FROM stg_online

    UNION ALL

    SELECT record_id, 3 AS source_priority, first_name, last_name,
           raw_email, raw_phone, raw_loyalty_id,
           NULL, NULL, NULL, NULL, NULL, NULL, NULL
    FROM stg_pos
    WHERE transaction_type = 'Sale'
),

best_fields AS (
    SELECT rtc.omni_lookup_id, d.*,
           ROW_NUMBER() OVER (PARTITION BY rtc.omni_lookup_id ORDER BY d.source_priority ASC) AS rn
    FROM all_records_detail d
    JOIN record_to_canonical rtc ON rtc.record_id = d.record_id
),

-- ---------------------------------------------------------------
-- STEP 8: Roll up channel activity and spend per canonical
-- customer, and keep an auditable list of every source record
-- that was matched into it.
-- ---------------------------------------------------------------

online_activity AS (
    SELECT rtc.omni_lookup_id,
           MAX(1)                     AS has_online_activity,
           SUM(s.total_orders)        AS total_online_orders,
           SUM(s.total_spent_gbp)     AS total_online_spent_gbp,
           MAX(s.tags)                AS online_tags
    FROM stg_online s
    JOIN record_to_canonical rtc ON rtc.record_id = s.record_id
    GROUP BY rtc.omni_lookup_id
),

instore_activity AS (
    SELECT rtc.omni_lookup_id,
           MAX(1)                                          AS has_instore_activity,
           COUNT(CASE WHEN p.transaction_type = 'Sale' THEN 1 END) AS total_instore_transactions,
           SUM(p.amount_gbp)                                AS total_instore_spent_gbp,
           MAX(CASE WHEN p.staff_discount = 'Yes' THEN 1 ELSE 0 END) AS is_staff
    FROM stg_pos p
    JOIN record_to_canonical rtc ON rtc.record_id = p.record_id
    GROUP BY rtc.omni_lookup_id
),

source_crosswalk AS (
    SELECT omni_lookup_id,
           STRING_AGG(record_id, '; ') AS matched_source_record_ids   -- Postgres/BigQuery: same syntax; older SQL Server: use FOR XML PATH instead
    FROM record_to_canonical
    GROUP BY omni_lookup_id
)

-- ---------------------------------------------------------------
-- FINAL: one row per canonical customer.
-- ---------------------------------------------------------------

SELECT
    bf.omni_lookup_id,
    bf.first_name,
    bf.last_name,
    bf.email,
    bf.phone,
    bf.loyalty_id,
    bf.address, bf.city, bf.postcode, bf.country,
    bf.signup_channel, bf.email_consent, bf.sms_consent,

    COALESCE(oa.has_online_activity, 0)   AS has_online_activity,
    COALESCE(ia.has_instore_activity, 0)  AS has_instore_activity,
    CASE
        WHEN COALESCE(oa.has_online_activity,0) = 1 AND COALESCE(ia.has_instore_activity,0) = 1 THEN 'Omnichannel'
        WHEN COALESCE(oa.has_online_activity,0) = 1 THEN 'Online only'
        WHEN COALESCE(ia.has_instore_activity,0) = 1 THEN 'In-store only'
        ELSE 'Unknown'
    END AS channel_segment,

    oa.total_online_orders,
    oa.total_online_spent_gbp,
    ia.total_instore_transactions,
    ia.total_instore_spent_gbp,
    COALESCE(oa.total_online_spent_gbp, 0) + COALESCE(ia.total_instore_spent_gbp, 0) AS total_lifetime_spent_gbp,

    CASE WHEN oa.online_tags LIKE '%wholesale%' THEN 'Possible corporate/bulk — review'
         WHEN ia.is_staff = 1 THEN 'Staff purchase'
         ELSE NULL
    END AS segment_flag,

    CASE
        WHEN mq.distinct_emails > 1 OR mq.distinct_phones > 1
        THEN 'Review: conflicting contact details across matched records'
        ELSE 'OK'
    END AS match_confidence,

    sx.matched_source_record_ids

FROM best_fields bf
LEFT JOIN online_activity oa   ON oa.omni_lookup_id = bf.omni_lookup_id
LEFT JOIN instore_activity ia  ON ia.omni_lookup_id = bf.omni_lookup_id
LEFT JOIN match_quality mq     ON mq.omni_lookup_id = bf.omni_lookup_id
LEFT JOIN source_crosswalk sx  ON sx.omni_lookup_id = bf.omni_lookup_id
WHERE bf.rn = 1   -- one row per canonical customer, using the highest-priority source's identity fields

-- Azure Fabric Warehouse / most modern engines:
-- wrap the whole query above in: CREATE TABLE customer_360 AS ( ... )
-- Classic SQL Server / dedicated Synapse pools: use SELECT ... INTO customer_360 instead
;

/* =====================================================================
   To actually save this as a table, wrap the full statement above:

     CREATE TABLE customer_360 AS
     <everything above, starting from the first WITH>

   NEXT STEP: this logic is exactly what should become a set of
   tested, version-controlled dbt models (stg_online, stg_pos,
   stg_crm → int_customer_edges → int_customer_components →
   customer_360), rather than living as one ad hoc script — with
   dbt tests asserting things like "no duplicate omni_lookup_id per
   source record" and "match_confidence = 'OK' for X% of customers"
   as an ongoing data quality gate, not a one-time check.
   ===================================================================== */


/* =====================================================================
   OPTIONAL: COMPLETENESS CHECK
   Confirms that single-source customers — e.g. Bright Futures Ltd
   (online only) and Sarah Jenkins (POS only) — still receive their
   own omni_lookup_id, even with no cross-source match. The connected-
   components logic above already guarantees this (every record starts
   out reaching itself), so these counts should simply confirm it:
   customer_360_rows should equal the number of distinct real people
   across all three files, not the number of *matched* people only.
   ===================================================================== */

SELECT COUNT(*) AS online_rows FROM online_customers;
SELECT COUNT(*) AS pos_sale_rows FROM teamwork_pos_data WHERE transaction_type = 'Sale';
SELECT COUNT(*) AS crm_rows FROM crm_data;
SELECT COUNT(*) AS customer_360_rows FROM customer_360;   -- run after customer_360 has been created

-- Spot-check the two specific customers by name:
SELECT omni_lookup_id, first_name, last_name, channel_segment, segment_flag
FROM customer_360
WHERE last_name IN ('Ltd', 'Jenkins');


/* =====================================================================
   PART 2: ID CROSSWALK LOOKUP TABLE
   Maps omni_lookup_id to the loyalty_id (CRM), customer_id (online),
   and transaction_id(s) (POS) that were matched into it.

   Deliberately built on top of the already-created customer_360 table
   — specifically its matched_source_record_ids column — rather than
   re-running the whole matching pipeline a second time. In a dbt
   implementation this duplication problem disappears entirely, since
   every model can simply ref() the earlier staging models instead of
   restating them.

   Note: a person can have many POS transactions but normally only one
   online account and one CRM/loyalty record, so loyalty_id and
   online_customer_id come back as single values, while
   pos_transaction_ids is a semicolon-separated list.
   ===================================================================== */

WITH exploded_ids AS (
    -- STRING_SPLIT is native T-SQL/Synapse/Fabric syntax. Postgres: use
    -- unnest(string_to_array(...)); Snowflake/BigQuery: use SPLIT / FLATTEN.
    SELECT
        c.omni_lookup_id,
        LTRIM(RTRIM(s.value)) AS source_record_id
    FROM customer_360 c
    CROSS APPLY STRING_SPLIT(c.matched_source_record_ids, ';') s
),

tagged_ids AS (
    SELECT
        omni_lookup_id,
        source_record_id,
        CASE
            WHEN source_record_id LIKE 'CRM-%'     THEN 'crm'
            WHEN source_record_id LIKE 'ONLINE-%' THEN 'online'
            WHEN source_record_id LIKE 'POS-%'     THEN 'pos'
        END AS source_system,
        CASE
            WHEN source_record_id LIKE 'CRM-%'     THEN SUBSTRING(source_record_id, 5, 50)
            WHEN source_record_id LIKE 'ONLINE-%' THEN SUBSTRING(source_record_id, 9, 50)
            WHEN source_record_id LIKE 'POS-%'     THEN SUBSTRING(source_record_id, 5, 50)
        END AS native_id
    FROM exploded_ids
)

-- One row per (customer, POS transaction) instead of a concatenated
-- list — makes a plain "WHERE pos_transaction_id = 'T20003'" lookup
-- possible without ever having to unpack a string.

customer_identity_scalars AS (
    -- loyalty_id and online_customer_id are naturally one-per-person
    -- in this dataset (unlike POS transactions), so these stay scalar.
    SELECT
        omni_lookup_id,
        MAX(CASE WHEN source_system = 'crm'     THEN native_id END) AS loyalty_id,
        MAX(CASE WHEN source_system = 'online' THEN native_id END) AS online_customer_id
    FROM tagged_ids
    GROUP BY omni_lookup_id
),

pos_records AS (
    SELECT omni_lookup_id, native_id AS pos_transaction_id
    FROM tagged_ids
    WHERE source_system = 'pos'
)

SELECT
    cis.omni_lookup_id,
    cis.loyalty_id,
    cis.online_customer_id,
    pr.pos_transaction_id
FROM customer_identity_scalars cis
LEFT JOIN pos_records pr ON pr.omni_lookup_id = cis.omni_lookup_id
-- LEFT JOIN, not JOIN: an online-only customer with zero POS
-- transactions must still get one row, with pos_transaction_id NULL —
-- not silently disappear from the crosswalk.

-- Wrap in: CREATE TABLE omni_lookup_id_crosswalk AS ( ... )
;

/* Example rows this produces:

   omni_lookup_id | loyalty_id | online_customer_id | pos_transaction_id
   ----------------|------------|----------------------|--------------------
   OID-00002      | OA10002    | 7451200567            | NULL                <- Daniel Wright, online only, no POS activity
   OID-00004      | OA10004    | 7451200812            | T20003              <- Liam O'Connor, his sale
   OID-00004      | OA10004    | 7451200812            | T20004              <- Liam O'Connor, the return on the same order
   OID-00012      | NULL       | NULL                  | T20009              <- Sarah Jenkins, POS only
   OID-00015      | NULL       | 7451202233            | NULL                <- Bright Futures Ltd, online only

   Liam now takes two rows instead of one, since he has two POS
   transactions — loyalty_id and online_customer_id are repeated on
   both, which is expected at this grain. His sale and return both stay
   listed for traceability, even though customer_360 already nets the
   £89 / -£89 down to a combined spend of £0 for that item.
*/

