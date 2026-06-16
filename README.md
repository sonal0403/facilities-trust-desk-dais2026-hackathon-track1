# Facility Trust Desk — Hackathon Documentation

---

## 1. Inspiration

> *"Healthcare facilities claim all kinds of capabilities — but how do you know what's genuinely backed by evidence vs. just noise in the data?"*

- **10,000 facilities** self-report capabilities — no verification layer exists today
- Planners need to evaluate: how strongly is each claim backed by evidence across the data?
- **15 healthcare capabilities × 10k facilities = 150,000 trust decisions** to make
- Manual verification is impossible at this scale

**Our goal:** Build a trust scoring system that counts evidence signals across multiple data fields, lets planners browse and evaluate claims at scale, and gives them the power to override when they know better.

**Future enhancement:** Treat specific quantitative claims (e.g., "22-bed ICU") as a strong signal in itself — currently it's counted like any other keyword hit.

---
## 2. What It Does

> *Think Netflix — but for healthcare facility trust.*

| Feature | What It Does |
|---------|-------------|
| Browse by Region | Netflix-style rows — click Maharashtra, see its facilities |
| Browse by Capability | Filter to ICU / Cardiology / etc. across all regions |
| Trust Scoring | Every facility×capability pair scored as **Strong / Partial / Weak / No Claim** |
| Re-evaluate | Edit evidence text, see trust level change live |
| Override with Audit | Confirm the change — writes to audit log AND updates live scores |
| Cross-filter Search | Maharashtra + ICU + Cardiology — AND logic |

