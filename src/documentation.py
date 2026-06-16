# Databricks notebook source
# MAGIC %md
# MAGIC # Facility Trust Desk — Hackathon Documentation
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 1. Inspiration
# MAGIC
# MAGIC > *"Healthcare facilities claim all kinds of capabilities — but how do you know what's genuinely backed by evidence vs. just noise in the data?"*
# MAGIC
# MAGIC - **10,000 facilities** self-report capabilities — no verification layer exists today
# MAGIC - Planners need to evaluate: how strongly is each claim backed by evidence across the data?
# MAGIC - **15 healthcare capabilities × 10k facilities = 150,000 trust decisions** to make
# MAGIC - Manual verification is impossible at this scale
# MAGIC
# MAGIC **Our goal:** Build a trust scoring system that counts evidence signals across multiple data fields, lets planners browse and evaluate claims at scale, and gives them the power to override when they know better.
# MAGIC
# MAGIC **Future enhancement:** Treat specific quantitative claims (e.g., "22-bed ICU") as a strong signal in itself — currently it's counted like any other keyword hit.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 2. What It Does
# MAGIC
# MAGIC > *Think Netflix — but for healthcare facility trust.*
# MAGIC
# MAGIC | Feature | What It Does |
# MAGIC |---------|-------------|
# MAGIC | Browse by Region | Netflix-style rows — click Maharashtra, see its facilities |
# MAGIC | Browse by Capability | Filter to ICU / Cardiology / etc. across all regions |
# MAGIC | Trust Scoring | Every facility×capability pair scored as **Strong / Partial / Weak / No Claim** |
# MAGIC | Re-evaluate | Edit evidence text, see trust level change live |
# MAGIC | Override with Audit | Confirm the change — writes to audit log AND updates live scores |
# MAGIC | Cross-filter Search | Maharashtra + ICU + Cardiology — AND logic |
# MAGIC
# MAGIC **Live app:** [facility-trust-desk-7474649205602894.aws.databricksapps.com](https://facility-trust-desk-7474649205602894.aws.databricksapps.com)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 3. How We Built It
# MAGIC
# MAGIC ### Our Multi-AI Approach
# MAGIC
# MAGIC We used a **multi-modal AI approach** combining Databricks AI Gateway and Genie for initial analysis, then Claude Code with Databricks MCP Server for iterative development:
# MAGIC
# MAGIC ```
# MAGIC ┌─────────────────────────────────────────────────────────────────────────────────────┐
# MAGIC │                         MULTI-AI DEVELOPMENT APPROACH                                │
# MAGIC │                                                                                      │
# MAGIC │  Phase 1: Discovery & Foundation          Phase 2: Build & Deploy                    │
# MAGIC │  ┌───────────────────────────────┐        ┌────────────────────────────────────┐    │
# MAGIC │  │  Databricks Genie             │        │  Claude Code (IntelliJ Terminal)    │    │
# MAGIC │  │  + AI Gateway                 │        │  + Databricks MCP Server            │    │
# MAGIC │  │                               │        │  + Databricks AI Gateway            │    │
# MAGIC │  │  • Explore raw data           │        │                                     │    │
# MAGIC │  │  • Identify 15 capabilities   │        │  • Expand keyword map per category  │    │
# MAGIC │  │  • Generate seed keyword list  │        │  • Build scoring engine             │    │
# MAGIC │  │  • Understand field structure  │        │  • Build FastAPI app + UI           │    │
# MAGIC │  └───────────────────────────────┘        │  • Deploy & iterate                 │    │
# MAGIC │              │                             └────────────────────────────────────┘    │
# MAGIC │              ▼                                            │                          │
# MAGIC │     Seed list (15 caps × flat keywords)                   ▼                          │
# MAGIC │              │                             Full 5-category keyword map                │
# MAGIC │              └──────────────────────────── + Working app + Live deployment           │
# MAGIC └─────────────────────────────────────────────────────────────────────────────────────┘
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Act 1: The Capability Map (most important piece)
# MAGIC
# MAGIC **How we built the map — step by step:**
# MAGIC
# MAGIC 1. **Genie explored the raw data** — our team fed the unstructured facility text to Genie and asked: "what healthcare capabilities are described across these 10k records?" Genie identified 15 distinct capability categories.
# MAGIC
# MAGIC 2. **Genie produced a seed keyword list** — for each capability, a flat array of core keywords that signal its presence:
# MAGIC    ```
# MAGIC    "ICU": ["icu", "intensive care", "critical care", "intensive care unit", ...]
# MAGIC    "NICU": ["nicu", "neonatal", "newborn intensive care", ...]
# MAGIC    "Maternity": ["maternity", "obstetrics", "labor", "delivery", ...]
# MAGIC    ```
# MAGIC
# MAGIC 3. **Claude Code expanded per category** — using Databricks MCP Server to query the actual data, Claude expanded the flat list into a structured 5-category map:
# MAGIC    - Distributed seed keywords to the correct categories (e.g., "ventilator" → equipment)
# MAGIC    - Added field-specific terms by analyzing what actually appears in each field (equipment names, procedure terms, specialty codes)
# MAGIC    - Added reasonable synonyms and variations as a "wishlist" — if they appear in the data, they'll match; if not, no harm
# MAGIC
# MAGIC 4. **Keywords are search terms, not extracted phrases** — the map is a collection of substring patterns, not an inventory of exact values found in the data. Keyword `"neonatal"` will catch `"Neonatal Intensive Care"`, `"neonatal resuscitation"`, etc. Some keywords may have zero matches across all facilities — they're there for completeness.
# MAGIC
# MAGIC **The final map structure (15 capabilities × 5 categories × N keywords each):**
# MAGIC
# MAGIC | Capability | capability field keywords | equipment field | procedure field | specialties field |
# MAGIC |-----------|--------------------------|-----------------|-----------------|-------------------|
# MAGIC | ICU | icu, intensive care, critical care | ventilator, cardiac monitor | mechanical ventilation, intubation | criticalCareMedicine |
# MAGIC | Maternity | maternity, labour room, delivery | fetal monitor, infant warmer | c-section, normal delivery | gynecologyAndObstetrics |
# MAGIC | Cardiology | cardiology, cardiac, cath lab | echocardiography, stent | angioplasty, bypass | interventionalCardiology |
# MAGIC | Emergency | emergency, 24x7, casualty | ambulance, defibrillator | trauma, resuscitation | emergencyMedicine |
# MAGIC | Oncology | oncology, cancer, chemotherapy | linear accelerator, pet-ct | chemotherapy, radiation | medicalOncology |

