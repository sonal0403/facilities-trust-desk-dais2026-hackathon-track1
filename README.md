# Facility Trust Desk — Hackathon Documentation

---

### Team

| Name | Role | Company |
|------|------|---------|
| **Sonal Jain** | Data Engineering Manager, AdTech | Comcast (Cable/Telecommunication) |
| **Saket Jain** | Principal Data Engineer, Data Platform | DriveWealth (FinTech) |

---

## Table of Contents

- [1. Inspiration](#1-inspiration)
- [2. What It Does](#2-what-it-does)
- [3. How We Built It](#3-how-we-built-it)
  - [Our Multi-AI Approach](#our-multi-ai-approach)
  - [Act 1: The Capability Map](#act-1-the-capability-map-most-important-piece)
  - [Act 2: The Scoring Engine](#act-2-the-scoring-engine)
  - [Act 3: Front-end Stack](#act-3-front-end-stack)
  - [Act 4: State Images](#act-4-state-images)
  - [Act 5: Override & Audit Flow](#act-5-override--audit-flow)
- [4. Challenges We Ran Into](#4-challenges-we-ran-into)
- [5. Accomplishments](#5-accomplishments)
- [6. What We Learned](#6-what-we-learned)
- [7. What's Next](#7-whats-next)
- [8. Technical Reference](#8-technical-reference)
  - [Development Workflow — Multi-Modal AI Approach](#development-workflow--multi-modal-ai-approach)
  - [Data Architecture](#data-architecture)
  - [API Reference](#api-reference)
  - [Ranking Logic](#ranking-logic--why-things-appear-where-they-do)
  - [Image Refresh Procedure](#image-refresh-procedure)

---

## 1. Inspiration

> *"A facility claims it has an ICU. But does it actually have ventilators? Does it perform mechanical ventilation? Does it have critical care specialists on staff? Or is ICU just a word in a list?"*

Every facility in our dataset has a **capability** field — a JSON array of things they say they can do: `["ICU", "Maternity", "Emergency"]`. These are their **claims**.

But a claim alone doesn't tell you how real it is. The same dataset also has:
- **equipment** — what physical devices they have
- **procedure** — what medical procedures they perform
- **specialties** — what registered medical specialties they hold
- **description** — free-text about the facility

**The question:** Does the rest of the data back up what the facility claims?

| What we have | What it means |
|-------------|---------------|
| Facility claims "ICU" in capability field | That's the **claim** |
| Equipment lists "ventilator", "cardiac monitor" | That's **evidence** supporting the claim |
| Procedures include "mechanical ventilation" | More **evidence** |
| Specialties include `criticalCareMedicine` | Even more **evidence** |

**Our approach:** Evaluate each claim by checking how many other categories corroborate it. More corroboration = higher trust.

- **10,000 facilities** × **15 capabilities** = **150,000 trust decisions** to make
- Manual verification is impossible at this scale
- **Our goal:** Build an app that evaluates facility claims by measuring corroborating evidence, lets planners browse and assess trust at scale, and gives them the power to override when they know better.

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

### Our Multi-AI Approach

We used a **multi-modal AI approach** combining Databricks AI Gateway and Genie for initial analysis, then Claude Code with Databricks MCP Server for iterative development:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         MULTI-AI DEVELOPMENT APPROACH                               │
│                                                                                     │
│  Phase 1: Discovery & Foundation          Phase 2: Build & Deploy                   │
│  ┌───────────────────────────────┐        ┌────────────────────────────────────┐    │
│  │  Databricks Genie             │        │  Claude Code (IntelliJ Terminal)   │    │
│  │  + AI Gateway                 │        │  + Databricks MCP Server           │    │
│  │                               │        │  + Databricks AI Gateway           │    │
│  │  • Explore raw data           │        │                                    │    │
│  │  • Identify 15 capabilities   │        │  • Expand keyword map per category │    │
│  │  • Generate seed keyword list │        │  • Build scoring engine            │    │
│  │  • Understand field structure │        │  • Build FastAPI app + UI          │    │
│  └───────────────────────────────┘        │  • Deploy & iterate                │    │
│              │                            └────────────────────────────────────┘    │
│              ▼                                            │                         │
│     Seed list (15 caps × flat keywords)                   ▼                         │
│              │                             Full 5-category keyword map              │
│              └──────────────────────────── + Working app + Live deployment          │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Act 1: Building the Data Foundation | The Capability Map (most important piece)

**How we built the map — step by step:**

1. **Genie explored the raw data** — our team fed the unstructured facility text to Genie and asked: "what healthcare capabilities are described across these 10k records?" Genie identified 15 distinct capability categories.

2. **Genie produced a seed keyword list** — for each capability, a flat array of core keywords that signal its presence:
   ```
   "ICU": ["icu", "intensive care", "critical care", "intensive care unit", ...]
   "NICU": ["nicu", "neonatal", "newborn intensive care", ...]
   "Maternity": ["maternity", "obstetrics", "labor", "delivery", ...]
   ```

3. **Claude Code expanded per category** — using Databricks MCP Server to query the actual data, Claude expanded the flat list into a structured 5-category map:
   - Distributed seed keywords to the correct categories (e.g., "ventilator" → equipment)
   - Added field-specific terms by analyzing what actually appears in each field (equipment names, procedure terms, specialty codes)
   - Added reasonable synonyms and variations as a "wishlist" — if they appear in the data, they'll match; if not, no harm

4. **Keywords are search terms, not extracted phrases** — the map is a collection of substring patterns, not an inventory of exact values found in the data. Keyword `"neonatal"` will catch `"Neonatal Intensive Care"`, `"neonatal resuscitation"`, etc. Some keywords may have zero matches across all facilities — they're there for completeness.

**The final map structure (15 capabilities × 5 categories × N keywords each):**

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
|-------------|------------------------|---------------------|-----------|
| **Strong** | 3+ categories matched | OR 5+ total hits (even in 1 category) | Either confirmed across multiple independent sources, OR overwhelming keyword density in the data |
| **Partial** | 2+ categories matched | OR 3+ total hits (even in 1 category) | Either evidence in 2 categories, OR enough repetition to suggest real capability |
| **Weak** | 1 category with a hit | (fewer than 3 total hits) | Mentioned somewhere but not strongly backed |
| **No Claim** | — | 0 matches | Capability not found anywhere in the facility's data |

*Additionally: a quantitative claim (e.g., "22-bed ICU") + 2+ categories → Strong (lowers the spread threshold by 1).*

**Quantitative detection code:**
```python
def _has_quantitative_claim(citations):
    quant_pattern = re.compile(r'\d+[\s-]*(bed|unit|theatre|ot |ventilator|machine|doctor)', re.IGNORECASE)
    for cite in citations:
        if quant_pattern.search(cite["text"]):
            return True
    return False

def _determine_trust_level(fields_matched, match_count, has_quant):
    num_fields = len(fields_matched)
    if num_fields >= 3 or match_count >= 5 or (has_quant and num_fields >= 2):
        return "strong_evidence"
    ...
```
*The regex detects patterns like "22-bed", "5 ventilator", "10 unit" in citation text. If found AND 2+ categories matched → promotes to Strong.*

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

---

## 4. Challenges We Ran Into

| Challenge | What We Found | How We Solved It |
|-----------|--------------|-----------------|
| **Messy state field** | `address_stateOrRegion` contains cities, geocodes (`12.9716,77.5946`), JSON fragments | Filter: `LENGTH < 40`, exclude `{` and `[` prefixes |
| **Duplicate scores** | Multiple rows per facility×capability in the scores table | `ROW_NUMBER() OVER (PARTITION BY capability ORDER BY match_count DESC)` — keep the best |
| **App container isolation** | Databricks App container can't access `/Workspace/` filesystem paths at runtime | Images stored as binary blobs in a Delta table, served via SQL query instead of file reads |
| **Performance at scale** | 10k facilities × 15 capabilities = 151k score rows; cold warehouse queries take seconds | In-memory cache on app startup (capabilities, regions, facility names) for instant search/autocomplete |
| **Image name mismatch** | DB: "Jammu And Kashmir" vs file: "Jammu_Kashmir_1.jpg" | Normalize to alpha-only lowercase + fuzzy `startsWith` comparison |

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
| Collaborative review | Assign facilities to specific planners, track review progress |
| Confidence scoring | Weight different signal types differently (equipment > description mention) |

---

## 8. Technical Reference

### Development Workflow — Multi-Modal AI Approach

We used **Databricks AI Gateway + Genie** for data discovery, then **Claude Code + Databricks MCP Server** for iterative development — a true multi-AI approach:

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                     MULTI-MODAL AI DEVELOPMENT WORKFLOW                               │
│                                                                                       │
│  Phase 1: Discovery                      Phase 2: Development                         │
│  ┌──────────────────────────────┐        ┌───────────────────────────────────────┐   │
│  │  Databricks AI Gateway       │        │  Claude Code (IntelliJ IDE Terminal)   │   │
│  │  + Genie                     │        │  + Databricks MCP Server               │   │
│  │                              │        │  + Databricks AI Gateway               │   │
│  │  • Explore 10k facility rows │        │                                        │   │
│  │  • Identify 15 capabilities  │        │  • Expand seed → 5-category map        │   │
│  │  • Generate seed keywords    │        │  • Build scoring engine (Python)        │   │
│  │  • Understand field schemas  │        │  • Build FastAPI + Netflix UI           │   │
│  │                              │        │  • Run SQL, manage tables, debug        │   │
│  └──────────────────────────────┘        │  • Deploy app from terminal             │   │
│              │                            │  • Full iteration loop — never          │   │
│              ▼                            │    left the terminal                    │   │
│     Seed keyword list                     └───────────────────────────────────────┘   │
│     (15 capabilities × flat arrays)                       │                           │
│              │                                            ▼                           │
│              └──────────────────────▶  Live app + scoring engine + audit system       │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**Phase 1 — Genie + AI Gateway (Foundation):**
- Our team used Genie to explore the raw unstructured data across 10k facility records
- Genie identified 15 healthcare capabilities and generated a seed keyword list for each
- This was the foundational data analysis — understanding what's in the data before building anything

**Phase 2 — Claude Code + Databricks MCP Server (Build):**
- From the IntelliJ IDE terminal, Claude Code connected to our Databricks workspace via the **Databricks MCP Server**
- This gave us the ability to: run SQL queries, create/modify tables, upload code, deploy the app, and debug — all in a single conversational loop
- Claude expanded the seed keyword list into a full 5-category map by querying actual data through the MCP connection
- The entire app (scoring engine, FastAPI backend, Netflix UI, override system) was built and deployed iteratively without leaving the terminal

**Key tools in the stack:**

| Tool | Role |
|------|------|
| Databricks AI Gateway | LLM access layer for Genie and AI-powered analysis |
| Genie | Natural language data exploration, generated seed capability map |
| Claude Code | AI coding assistant — wrote all application code |
| Databricks MCP Server | Connected Claude Code to workspace (SQL, tables, files, deploy) |
| Databricks Apps | Hosted the final FastAPI application |

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

### API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve main UI (index.html) |
| `/api/cache-status` | GET | Check if startup cache is ready |
| `/api/capabilities` | GET | List 15 capabilities with facility counts |
| `/api/regions` | GET | List all valid regions with facility counts |
| `/api/hero-regions` | GET | Top 5 regions for hero carousel |
| `/api/top-facilities?limit=` | GET | Facilities with highest total citation counts |
| `/api/strong-evidence?limit=` | GET | Facilities scored as strong evidence |
| `/api/needs-review?limit=` | GET | Weak evidence with match_count ≥ 2 (borderline) |
| `/api/facilities?capability=&region=&trust_level=&limit=&offset=` | GET | Filtered facility list with pagination |
| `/api/facility/{id}?capability=` | GET | Full facility detail + all capability scores |
| `/api/search?q=` | GET | Autocomplete across capabilities, regions, facilities |
| `/api/state-image/{region}` | GET | Serve JPEG image from Delta table |
| `/api/facility/{id}/rescore` | POST | Re-evaluate with edited texts → before/after |
| `/api/facility/{id}/confirm-override` | POST | Write override to audit + update live scores |

### Ranking Logic — Why Things Appear Where They Do

| What you see in the UI | Why it's in that order |
|------------------------|----------------------|
| Maharashtra as first region | Highest `facility_count` in source table |
| First capability listed (e.g., Emergency) | Most facilities with non-"no_claim" scores |
| Top facility in "Top Facilities" row | Highest `SUM(match_count)` across all 15 capabilities |
| Facility tagged "ICU" on its card | Either filtering by ICU, or ICU is its highest-scored capability |
| Strong before Partial in facility list | `ORDER BY trust_priority` (strong=1, partial=2, weak=3, none=4) |
| "Needs Review" row entries | `trust_level = 'weak_evidence' AND match_count >= 2` — borderline cases |

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

---

*Built for DAIS 2026 Hackathon — Track 1*

**Team:** Sonal Jain, Saket Jain

**App:** [facility-trust-desk-7474649205602894.aws.databricksapps.com](https://facility-trust-desk-7474649205602894.aws.databricksapps.com)