**Live app:** [facility-trust-desk-7474649205602894.aws.databricksapps.com](https://facility-trust-desk-7474649205602894.aws.databricksapps.com)

---
## 3. How We Built It

### Act 1: The Capability Map (most important piece)

> *We had raw unstructured text. Our team fed it to Genie and asked: "what capabilities are described here?" Genie produced a global capability map — 15 capabilities, each with keyword dictionaries by field. This became the foundation.*

```
┌──────────────────────┐       ┌─────────────────────┐       ┌────────────────────────┐       ┌──────────────────┐
│  Raw facility text   │ ────▶ │   Genie analysis    │ ────▶ │  Capability Map (JSON) │ ────▶ │  Scoring Engine  │
│  (5 unstructured     │       │   "what capabilities│       │  15 capabilities ×     │       │  config — no LLM │
│   fields per row)    │       │    are here?"       │       │  5 fields × N keywords │       │  needed at runtime│
└──────────────────────┘       └─────────────────────┘       └────────────────────────┘       └──────────────────┘
```

**Sample from the capability map:**

| Capability | capability field keywords | equipment field | procedure field | specialties field |
|-----------|--------------------------|-----------------|-----------------|-------------------|
| ICU | icu, intensive care, critical care | ventilator, cardiac monitor | mechanical ventilation, intubation | criticalCareMedicine |
| Maternity | maternity, labour room, delivery | fetal monitor, infant warmer | c-section, normal delivery | gynecologyAndObstetrics |
| Cardiology | cardiology, cardiac, cath lab | echocardiography, stent | angioplasty, bypass | interventionalCardiology |
| Emergency | emergency, 24x7, casualty | ambulance, defibrillator | trauma, resuscitation | emergencyMedicine |
| Oncology | oncology, cancer, chemotherapy | linear accelerator, pet-ct | chemotherapy, radiation | medicalOncology |

### Act 2: The Scoring Engine

> *No LLM. No API calls. Pure keyword matching — fast and deterministic.*

#### The Core Idea: Categories as Independent Signals

Each capability in our map has keywords organized into **5 categories** (fields from the source data):

| Category | What it represents | Example (NICU) |
|----------|-------------------|----------------|
| **capability** | Services the facility lists as offerings | "nicu", "neonatal intensive care" |
| **equipment** | Physical equipment/devices on site | "incubator", "infant warmer", "phototherapy" |
| **procedure** | Medical procedures performed | "neonatal resuscitation", "exchange transfusion" |
| **specialties** | Registered medical specialty codes | `neonatologyPerinatalMedicine` |
| **description** | Free-text facility description | "nicu", "neonatal", "newborn intensive" |

**Trust is determined by how many of these 5 categories show evidence.** Each category that has at least one keyword match counts as one independent signal. The logic:
- If only the `specialties` field mentions it → that's 1 category → not strongly backed
- If `specialties` AND `equipment` both mention it → 2 categories → more confidence
- If `specialties` + `equipment` + `procedure` all mention it → 3 categories → strong — the facility has the specialty code, owns the equipment, AND performs the procedures

```
┌─────────────┐     ┌────────────────┐     ┌──────────────────┐     ┌────────────────┐
│ Facility    │ ──▶ │ Parse fields   │ ──▶ │ Match keywords   │ ──▶ │ Count & Decide │
│ raw fields  │     │ (JSON arrays)  │     │ (substring)      │     │ trust level    │
└─────────────┘     └────────────────┘     └──────────────────┘     └────────────────┘
                                                    │
                                            ┌───────▼────────┐
                                            │ Record citation│
                                            │ {field, text}  │
                                            └────────────────┘
```

**How it works step by step:**
1. For each facility × capability pair: parse each category's JSON array into text items
2. Substring-match each item against the capability's keywords for that category
3. Record every match as a citation: `{field: "equipment", text: "infant warmer"}`
4. Count **categories matched** (how many of the 5 categories had at least one hit) and **total hits** (sum of all keyword matches)
5. Determine trust level based on thresholds:

**Trust Level Decision Table:**

| Trust Level | Path 1: Category Spread | Path 2: Sheer Volume | Intuition |
|-------------|------------------------|---------------------|-----------||
| **Strong** | 3+ categories matched | OR 5+ total hits (even in 1 category) | Either confirmed across multiple independent sources, OR overwhelming keyword density in the data |
| **Partial** | 2+ categories matched | OR 3+ total hits (even in 1 category) | Either evidence in 2 categories, OR enough repetition to suggest real capability |
| **Weak** | 1 category with a hit | (fewer than 3 total hits) | Mentioned somewhere but not strongly backed |
| **No Claim** | — | 0 matches | Capability not found anywhere in the facility's data |

*Additionally: a quantitative claim (e.g., "22-bed ICU") + 2+ categories → Strong (lowers the spread threshold by 1).*

**Worked example — NICU scoring for a facility:**

| Category | Items in facility data | Keyword matched? | Hits |
|----------|----------------------|------------------|------|
| capability | ["General Medicine", "Pediatrics"] | No NICU keywords found | 0 |
| equipment | ["Incubator", "Radiant Warmer", "Ventilator"] | "incubator" ✓, "radiant warmer" ✓ | 2 |
| procedure | ["Neonatal Resuscitation", "Phototherapy"] | "neonatal resuscitation" ✓, "phototherapy" ✓ | 2 |
| specialties | ["neonatologyPerinatalMedicine"] | Exact match ✓ | 1 |
| description | "Multi-specialty hospital" | No NICU keywords | 0 |

**Result:** 3 categories matched (equipment + procedure + specialties), 5 total hits → **Strong Evidence** (qualifies via BOTH paths)

> **Key insight:** There are two ways to reach a higher trust level:
> - **Category spread** — evidence across multiple independent categories (strongest signal)
> - **Keyword density** — enough hits even in a single category (e.g., a facility lists 5 NICU-related items in their equipment field alone → Strong via Path 2)
>
> Both paths are valid. Category spread means independent corroboration. Keyword density means the data is rich with references even if concentrated in one area.

> **Future enhancement:** Treat specific quantitative claims (e.g., "22-bed ICU") as a strong signal in itself — currently counted like any other keyword hit.

**Example SQL to see scoring in action:**
```sql
-- See the scoring in action for a real facility
SELECT facility_id, capability, trust_level, match_count, fields_matched, evidence_citations
FROM workspace.default.facility_trust_scores
WHERE trust_level = 'strong_evidence'
ORDER BY match_count DESC
LIMIT 5
```

### Act 3: Front-end Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | FastAPI (Python) | Single file, no external ML deps, Databricks App compatible |
| Frontend | Vanilla HTML/CSS/JS | No React, no build step, no framework overhead |
| UI Theme | Netflix dark | Horizontal scroll rows, card-based browsing |
| Deployment | Databricks App | Source code snapshot from workspace folder |
| Images | Binary blobs in Delta table | App container can't access `/Workspace/` paths |

### Act 4: State Images

```
┌──────────────────┐    SQL read_files()    ┌─────────────────────┐    /api/state-image/    ┌──────┐
│ /Workspace/final/│ ─────────────────────▶ │ state_images_data   │ ─────────────────────▶ │ JPEG │
│ (image files)    │                        │ (Delta: filename +  │     fuzzy match        │ resp │
└──────────────────┘                        │  binary content)    │                        └──────┘
                                            └─────────────────────┘
```

**Fuzzy matching logic:** Normalize both state names (DB) and filenames to lowercase alpha-only, then `startsWith` comparison handles cases like "Jammu And Kashmir" → `jammuandkashmir` matching `jammukashmir` from filename `Jammu_Kashmir.jpg`.

### Act 5: Override & Audit Flow

```
Planner edits citation pills in the UI
        │
        ▼
  POST /api/facility/{id}/rescore
  → Runs score_facility() with edited texts
  → Returns {before: {...}, after: {...}}
        │
        ▼
  UI shows Before / After diff (trust level, citations)
  Planner adds a note, clicks "Confirm Override"
        │
        ▼
  POST /api/facility/{id}/confirm-override
  → INSERT INTO user_overrides (full audit record)
  → UPDATE facility_trust_scores (live scores table)
        │
        ▼
  Change is visible immediately across the entire app
```

**Two writes on every confirm:**
1. **`user_overrides`** — immutable audit record (override_id, facility_id, capability, all edited texts, old/new trust levels, old/new citations, note, timestamp)
2. **`facility_trust_scores`** — UPDATE the live row with new trust_level, citations, fields_matched, match_count, scored_at

This means overrides are **immediately reflected** everywhere in the app AND **fully auditable**.

**Example SQL to view audit trail:**
```sql
-- View recent overrides (audit trail)
SELECT id, facility_id, capability_scored, old_trust_level, new_trust_level, note, confirmed_at
FROM workspace.default.user_overrides
ORDER BY confirmed_at DESC
LIMIT 10
```

---
## 4. Challenges We Ran Into

| Challenge | What We Found | How We Solved It |
|-----------|--------------|------------------|
| **Messy state field** | `address_stateOrRegion` contains cities, geocodes (`12.9716,77.5946`), JSON fragments | Filter: `LENGTH < 40`, exclude `{` and `[` prefixes |
| **Duplicate scores** | Multiple rows per facility×capability in the scores table | `ROW_NUMBER() OVER (PARTITION BY capability ORDER BY match_count DESC)` — keep the best |
| **App container isolation** | Databricks App container can't access `/Workspace/` filesystem paths at runtime | Images stored as binary blobs in a Delta table, served via SQL query instead of file reads |
| **Performance at scale** | 10k facilities × 15 capabilities = 151k score rows; cold warehouse queries take seconds | In-memory cache on app startup (capabilities, regions, facility names) for instant search/autocomplete |
| **Image name mismatch** | DB: "Jammu And Kashmir" vs file: "Jammu_Kashmir_1.jpg" | Normalize to alpha-only lowercase + fuzzy `startsWith` comparison |

**Example of messy state data:**
```sql
-- Example of the messy state data we had to handle
SELECT address_stateOrRegion, COUNT(*) as cnt
FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
WHERE address_stateOrRegion IS NOT NULL
GROUP BY address_stateOrRegion
ORDER BY cnt DESC
LIMIT 20
```

---
## 5. Accomplishments

- **Zero-LLM scoring** — runs in milliseconds, no API cost, fully deterministic
- **Full audit trail** — every override is traceable with before/after values + planner note + timestamp
- **Live propagation** — overrides update the scores table immediately, visible everywhere
- **Netflix UX** — 10,000 facilities feel browseable, not overwhelming
- **Cross-filter AND search** — "Maharashtra + ICU + Cardiology" just works
- **Fuzzy image matching** — gracefully handles messy state names and inconsistent filenames
- **Genie-powered foundation** — the capability map was generated from raw data, not hand-crafted

---
## 6. What We Learned

- **Keyword scoring is surprisingly effective** — when the capability map is well-curated (Genie produced a great initial map from raw text)
- **Trust thresholds need tuning** — too strict misses real capabilities, too loose flags everything as "strong"
- **Quantitative claims feel strong but aren't (yet)** — "22-bed ICU" is counted as one keyword hit today; treating it as inherently stronger is a future enhancement
- **Databricks Apps have constraints** — powerful for rapid deployment, but app containers can't access `/Workspace/` paths directly (hence the Delta-table image solution)
- **Caching makes everything feel instant** — startup cache for metadata eliminates repeated SQL for search/autocomplete

---
## 7. What's Next

| Enhancement | Impact |
|-------------|--------|
| LLM second pass | Semantic verification of keyword matches — does the text *mean* the facility has this capability? |
| Quantitative claim weighting | "22-bed ICU" counts as a strong signal by itself |
| Bulk override workflow | Approve/reject multiple facilities at once |
| External verification | Cross-reference with government registry, accreditation databases |
| Collaborative review | Assign facilities to specific planners, track review progress; requires authentication and authorization to manage user roles and permissions |
| Confidence scoring | Weight different signal types differently (equipment > description mention) |

---
## 8. Technical Reference

### Development Workflow

We used two AI-powered tools in tandem to build this app:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                        DEVELOPMENT WORKFLOW                                     │
│                                                                                 │
│  ┌─────────────────────┐         ┌──────────────────────────────────────────┐  │
│  │   Genie (AI Code)   │         │   Claude Code (IntelliJ Terminal)         │  │
│  │                     │         │                                           │  │
│  │  • Analyzed raw     │         │  • Connected to Databricks workspace      │  │
│  │    facility data    │         │    via Databricks MCP Server              │  │
│  │  • Built the 15-    │         │  • Iterated on app code (FastAPI + JS)    │  │
│  │    capability map   │         │  • Deployed app directly from terminal    │  │
│  │  • Foundational     │         │  • Managed tables, queries, debugging     │  │
│  │    data analysis    │         │  • End-to-end development loop            │  │
│  └─────────────────────┘         └──────────────────────────────────────────┘  │
│         │                                        │                              │
│         ▼                                        ▼                              │
│   Capability Map JSON                  Working App + Deployment                  │
│   (keywords per field)                 (code → workspace → live app)             │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Step 1 — Genie Code:** Our team used Genie to explore the raw unstructured facility data, understand patterns across 10k rows, and generate the global capability map (15 capabilities × 5 categories × N keywords). This was the foundational data work.

**Step 2 — Claude Code:** From the IntelliJ IDE terminal, we connected Claude Code to our Databricks workspace using the **Databricks MCP Server**. This gave us the ability to iterate on code, run SQL, manage tables, upload files, and deploy the app — all in a single conversational loop without leaving the terminal.

---

### Data Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                        SOURCE OF TRUTH                             │
│  databricks_virtue_foundation_dataset_dais_2026                    │
│  .virtue_foundation_dataset.facilities  (10,088 rows)              │
│                                                                    │
│  Fields: unique_id, name, capability[], procedure[], equipment[],  │
│          specialties[], description, address_city,                  │
│          address_stateOrRegion, ...                                 │
└──────────────────────────────┬────────────────────────────────────┘
                               │ scored by keyword engine
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│  workspace.default.facility_trust_scores  (~150,000 rows)          │
│                                                                    │
│  Columns: facility_id, capability, trust_level, match_count,       │
│           fields_matched (JSON array), evidence_citations (JSON),   │
│           scored_at                                                 │
│                                                                    │
│  One row per facility × capability (deduped at query time)         │
└──────────────────┬────────────────────────────────────────────────┘
                   │ on override: UPDATE live row
                   │
┌──────────────────▼────────────────────────────────────────────────┐
│  workspace.default.user_overrides  (audit log — append only)       │
│                                                                    │
│  Columns: id, facility_id, capability_scored,                      │
│           edited_capability, edited_procedure, edited_equipment,    │
│           edited_specialties, edited_description,                   │
│           old_trust_level, new_trust_level,                         │
│           old_citations, new_citations,                             │
│           note, confirmed_at                                        │
│                                                                    │
│  INSERT on every confirm (immutable — never updated or deleted)    │
└───────────────────────────────────────────────────────────────────┘
```

**Table statistics:**
```sql
-- Table stats
SELECT 'facilities (source)' as table_name, COUNT(*) as row_count 
FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
UNION ALL
SELECT 'facility_trust_scores', COUNT(*) FROM workspace.default.facility_trust_scores
UNION ALL
SELECT 'user_overrides', COUNT(*) FROM workspace.default.user_overrides
UNION ALL
SELECT 'state_images_data', COUNT(*) FROM workspace.default.state_images_data
```

### API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|  
| `/` | GET | Serve main UI (index.html) |
| `/api/cache-status` | GET | Check if startup cache is ready |
| `/api/capabilities` | GET | List 15 capabilities with facility counts |
| `/api/regions` | GET | List all valid regions with facility counts |
| `/api/hero-regions` | GET | Top 5 regions for hero carousel |
| `/api/top-facilities?limit=` | GET | Facilities with highest total citation counts |
| `/api/strong-evidence?limit=` | GET | Facilities scored as strong across most capabilities |
| `/api/needs-review?limit=` | GET | Borderline cases (weak + 2+ matches) |
| `/api/facilities?region=&capability=&name=` | GET | Cross-filter search (AND logic) |
| `/api/facility/{id}` | GET | Full facility details + all 15 capability scores |
| `/api/facility/{id}/rescore` | POST | Re-evaluate with edited texts, return before/after |
| `/api/facility/{id}/confirm-override` | POST | Write audit + update live scores |
| `/api/state-image/{state}` | GET | JPEG response (fuzzy match on state name) |
| `/api/search-suggestions?q=` | GET | Autocomplete facility names (cached) |

### Ranking Logic — Why Things Appear Where They Do

| What you see in the UI | Why it's in that order |
|------------------------|----------------------|
| Maharashtra as first region | Highest `facility_count` in source table |
| First capability listed (e.g., Emergency) | Most facilities with non-"no_claim" scores |
| Top facility in "Top Facilities" row | Highest `SUM(match_count)` across all 15 capabilities |
| Facility tagged "ICU" on its card | Either filtering by ICU, or ICU is its highest-scored capability |
| Strong before Partial in facility list | `ORDER BY trust_priority` (strong=1, partial=2, weak=3, none=4) |
| "Needs Review" row entries | `trust_level = 'weak_evidence' AND match_count >= 2` — borderline cases |

**Example - Why Maharashtra is first:**
```sql
-- Why Maharashtra is first: top regions by facility count
SELECT address_stateOrRegion as region, COUNT(*) as facility_count
FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
WHERE address_stateOrRegion IS NOT NULL
  AND LENGTH(address_stateOrRegion) < 40
  AND address_stateOrRegion NOT LIKE '{%'
  AND address_stateOrRegion NOT LIKE '[%'
GROUP BY address_stateOrRegion
ORDER BY facility_count DESC
LIMIT 10
```

### Image Refresh Procedure

When new state images are added to `/Workspace/Users/sonal.0403@gmail.com/final/`:

```sql
-- Step 1: Reload images from the workspace folder into Delta
CREATE OR REPLACE TABLE workspace.default.state_images_data AS
SELECT regexp_extract(path, '([^/]+)$', 1) as filename, content
FROM read_files('/Workspace/Users/sonal.0403@gmail.com/final/', format => 'binaryFile')
```

Then redeploy the app to clear the in-memory filename index (it caches on first request).

The fuzzy matching handles inconsistencies like:
- `"Maharashtra"` → normalized → `maharashtra` → matches file `Maharashtra_1.jpg` (normalized: `maharashtra`)
- `"Jammu And Kashmir"` → normalized → `jammuandkashmir` → `startsWith` match with `jammukashmir`

**Current state images:**
```sql
-- Current state images in the table
SELECT filename, LENGTH(content) as size_bytes
FROM workspace.default.state_images_data
ORDER BY filename
```

---

### Trust Level Distribution (live)

```sql
-- How are the 150k scores distributed across trust levels?
SELECT trust_level, COUNT(*) as score_count,
       COUNT(DISTINCT facility_id) as facilities_affected,
       ROUND(AVG(match_count), 1) as avg_match_count
FROM workspace.default.facility_trust_scores
GROUP BY trust_level
ORDER BY CASE trust_level
    WHEN 'strong_evidence' THEN 1
    WHEN 'partial_evidence' THEN 2
    WHEN 'weak_evidence' THEN 3
    ELSE 4
END
```

---
*Built for DAIS 2026 Hackathon — Track 1*

**Team:** Jain

**App:** [facility-trust-desk-7474649205602894.aws.databricksapps.com](https://facility-trust-desk-7474649205602894.aws.databricksapps.com)