# COMMAND ----------

# MAGIC %md
# MAGIC ### Act 2: The Scoring Engine
# MAGIC
# MAGIC > *No LLM. No API calls. Pure keyword matching — fast and deterministic.*
# MAGIC
# MAGIC #### The Core Idea: Categories as Independent Signals
# MAGIC
# MAGIC Each capability in our map has keywords organized into **5 categories** (fields from the source data):
# MAGIC
# MAGIC | Category | What it represents | Example (NICU) |
# MAGIC |----------|-------------------|----------------|
# MAGIC | **capability** | Services the facility lists as offerings | "nicu", "neonatal intensive care" |
# MAGIC | **equipment** | Physical equipment/devices on site | "incubator", "infant warmer", "phototherapy" |
# MAGIC | **procedure** | Medical procedures performed | "neonatal resuscitation", "exchange transfusion" |
# MAGIC | **specialties** | Registered medical specialty codes | `neonatologyPerinatalMedicine` |
# MAGIC | **description** | Free-text facility description | "nicu", "neonatal", "newborn intensive" |
# MAGIC
# MAGIC **Trust is determined by how many of these 5 categories show evidence.** Each category that has at least one keyword match counts as one independent signal. The logic:
# MAGIC - If only the `specialties` field mentions it → that's 1 category → not strongly backed
# MAGIC - If `specialties` AND `equipment` both mention it → 2 categories → more confidence
# MAGIC - If `specialties` + `equipment` + `procedure` all mention it → 3 categories → strong — the facility has the specialty code, owns the equipment, AND performs the procedures
# MAGIC
# MAGIC ```
# MAGIC ┌─────────────┐     ┌────────────────┐     ┌──────────────────┐     ┌────────────────┐
# MAGIC │ Facility    │ ──▶ │ Parse fields   │ ──▶ │ Match keywords   │ ──▶ │ Count & Decide │
# MAGIC │ raw fields  │     │ (JSON arrays)  │     │ (substring)      │     │ trust level    │
# MAGIC └─────────────┘     └────────────────┘     └──────────────────┘     └────────────────┘
# MAGIC                                                     │
# MAGIC                                             ┌───────▼────────┐
# MAGIC                                             │ Record citation│
# MAGIC                                             │ {field, text}  │
# MAGIC                                             └────────────────┘
# MAGIC ```
# MAGIC
# MAGIC **How it works step by step:**
# MAGIC 1. For each facility × capability pair: parse each category's JSON array into text items
# MAGIC 2. Substring-match each item against the capability's keywords for that category
# MAGIC 3. Record every match as a citation: `{field: "equipment", text: "infant warmer"}`
# MAGIC 4. Count **categories matched** (how many of the 5 categories had at least one hit) and **total hits** (sum of all keyword matches)
# MAGIC 5. Determine trust level based on thresholds:
# MAGIC
# MAGIC **Trust Level Decision Table:**
# MAGIC
# MAGIC | Trust Level | Condition | What it means |
# MAGIC |-------------|-----------|---------------|
# MAGIC | Trust Level | Path 1: Category Spread | Path 2: Sheer Volume | Intuition |
# MAGIC |-------------|------------------------|---------------------|-----------|
# MAGIC | **Strong** | 3+ categories matched | OR 5+ total hits (even in 1 category) | Either confirmed across multiple independent sources, OR overwhelming keyword density in the data |
# MAGIC | **Partial** | 2+ categories matched | OR 3+ total hits (even in 1 category) | Either evidence in 2 categories, OR enough repetition to suggest real capability |
# MAGIC | **Weak** | 1 category with a hit | (fewer than 3 total hits) | Mentioned somewhere but not strongly backed |
# MAGIC | **No Claim** | — | 0 matches | Capability not found anywhere in the facility's data |
# MAGIC
# MAGIC *Additionally: a quantitative claim (e.g., "22-bed ICU") + 2+ categories → Strong (lowers the spread threshold by 1).*
# MAGIC
# MAGIC **Quantitative detection code:**
# MAGIC ```python
# MAGIC def _has_quantitative_claim(citations):
# MAGIC     quant_pattern = re.compile(r'\d+[\s-]*(bed|unit|theatre|ot |ventilator|machine|doctor)', re.IGNORECASE)
# MAGIC     for cite in citations:
# MAGIC         if quant_pattern.search(cite["text"]):
# MAGIC             return True
# MAGIC     return False
# MAGIC
# MAGIC def _determine_trust_level(fields_matched, match_count, has_quant):
# MAGIC     num_fields = len(fields_matched)
# MAGIC     if num_fields >= 3 or match_count >= 5 or (has_quant and num_fields >= 2):
# MAGIC         return "strong_evidence"
# MAGIC     ...
# MAGIC ```
# MAGIC *The regex detects patterns like "22-bed", "5 ventilator", "10 unit" in citation text. If found AND 2+ categories matched → promotes to Strong.*
# MAGIC
# MAGIC **Worked example — NICU scoring for a facility:**
# MAGIC
# MAGIC | Category | Items in facility data | Keyword matched? | Hits |
# MAGIC |----------|----------------------|------------------|------|
# MAGIC | capability | ["General Medicine", "Pediatrics"] | No NICU keywords found | 0 |
# MAGIC | equipment | ["Incubator", "Radiant Warmer", "Ventilator"] | "incubator" ✓, "radiant warmer" ✓ | 2 |
# MAGIC | procedure | ["Neonatal Resuscitation", "Phototherapy"] | "neonatal resuscitation" ✓, "phototherapy" ✓ | 2 |
# MAGIC | specialties | ["neonatologyPerinatalMedicine"] | Exact match ✓ | 1 |
# MAGIC | description | "Multi-specialty hospital" | No NICU keywords | 0 |
# MAGIC
# MAGIC **Result:** 3 categories matched (equipment + procedure + specialties), 5 total hits → **Strong Evidence** (qualifies via BOTH paths)
# MAGIC
# MAGIC > **Key insight:** There are two ways to reach a higher trust level:
# MAGIC > - **Category spread** — evidence across multiple independent categories (strongest signal)
# MAGIC > - **Keyword density** — enough hits even in a single category (e.g., a facility lists 5 NICU-related items in their equipment field alone → Strong via Path 2)
# MAGIC >
# MAGIC > Both paths are valid. Category spread means independent corroboration. Keyword density means the data is rich with references even if concentrated in one area.
# MAGIC
# MAGIC > **Future enhancement:** Treat specific quantitative claims (e.g., "22-bed ICU") as a strong signal in itself — currently counted like any other keyword hit.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example: See the scoring in action for a real facility
# MAGIC SELECT facility_id, capability, trust_level, match_count, fields_matched, evidence_citations
# MAGIC FROM workspace.default.facility_trust_scores
# MAGIC WHERE trust_level = 'strong_evidence'
# MAGIC ORDER BY match_count DESC
# MAGIC LIMIT 5

# COMMAND ----------

# MAGIC %md
# MAGIC ### Act 3: Front-end Stack
# MAGIC
# MAGIC | Layer | Choice | Why |
# MAGIC |-------|--------|-----|
# MAGIC | Backend | FastAPI (Python) | Single file, no external ML deps, Databricks App compatible |
# MAGIC | Frontend | Vanilla HTML/CSS/JS | No React, no build step, no framework overhead |
# MAGIC | UI Theme | Netflix dark | Horizontal scroll rows, card-based browsing |
# MAGIC | Deployment | Databricks App | Source code snapshot from workspace folder |
# MAGIC | Images | Binary blobs in Delta table | App container can't access `/Workspace/` paths |

# COMMAND ----------

# MAGIC %md
# MAGIC ### Act 4: State Images
# MAGIC
# MAGIC ```
# MAGIC ┌──────────────────┐    SQL read_files()    ┌─────────────────────┐    /api/state-image/    ┌──────┐
# MAGIC │ /Workspace/final/│ ─────────────────────▶ │ state_images_data   │ ─────────────────────▶ │ JPEG │
# MAGIC │ (image files)    │                        │ (Delta: filename +  │     fuzzy match        │ resp │
# MAGIC └──────────────────┘                        │  binary content)    │                        └──────┘
# MAGIC                                             └─────────────────────┘
# MAGIC ```
# MAGIC
# MAGIC **Fuzzy matching logic:** Normalize both state names (DB) and filenames to lowercase alpha-only, then `startsWith` comparison handles cases like "Jammu And Kashmir" → `jammuandkashmir` matching `jammukashmir` from filename `Jammu_Kashmir.jpg`.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Act 5: Override & Audit Flow
# MAGIC
# MAGIC ```
# MAGIC Planner edits citation pills in the UI
# MAGIC         │
# MAGIC         ▼
# MAGIC   POST /api/facility/{id}/rescore
# MAGIC   → Runs score_facility() with edited texts
# MAGIC   → Returns {before: {...}, after: {...}}
# MAGIC         │
# MAGIC         ▼
# MAGIC   UI shows Before / After diff (trust level, citations)
# MAGIC   Planner adds a note, clicks "Confirm Override"
# MAGIC         │
# MAGIC         ▼
# MAGIC   POST /api/facility/{id}/confirm-override
# MAGIC   → INSERT INTO user_overrides (full audit record)
# MAGIC   → UPDATE facility_trust_scores (live scores table)
# MAGIC         │
# MAGIC         ▼
# MAGIC   Change is visible immediately across the entire app
# MAGIC ```
# MAGIC
# MAGIC **Two writes on every confirm:**
# MAGIC 1. **`user_overrides`** — immutable audit record (override_id, facility_id, capability, all edited texts, old/new trust levels, old/new citations, note, timestamp)
# MAGIC 2. **`facility_trust_scores`** — UPDATE the live row with new trust_level, citations, fields_matched, match_count, scored_at
# MAGIC
# MAGIC This means overrides are **immediately reflected** everywhere in the app AND **fully auditable**.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- View recent overrides (audit trail)
# MAGIC SELECT id, facility_id, capability_scored, old_trust_level, new_trust_level, note, confirmed_at
# MAGIC FROM workspace.default.user_overrides
# MAGIC ORDER BY confirmed_at DESC
# MAGIC LIMIT 10

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 4. Challenges We Ran Into
# MAGIC
# MAGIC | Challenge | What We Found | How We Solved It |
# MAGIC |-----------|--------------|-----------------|
# MAGIC | **Messy state field** | `address_stateOrRegion` contains cities, geocodes (`12.9716,77.5946`), JSON fragments | Filter: `LENGTH < 40`, exclude `{` and `[` prefixes |
# MAGIC | **Duplicate scores** | Multiple rows per facility×capability in the scores table | `ROW_NUMBER() OVER (PARTITION BY capability ORDER BY match_count DESC)` — keep the best |
# MAGIC | **App container isolation** | Databricks App container can't access `/Workspace/` filesystem paths at runtime | Images stored as binary blobs in a Delta table, served via SQL query instead of file reads |
# MAGIC | **Performance at scale** | 10k facilities × 15 capabilities = 151k score rows; cold warehouse queries take seconds | In-memory cache on app startup (capabilities, regions, facility names) for instant search/autocomplete |
# MAGIC | **Image name mismatch** | DB: "Jammu And Kashmir" vs file: "Jammu_Kashmir_1.jpg" | Normalize to alpha-only lowercase + fuzzy `startsWith` comparison |

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example of the messy state data we had to handle
# MAGIC SELECT address_stateOrRegion, COUNT(*) as cnt
# MAGIC FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
# MAGIC WHERE address_stateOrRegion IS NOT NULL
# MAGIC GROUP BY address_stateOrRegion
# MAGIC ORDER BY cnt DESC
# MAGIC LIMIT 20

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 5. Accomplishments
# MAGIC
# MAGIC - **Zero-LLM scoring** — runs in milliseconds, no API cost, fully deterministic
# MAGIC - **Full audit trail** — every override is traceable with before/after values + planner note + timestamp
# MAGIC - **Live propagation** — overrides update the scores table immediately, visible everywhere
# MAGIC - **Netflix UX** — 10,000 facilities feel browseable, not overwhelming
# MAGIC - **Cross-filter AND search** — "Maharashtra + ICU + Cardiology" just works
# MAGIC - **Fuzzy image matching** — gracefully handles messy state names and inconsistent filenames
# MAGIC - **Genie-powered foundation** — the capability map was generated from raw data, not hand-crafted

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 6. What We Learned
# MAGIC
# MAGIC - **Keyword scoring is surprisingly effective** — when the capability map is well-curated (Genie produced a great initial map from raw text)
# MAGIC - **Trust thresholds need tuning** — too strict misses real capabilities, too loose flags everything as "strong"
# MAGIC - **Quantitative claims feel strong but aren't (yet)** — "22-bed ICU" is counted as one keyword hit today; treating it as inherently stronger is a future enhancement
# MAGIC - **Databricks Apps have constraints** — powerful for rapid deployment, but app containers can't access `/Workspace/` paths directly (hence the Delta-table image solution)
# MAGIC - **Caching makes everything feel instant** — startup cache for metadata eliminates repeated SQL for search/autocomplete

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 7. What's Next
# MAGIC
# MAGIC | Enhancement | Impact |
# MAGIC |-------------|--------|
# MAGIC | LLM second pass | Semantic verification of keyword matches — does the text *mean* the facility has this capability? |
# MAGIC | Quantitative claim weighting | "22-bed ICU" counts as a strong signal by itself |
# MAGIC | Bulk override workflow | Approve/reject multiple facilities at once |
# MAGIC | External verification | Cross-reference with government registry, accreditation databases |
# MAGIC | Collaborative review | Assign facilities to specific planners, track review progress |
# MAGIC | Confidence scoring | Weight different signal types differently (equipment > description mention) |

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 8. Technical Reference
# MAGIC
# MAGIC ### Development Workflow — Multi-Modal AI Approach
# MAGIC
# MAGIC We used **Databricks AI Gateway + Genie** for data discovery, then **Claude Code + Databricks MCP Server** for iterative development — a true multi-AI approach:
# MAGIC
# MAGIC ```
# MAGIC ┌──────────────────────────────────────────────────────────────────────────────────────┐
# MAGIC │                     MULTI-MODAL AI DEVELOPMENT WORKFLOW                               │
# MAGIC │                                                                                       │
# MAGIC │  Phase 1: Discovery                      Phase 2: Development                         │
# MAGIC │  ┌──────────────────────────────┐        ┌───────────────────────────────────────┐   │
# MAGIC │  │  Databricks AI Gateway       │        │  Claude Code (IntelliJ IDE Terminal)   │   │
# MAGIC │  │  + Genie                     │        │  + Databricks MCP Server               │   │
# MAGIC │  │                              │        │  + Databricks AI Gateway               │   │
# MAGIC │  │  • Explore 10k facility rows │        │                                        │   │
# MAGIC │  │  • Identify 15 capabilities  │        │  • Expand seed → 5-category map        │   │
# MAGIC │  │  • Generate seed keywords    │        │  • Build scoring engine (Python)        │   │
# MAGIC │  │  • Understand field schemas  │        │  • Build FastAPI + Netflix UI           │   │
# MAGIC │  │                              │        │  • Run SQL, manage tables, debug        │   │
# MAGIC │  └──────────────────────────────┘        │  • Deploy app from terminal             │   │
# MAGIC │              │                            │  • Full iteration loop — never          │   │
# MAGIC │              ▼                            │    left the terminal                    │   │
# MAGIC │     Seed keyword list                     └───────────────────────────────────────┘   │
# MAGIC │     (15 capabilities × flat arrays)                       │                           │
# MAGIC │              │                                            ▼                           │
# MAGIC │              └──────────────────────▶  Live app + scoring engine + audit system       │
# MAGIC └──────────────────────────────────────────────────────────────────────────────────────┘
# MAGIC ```
# MAGIC
# MAGIC **Phase 1 — Genie + AI Gateway (Foundation):**
# MAGIC - Our team used Genie to explore the raw unstructured data across 10k facility records
# MAGIC - Genie identified 15 healthcare capabilities and generated a seed keyword list for each
# MAGIC - This was the foundational data analysis — understanding what's in the data before building anything
# MAGIC
# MAGIC **Phase 2 — Claude Code + Databricks MCP Server (Build):**
# MAGIC - From the IntelliJ IDE terminal, Claude Code connected to our Databricks workspace via the **Databricks MCP Server**
# MAGIC - This gave us the ability to: run SQL queries, create/modify tables, upload code, deploy the app, and debug — all in a single conversational loop
# MAGIC - Claude expanded the seed keyword list into a full 5-category map by querying actual data through the MCP connection
# MAGIC - The entire app (scoring engine, FastAPI backend, Netflix UI, override system) was built and deployed iteratively without leaving the terminal
# MAGIC
# MAGIC **Key tools in the stack:**
# MAGIC | Tool | Role |
# MAGIC |------|------|
# MAGIC | Databricks AI Gateway | LLM access layer for Genie and AI-powered analysis |
# MAGIC | Genie | Natural language data exploration, generated seed capability map |
# MAGIC | Claude Code | AI coding assistant — wrote all application code |
# MAGIC | Databricks MCP Server | Connected Claude Code to workspace (SQL, tables, files, deploy) |
# MAGIC | Databricks Apps | Hosted the final FastAPI application |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Data Architecture
# MAGIC
# MAGIC ```
# MAGIC ┌───────────────────────────────────────────────────────────────────┐
# MAGIC │                        SOURCE OF TRUTH                             │
# MAGIC │  databricks_virtue_foundation_dataset_dais_2026                    │
# MAGIC │  .virtue_foundation_dataset.facilities  (10,088 rows)              │
# MAGIC │                                                                    │
# MAGIC │  Fields: unique_id, name, capability[], procedure[], equipment[],  │
# MAGIC │          specialties[], description, address_city,                  │
# MAGIC │          address_stateOrRegion, ...                                 │
# MAGIC └──────────────────────────────┬────────────────────────────────────┘
# MAGIC                                │ scored by keyword engine
# MAGIC                                ▼
# MAGIC ┌───────────────────────────────────────────────────────────────────┐
# MAGIC │  workspace.default.facility_trust_scores  (~150,000 rows)          │
# MAGIC │                                                                    │
# MAGIC │  Columns: facility_id, capability, trust_level, match_count,       │
# MAGIC │           fields_matched (JSON array), evidence_citations (JSON),   │
# MAGIC │           scored_at                                                 │
# MAGIC │                                                                    │
# MAGIC │  One row per facility × capability (deduped at query time)         │
# MAGIC └──────────────────┬────────────────────────────────────────────────┘
# MAGIC                    │ on override: UPDATE live row
# MAGIC                    │
# MAGIC ┌──────────────────▼────────────────────────────────────────────────┐
# MAGIC │  workspace.default.user_overrides  (audit log — append only)       │
# MAGIC │                                                                    │
# MAGIC │  Columns: id, facility_id, capability_scored,                      │
# MAGIC │           edited_capability, edited_procedure, edited_equipment,    │
# MAGIC │           edited_specialties, edited_description,                   │
# MAGIC │           old_trust_level, new_trust_level,                         │
# MAGIC │           old_citations, new_citations,                             │
# MAGIC │           note, confirmed_at                                        │
# MAGIC │                                                                    │
# MAGIC │  INSERT on every confirm (immutable — never updated or deleted)    │
# MAGIC └───────────────────────────────────────────────────────────────────┘
# MAGIC ```

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Table stats
# MAGIC SELECT 'facilities (source)' as table_name, COUNT(*) as row_count FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
# MAGIC UNION ALL
# MAGIC SELECT 'facility_trust_scores', COUNT(*) FROM workspace.default.facility_trust_scores
# MAGIC UNION ALL
# MAGIC SELECT 'user_overrides', COUNT(*) FROM workspace.default.user_overrides
# MAGIC UNION ALL
# MAGIC SELECT 'state_images_data', COUNT(*) FROM workspace.default.state_images_data

# COMMAND ----------

# MAGIC %md
# MAGIC ### API Reference
# MAGIC
# MAGIC | Endpoint | Method | Purpose |
# MAGIC |----------|--------|---------|
# MAGIC | `/` | GET | Serve main UI (index.html) |
# MAGIC | `/api/cache-status` | GET | Check if startup cache is ready |
# MAGIC | `/api/capabilities` | GET | List 15 capabilities with facility counts |
# MAGIC | `/api/regions` | GET | List all valid regions with facility counts |
# MAGIC | `/api/hero-regions` | GET | Top 5 regions for hero carousel |
# MAGIC | `/api/top-facilities?limit=` | GET | Facilities with highest total citation counts |
# MAGIC | `/api/strong-evidence?limit=` | GET | Facilities scored as strong evidence |
# MAGIC | `/api/needs-review?limit=` | GET | Weak evidence with match_count ≥ 2 (borderline) |
# MAGIC | `/api/facilities?capability=&region=&trust_level=&limit=&offset=` | GET | Filtered facility list with pagination |
# MAGIC | `/api/facility/{id}?capability=` | GET | Full facility detail + all capability scores |
# MAGIC | `/api/search?q=` | GET | Autocomplete across capabilities, regions, facilities |
# MAGIC | `/api/state-image/{region}` | GET | Serve JPEG image from Delta table |
# MAGIC | `/api/facility/{id}/rescore` | POST | Re-evaluate with edited texts → before/after |
# MAGIC | `/api/facility/{id}/confirm-override` | POST | Write override to audit + update live scores |

# COMMAND ----------

# MAGIC %md
# MAGIC ### Ranking Logic — Why Things Appear Where They Do
# MAGIC
# MAGIC | What you see in the UI | Why it's in that order |
# MAGIC |------------------------|----------------------|
# MAGIC | Maharashtra as first region | Highest `facility_count` in source table |
# MAGIC | First capability listed (e.g., Emergency) | Most facilities with non-"no_claim" scores |
# MAGIC | Top facility in "Top Facilities" row | Highest `SUM(match_count)` across all 15 capabilities |
# MAGIC | Facility tagged "ICU" on its card | Either filtering by ICU, or ICU is its highest-scored capability |
# MAGIC | Strong before Partial in facility list | `ORDER BY trust_priority` (strong=1, partial=2, weak=3, none=4) |
# MAGIC | "Needs Review" row entries | `trust_level = 'weak_evidence' AND match_count >= 2` — borderline cases |

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Why Maharashtra is first: top regions by facility count
# MAGIC SELECT address_stateOrRegion as region, COUNT(*) as facility_count
# MAGIC FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
# MAGIC WHERE address_stateOrRegion IS NOT NULL
# MAGIC   AND LENGTH(address_stateOrRegion) < 40
# MAGIC   AND address_stateOrRegion NOT LIKE '{%'
# MAGIC   AND address_stateOrRegion NOT LIKE '[%'
# MAGIC GROUP BY address_stateOrRegion
# MAGIC ORDER BY facility_count DESC
# MAGIC LIMIT 10

# COMMAND ----------

# MAGIC %md
# MAGIC ### Image Refresh Procedure
# MAGIC
# MAGIC When new state images are added to `/Workspace/Users/sonal.0403@gmail.com/final/`:
# MAGIC
# MAGIC ```sql
# MAGIC -- Step 1: Reload images from the workspace folder into Delta
# MAGIC CREATE OR REPLACE TABLE workspace.default.state_images_data AS
# MAGIC SELECT regexp_extract(path, '([^/]+)$', 1) as filename, content
# MAGIC FROM read_files('/Workspace/Users/sonal.0403@gmail.com/final/', format => 'binaryFile')
# MAGIC ```
# MAGIC
# MAGIC Then redeploy the app to clear the in-memory filename index (it caches on first request).
# MAGIC
# MAGIC The fuzzy matching handles inconsistencies like:
# MAGIC - `"Maharashtra"` → normalized → `maharashtra` → matches file `Maharashtra_1.jpg` (normalized: `maharashtra`)
# MAGIC - `"Jammu And Kashmir"` → normalized → `jammuandkashmir` → `startsWith` match with `jammukashmir`

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Current state images in the table
# MAGIC SELECT filename, LENGTH(content) as size_bytes
# MAGIC FROM workspace.default.state_images_data
# MAGIC ORDER BY filename

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ### Trust Level Distribution (live)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- How are the 150k scores distributed across trust levels?
# MAGIC SELECT trust_level, COUNT(*) as score_count,
# MAGIC        COUNT(DISTINCT facility_id) as facilities_affected,
# MAGIC        ROUND(AVG(match_count), 1) as avg_match_count
# MAGIC FROM workspace.default.facility_trust_scores
# MAGIC GROUP BY trust_level
# MAGIC ORDER BY CASE trust_level
# MAGIC     WHEN 'strong_evidence' THEN 1
# MAGIC     WHEN 'partial_evidence' THEN 2
# MAGIC     WHEN 'weak_evidence' THEN 3
# MAGIC     ELSE 4
# MAGIC END

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC *Built for DAIS 2026 Hackathon — Track 1*
# MAGIC
# MAGIC **Team:** Sonal Jain
# MAGIC
# MAGIC **App:** [facility-trust-desk-7474649205602894.aws.databricksapps.com](https://facility-trust-desk-7474649205602894.aws.databricksapps.com)
