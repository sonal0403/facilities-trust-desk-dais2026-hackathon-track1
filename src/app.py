"""
Facility Trust Desk — Databricks App (FastAPI)

Netflix-style UI with override/re-score capability.
Caches metadata on startup for fast search. Inline scoring engine for re-evaluation.
"""

import os
import json
import re
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from databricks import sql as dbsql

app = FastAPI(title="Facility Trust Desk")

APP_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

# Connection config
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST","<>")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN","<>")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "<>")
HTTP_PATH = f"/sql/1.0/warehouses/{WAREHOUSE_ID}"

SOURCE_TABLE = "databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities"
SCORES_TABLE = "workspace.default.facility_trust_scores"
OVERRIDES_TABLE = "workspace.default.user_overrides"

# ─── In-memory cache ─────────────────────────────────────────────────────────
cache = {
    "ready": False,
    "capabilities": [],
    "regions": [],
    "facilities": [],
}


def get_connection():
    return dbsql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
    )


def run_query(sql):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def run_statement(sql):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
    finally:
        conn.close()


def load_cache():
    try:
        cache["capabilities"] = run_query(f"""
            SELECT capability, COUNT(DISTINCT facility_id) as facility_count
            FROM {SCORES_TABLE}
            WHERE trust_level != 'no_claim'
            GROUP BY capability
            ORDER BY facility_count DESC
        """)

        cache["regions"] = run_query(f"""
            SELECT address_stateOrRegion as region, COUNT(*) as facility_count
            FROM {SOURCE_TABLE}
            WHERE address_stateOrRegion IS NOT NULL
              AND LENGTH(address_stateOrRegion) < 40
              AND address_stateOrRegion NOT LIKE '{{%'
              AND address_stateOrRegion NOT LIKE '[%'
            GROUP BY address_stateOrRegion
            ORDER BY facility_count DESC
        """)

        cache["facilities"] = run_query(f"""
            SELECT unique_id, name, address_city, address_stateOrRegion as region
            FROM {SOURCE_TABLE}
            WHERE name IS NOT NULL
        """)

        cache["ready"] = True
    except Exception as e:
        print(f"Cache load error: {e}")
        cache["ready"] = False


def ensure_overrides_table():
    try:
        run_statement(f"""
            CREATE TABLE IF NOT EXISTS {OVERRIDES_TABLE} (
                id STRING,
                facility_id STRING,
                capability_scored STRING,
                edited_capability STRING,
                edited_procedure STRING,
                edited_equipment STRING,
                edited_specialties STRING,
                edited_description STRING,
                old_trust_level STRING,
                new_trust_level STRING,
                old_citations STRING,
                new_citations STRING,
                note STRING,
                confirmed_at STRING
            )
        """)
    except Exception as e:
        print(f"Table creation note: {e}")


@app.on_event("startup")
def startup_event():
    threading.Thread(target=load_cache, daemon=True).start()
    threading.Thread(target=ensure_overrides_table, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════════
# INLINE SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

CAPABILITY_KEYWORDS = {
    "ICU": {
        "capability": ["icu", "intensive care unit", "intensive care", "critical care", "critical care unit", "ventilator beds", "ventilator bed", "level ii icu", "level iii icu", "medical icu", "surgical icu", "cardiac icu"],
        "equipment": ["ventilator", "icu", "cardiac monitor", "central monitoring", "bedside monitor", "defibrillator", "infusion pump", "pulse oximeter", "cpap", "bipap"],
        "procedure": ["mechanical ventilation", "invasive ventilation", "non-invasive ventilation", "critical care", "intubation", "central line"],
        "specialties": ["criticalCareMedicine"],
        "description": ["icu", "intensive care", "critical care"],
    },
    "Maternity": {
        "capability": ["maternity", "labour room", "labor room", "delivery room", "obstetrics", "obstetric", "antenatal", "postnatal", "prenatal", "maternity ward", "delivery services", "birthing", "normal delivery", "cesarean", "c-section", "labor", "delivery"],
        "equipment": ["fetal monitor", "fetal doppler", "doppler", "ctg", "cardiotocograph", "delivery table", "infant warmer", "radiant warmer"],
        "procedure": ["delivery", "deliveries", "c-section", "cesarean", "caesarean", "csection", "normal delivery", "vaginal delivery", "obstetric", "episiotomy", "labor", "labour"],
        "specialties": ["gynecologyAndObstetrics", "obstetricsAndMaternityCare", "maternalFetalMedicineOrPerinatology", "familyPlanningAndComplexContraception"],
        "description": ["maternity", "obstetric", "delivery", "labour room", "labor room", "antenatal", "birthing", "prenatal", "postnatal"],
    },
    "Emergency": {
        "capability": ["emergency", "24x7", "24/7", "24 x 7", "round the clock", "accident", "casualty", "trauma centre", "trauma center", "emergency department", "emergency room", "emergency services", "urgent care"],
        "equipment": ["ambulance", "defibrillator", "crash cart", "emergency", "trauma"],
        "procedure": ["emergency", "trauma", "resuscitation", "triage", "stabilization"],
        "specialties": ["emergencyMedicine", "pediatricEmergencyMedicine"],
        "description": ["emergency", "24x7", "24/7", "casualty", "accident", "round the clock", "urgent care"],
    },
    "Oncology": {
        "capability": ["oncology", "cancer", "chemotherapy", "radiation therapy", "radiotherapy", "tumor", "tumour", "malignancy", "cancer care", "cancer treatment", "cancer hospital", "bone marrow transplant", "bmt"],
        "equipment": ["linear accelerator", "linac", "cobalt", "brachytherapy", "pet-ct", "pet ct", "pet scan", "cyberknife", "gamma knife"],
        "procedure": ["chemotherapy", "radiation", "radiotherapy", "bone marrow transplant", "bmt", "stem cell transplant", "mastectomy", "lumpectomy", "biopsy", "immunotherapy", "targeted therapy"],
        "specialties": ["medicalOncology", "surgicalOncology", "gynecologicOncology", "gynecologicalOncology", "radiationOncology", "pediatricHematologyOncology"],
        "description": ["oncology", "cancer", "chemotherapy", "radiation", "tumor", "malignancy"],
    },
    "Trauma": {
        "capability": ["trauma", "polytrauma", "trauma centre", "trauma center", "trauma unit", "fracture management", "trauma care", "trauma surgery", "burns management", "burn unit", "level i trauma", "level ii trauma", "level iii trauma"],
        "equipment": ["trauma", "c-arm", "fluoroscopy", "orthopedic implant", "external fixator", "traction"],
        "procedure": ["fracture", "trauma surgery", "polytrauma", "open reduction", "internal fixation", "orif", "external fixation", "debridement", "skin grafting", "flap surgery"],
        "specialties": ["burnAndTraumaPlasticSurgery", "orthopedicSurgery", "traumaSurgery"],
        "description": ["trauma", "polytrauma", "fracture", "burns"],
    },
    "NICU": {
        "capability": ["nicu", "neonatal intensive care", "neonatal intensive care unit", "neonatal icu", "newborn icu", "newborn intensive care", "neonatal care", "newborn care", "level ii nicu", "level iii nicu", "sick newborn", "preterm"],
        "equipment": ["incubator", "infant warmer", "radiant warmer", "phototherapy", "neonatal ventilator", "cpap", "nasal cpap", "bubble cpap", "infant flow", "neonatal monitor"],
        "procedure": ["neonatal resuscitation", "exchange transfusion", "surfactant", "phototherapy", "kangaroo care"],
        "specialties": ["neonatologyPerinatalMedicine"],
        "description": ["nicu", "neonatal", "newborn intensive"],
    },
    "Cardiology": {
        "capability": ["cardiology", "cardiac", "heart", "cardiovascular", "coronary", "interventional cardiology", "cardiac surgery", "open heart", "bypass", "cath lab", "cardiac catheterization"],
        "equipment": ["cath lab", "echocardiography", "ecg", "ekg", "holter", "treadmill", "angiography", "pacemaker", "defibrillator", "stent"],
        "procedure": ["angioplasty", "angiography", "bypass", "cabg", "stenting", "pacemaker", "valve replacement", "echocardiography", "cardiac catheterization", "coronary intervention"],
        "specialties": ["cardiology", "interventionalCardiology", "cardiothoracicSurgery", "cardiacSurgery", "pediatricCardiology"],
        "description": ["cardiology", "cardiac", "heart", "cardiovascular", "coronary"],
    },
    "Orthopedics": {
        "capability": ["orthopedic", "orthopaedic", "joint replacement", "bone", "fracture", "spine", "joint", "musculoskeletal", "sports medicine"],
        "equipment": ["c-arm", "fluoroscopy", "arthroscopy", "orthopedic implant", "external fixator", "traction", "bone drill"],
        "procedure": ["joint replacement", "knee replacement", "hip replacement", "arthroscopy", "fracture fixation", "spinal surgery", "spine surgery", "total knee", "total hip", "orif", "open reduction", "internal fixation"],
        "specialties": ["orthopedicSurgery", "pediatricOrthopedicSurgery", "shoulderAndElbowOrthopedicSurgery", "jointReconstructionSurgery", "spineNeurosurgery", "orthopedicOncology"],
        "description": ["orthopedic", "orthopaedic", "joint replacement", "fracture", "spine", "bone"],
    },
    "Pediatrics": {
        "capability": ["pediatric", "paediatric", "children", "child health", "pediatrics", "paediatrics", "child care", "children's hospital"],
        "equipment": ["pediatric", "paediatric", "infant", "neonatal", "child"],
        "procedure": ["pediatric", "paediatric", "vaccination", "immunization", "child"],
        "specialties": ["pediatrics", "pediatricSurgery", "pediatricCardiology", "pediatricOrthopedicSurgery", "pediatricEmergencyMedicine", "pediatricHematologyOncology"],
        "description": ["pediatric", "paediatric", "children", "child health"],
    },
    "Nephrology": {
        "capability": ["nephrology", "kidney", "renal", "dialysis", "kidney transplant", "hemodialysis", "haemodialysis", "peritoneal dialysis"],
        "equipment": ["dialysis", "hemodialysis", "haemodialysis", "dialysis machine", "reverse osmosis"],
        "procedure": ["dialysis", "hemodialysis", "haemodialysis", "peritoneal dialysis", "kidney transplant", "renal transplant", "av fistula"],
        "specialties": ["nephrology"],
        "description": ["nephrology", "kidney", "renal", "dialysis"],
    },
    "Neurology": {
        "capability": ["neurology", "neurological", "brain", "stroke", "neurosurgery", "neuro", "epilepsy", "parkinson", "multiple sclerosis"],
        "equipment": ["eeg", "emg", "ncv", "neurosurgery", "operating microscope", "neuro navigation"],
        "procedure": ["craniotomy", "brain surgery", "spine surgery", "neurosurgery", "stroke", "thrombectomy", "deep brain stimulation", "dbs"],
        "specialties": ["neurology", "neurosurgery", "spineNeurosurgery", "peripheralNerveNeurosurgery", "neuropsychiatry"],
        "description": ["neurology", "neurological", "brain", "stroke", "neurosurgery"],
    },
    "Ophthalmology": {
        "capability": ["ophthalmology", "eye", "vision", "cataract", "retina", "glaucoma", "eye care", "eye hospital", "lasik", "cornea"],
        "equipment": ["slit lamp", "ophthalmoscope", "fundus camera", "oct", "phaco", "laser", "keratometer", "autorefractor"],
        "procedure": ["cataract surgery", "lasik", "phacoemulsification", "retina surgery", "glaucoma surgery", "corneal transplant", "vitrectomy"],
        "specialties": ["ophthalmology", "cataractAndAnteriorSegmentSurgery", "refractiveSurgeryOphthalmology", "glaucomaOphthalmology", "corneaOphthalmology", "retinaAndVitreoretinalOphthalmology", "oculoplasticsAndReconstructiveOrbitalSurgery", "pediatricsAndStrabismusOphthalmology"],
        "description": ["ophthalmology", "eye", "cataract", "retina", "glaucoma", "eye care"],
    },
    "Dental": {
        "capability": ["dental", "dentistry", "oral surgery", "tooth", "oral health", "endodontics", "orthodontics", "dental implant", "dental clinic"],
        "equipment": ["dental chair", "dental x-ray", "opg", "dental laser", "autoclave"],
        "procedure": ["root canal", "extraction", "dental implant", "orthodontic", "braces", "crown", "bridge", "scaling", "filling", "denture"],
        "specialties": ["dentistry", "endodontics", "orthodontics", "periodontics", "prosthodontics", "oralAndMaxillofacialSurgery", "pediatricDentistry", "paediatricDentistry", "cosmeticDentistry", "laserDentistry", "dentalImplant"],
        "description": ["dental", "dentistry", "oral", "tooth"],
    },
    "Dermatology": {
        "capability": ["dermatology", "skin", "dermatological", "cosmetic dermatology", "skin care", "skin clinic", "hair", "cosmetology"],
        "equipment": ["dermatoscope", "laser", "cryotherapy", "electrocautery", "phototherapy"],
        "procedure": ["skin biopsy", "laser treatment", "chemical peel", "botox", "filler", "hair transplant", "microdermabrasion"],
        "specialties": ["dermatology", "cosmeticDermatology"],
        "description": ["dermatology", "skin", "dermatological", "cosmetic dermatology"],
    },
    "Gastroenterology": {
        "capability": ["gastroenterology", "digestive", "gastrointestinal", "liver", "hepatology", "gi ", "endoscopy", "gastro"],
        "equipment": ["endoscope", "colonoscope", "endoscopy", "ercp", "ultrasound"],
        "procedure": ["endoscopy", "colonoscopy", "ercp", "liver transplant", "upper gi endoscopy", "polypectomy", "liver biopsy"],
        "specialties": ["gastroenterology", "hepatology", "surgicalGastroenterology"],
        "description": ["gastroenterology", "digestive", "gastrointestinal", "liver", "hepatology"],
    },
}


def _parse_json_array(raw):
    if not raw or raw == "null" or raw == "[]":
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
        return [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        return [raw] if isinstance(raw, str) else []


def _find_matches(text_items, keywords, field_name):
    citations = []
    for item in text_items:
        item_lower = item.lower()
        for kw in keywords:
            if kw.lower() in item_lower:
                citations.append({"field": field_name, "text": item.strip()})
                break
    return citations


def _find_specialty_matches(specialties_raw, target_specialties):
    items = _parse_json_array(specialties_raw)
    target_set = set(target_specialties)
    seen = set()
    deduped = []
    for item in items:
        if item in target_set:
            if item not in seen:
                seen.add(item)
                deduped.append({"field": "specialties", "text": item})
    return deduped


def _has_quantitative_claim(citations):
    quant_pattern = re.compile(r'\d+[\s-]*(bed|unit|theatre|ot |ventilator|machine|doctor)', re.IGNORECASE)
    for cite in citations:
        if quant_pattern.search(cite["text"]):
            return True
    return False


def _determine_trust_level(fields_matched, match_count, has_quant):
    num_fields = len(fields_matched)
    if match_count == 0:
        return "no_claim"
    if num_fields >= 3 or match_count >= 5 or (has_quant and num_fields >= 2):
        return "strong_evidence"
    if num_fields >= 2 or match_count >= 3:
        return "partial_evidence"
    return "weak_evidence"


def score_facility(capability, texts):
    if capability not in CAPABILITY_KEYWORDS:
        return {"trust_level": "no_claim", "evidence_citations": [], "fields_matched": [], "match_count": 0}

    keywords_by_field = CAPABILITY_KEYWORDS[capability]
    all_citations = []
    fields_matched = []
    total_match_count = 0

    for field_name in ["capability", "procedure", "equipment", "description"]:
        raw_value = texts.get(field_name, "")
        if not raw_value or raw_value == "null":
            continue
        field_keywords = keywords_by_field.get(field_name, [])
        if not field_keywords:
            continue
        if field_name == "description":
            items = [raw_value] if raw_value else []
        else:
            items = _parse_json_array(raw_value)
        matches = _find_matches(items, field_keywords, field_name)
        if matches:
            fields_matched.append(field_name)
            total_match_count += len(matches)
            all_citations.extend(matches)

    specialties_raw = texts.get("specialties", "")
    specialty_keywords = keywords_by_field.get("specialties", [])
    if specialties_raw and specialties_raw != "null" and specialty_keywords:
        specialty_matches = _find_specialty_matches(specialties_raw, specialty_keywords)
        if specialty_matches:
            fields_matched.append("specialties")
            total_match_count += len(specialty_matches)
            all_citations.extend(specialty_matches)

    has_quant = _has_quantitative_claim(all_citations)
    trust_level = _determine_trust_level(fields_matched, total_match_count, has_quant)

    seen = set()
    unique_citations = []
    for c in all_citations:
        key = (c["field"], c["text"])
        if key not in seen:
            seen.add(key)
            unique_citations.append(c)

    return {
        "trust_level": trust_level,
        "evidence_citations": unique_citations,
        "fields_matched": fields_matched,
        "match_count": total_match_count,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return (APP_DIR / "templates" / "index.html").read_text()


STATE_IMAGES_TABLE = "workspace.default.state_images_data"
_state_image_index = {}


def _normalize_for_match(name):
    return re.sub(r'[^a-z]', '', name.lower())


def _build_state_image_index():
    if _state_image_index:
        return
    try:
        rows = run_query(f"SELECT filename FROM {STATE_IMAGES_TABLE}")
        for r in rows:
            stem = r["filename"].rsplit(".", 1)[0]
            key = _normalize_for_match(stem)
            _state_image_index[key] = r["filename"]
    except Exception:
        pass


def _find_state_image_filename(region):
    _build_state_image_index()
    if not _state_image_index:
        return None
    norm = _normalize_for_match(region)
    if norm in _state_image_index:
        return _state_image_index[norm]
    for key, fname in _state_image_index.items():
        if norm.startswith(key) or key.startswith(norm):
            return fname
    for key, fname in _state_image_index.items():
        if len(norm) > 3 and norm[:4] == key[:4]:
            return fname
    return None


@app.get("/api/state-image/{region}")
def get_state_image(region: str):
    filename = _find_state_image_filename(region)
    if not filename:
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        rows = run_query(f"SELECT content FROM {STATE_IMAGES_TABLE} WHERE filename = '{_safe(filename)}'")
        if rows and rows[0]["content"]:
            return Response(content=rows[0]["content"], media_type="image/jpeg")
    except Exception:
        pass
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/api/cache-status")
def cache_status():
    return {"ready": cache["ready"]}


@app.get("/api/capabilities")
def get_capabilities():
    if cache["ready"]:
        return cache["capabilities"]
    return run_query(f"""
        SELECT capability, COUNT(DISTINCT facility_id) as facility_count
        FROM {SCORES_TABLE} WHERE trust_level != 'no_claim'
        GROUP BY capability ORDER BY facility_count DESC
    """)


@app.get("/api/regions")
def get_regions():
    if cache["ready"]:
        return cache["regions"]
    return run_query(f"""
        SELECT address_stateOrRegion as region, COUNT(*) as facility_count
        FROM {SOURCE_TABLE}
        WHERE address_stateOrRegion IS NOT NULL
          AND LENGTH(address_stateOrRegion) < 40
          AND address_stateOrRegion NOT LIKE '{{%'
          AND address_stateOrRegion NOT LIKE '[%'
        GROUP BY address_stateOrRegion ORDER BY facility_count DESC
    """)


@app.get("/api/hero-regions")
def get_hero_regions():
    if cache["ready"]:
        return cache["regions"][:5]
    regions = run_query(f"""
        SELECT address_stateOrRegion as region, COUNT(*) as facility_count
        FROM {SOURCE_TABLE}
        WHERE address_stateOrRegion IS NOT NULL
          AND LENGTH(address_stateOrRegion) < 40
          AND address_stateOrRegion NOT LIKE '{{%'
          AND address_stateOrRegion NOT LIKE '[%'
        GROUP BY address_stateOrRegion ORDER BY facility_count DESC LIMIT 5
    """)
    return regions


@app.get("/api/top-facilities")
def get_top_facilities(limit: int = Query(25)):
    return run_query(f"""
        SELECT s.facility_id, f.name, f.address_city, f.address_stateOrRegion as region,
               SUM(s.match_count) as total_citations,
               COUNT(CASE WHEN s.trust_level = 'strong_evidence' THEN 1 END) as strong_count,
               FIRST(CASE WHEN s.trust_level = 'strong_evidence' THEN s.capability END) as top_capability
        FROM {SCORES_TABLE} s
        JOIN {SOURCE_TABLE} f ON s.facility_id = f.unique_id
        WHERE s.trust_level != 'no_claim'
        GROUP BY s.facility_id, f.name, f.address_city, f.address_stateOrRegion
        ORDER BY total_citations DESC
        LIMIT {limit}
    """)


@app.get("/api/needs-review")
def get_needs_review(limit: int = Query(25)):
    return run_query(f"""
        SELECT s.facility_id, f.name, f.address_city, f.address_stateOrRegion as region,
               s.capability, s.trust_level, s.match_count, s.fields_matched, s.evidence_citations
        FROM {SCORES_TABLE} s
        JOIN {SOURCE_TABLE} f ON s.facility_id = f.unique_id
        WHERE s.trust_level = 'weak_evidence' AND s.match_count >= 2
        ORDER BY s.match_count DESC
        LIMIT {limit}
    """)


@app.get("/api/strong-evidence")
def get_strong_evidence(limit: int = Query(25)):
    return run_query(f"""
        SELECT s.facility_id, f.name, f.address_city, f.address_stateOrRegion as region,
               s.capability, s.trust_level, s.match_count, s.fields_matched, s.evidence_citations
        FROM {SCORES_TABLE} s
        JOIN {SOURCE_TABLE} f ON s.facility_id = f.unique_id
        WHERE s.trust_level = 'strong_evidence'
        ORDER BY s.match_count DESC
        LIMIT {limit}
    """)


@app.get("/api/facilities")
def get_facilities(
    capability: str = Query(None),
    region: str = Query(None),
    trust_level: str = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
):
    conditions = []
    if capability:
        caps = [c.strip() for c in capability.split(",") if c.strip()]
        if len(caps) == 1:
            conditions.append(f"s.capability = '{_safe(caps[0])}'")
        else:
            in_list = ", ".join(f"'{_safe(c)}'" for c in caps)
            conditions.append(f"s.capability IN ({in_list})")
    if trust_level:
        conditions.append(f"s.trust_level = '{_safe(trust_level)}'")
    if region:
        regions = [r.strip() for r in region.split(",") if r.strip()]
        if len(regions) == 1:
            conditions.append(f"f.address_stateOrRegion = '{_safe(regions[0])}'")
        else:
            in_list = ", ".join(f"'{_safe(r)}'" for r in regions)
            conditions.append(f"f.address_stateOrRegion IN ({in_list})")
    if not capability:
        conditions.append("s.trust_level != 'no_claim'")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    total = run_query(f"""
        SELECT COUNT(*) as total
        FROM {SCORES_TABLE} s
        JOIN {SOURCE_TABLE} f ON s.facility_id = f.unique_id
        {where}
    """)[0]["total"]

    facilities = run_query(f"""
        SELECT s.facility_id, f.name, f.address_city, f.address_stateOrRegion as region,
               s.capability, s.trust_level, s.match_count,
               s.fields_matched, s.evidence_citations
        FROM {SCORES_TABLE} s
        JOIN {SOURCE_TABLE} f ON s.facility_id = f.unique_id
        {where}
        ORDER BY CASE s.trust_level
            WHEN 'strong_evidence' THEN 1
            WHEN 'partial_evidence' THEN 2
            WHEN 'weak_evidence' THEN 3
            ELSE 4
        END, s.match_count DESC
        LIMIT {limit} OFFSET {offset}
    """)

    return {"total": total, "facilities": facilities}


@app.get("/api/facility/{facility_id}")
def get_facility_detail(facility_id: str, capability: str = Query(None)):
    fid = _safe(facility_id)
    facility = run_query(f"""
        SELECT unique_id, name, address_city, address_stateOrRegion as region,
               capability, procedure, equipment, specialties, description
        FROM {SOURCE_TABLE}
        WHERE unique_id = '{fid}'
    """)
    if not facility:
        return JSONResponse({"error": "Facility not found"}, status_code=404)

    score_filter = f"AND capability = '{_safe(capability)}'" if capability else ""
    scores = run_query(f"""
        SELECT capability, trust_level, match_count, fields_matched, evidence_citations
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY capability ORDER BY match_count DESC) as rn
            FROM {SCORES_TABLE}
            WHERE facility_id = '{fid}' {score_filter}
        )
        WHERE rn = 1
        ORDER BY CASE trust_level
            WHEN 'strong_evidence' THEN 1 WHEN 'partial_evidence' THEN 2
            WHEN 'weak_evidence' THEN 3 ELSE 4 END
    """)

    return {"facility": facility[0], "scores": scores}


@app.get("/api/search")
def search(q: str = Query(..., min_length=2)):
    if not cache["ready"]:
        return []

    q_lower = q.lower()
    results = []

    for cap in cache["capabilities"]:
        if q_lower in cap["capability"].lower():
            results.append({"type": "capability", "title": cap["capability"], "subtitle": f"{cap['facility_count']} facilities"})

    region_matches = 0
    for r in cache["regions"]:
        if q_lower in r["region"].lower():
            results.append({"type": "region", "title": r["region"], "subtitle": f"{r['facility_count']} facilities"})
            region_matches += 1
            if region_matches >= 5:
                break

    facility_matches = 0
    for f in cache["facilities"]:
        if f["name"] and q_lower in f["name"].lower():
            subtitle = f"{f['address_city'] or ''}, {f['region'] or ''}".strip(", ")
            results.append({"type": "facility", "id": f["unique_id"], "title": f["name"], "subtitle": subtitle})
            facility_matches += 1
            if facility_matches >= 7:
                break

    return results[:10]


# ─── Override / Re-score ──────────────────────────────────────────────────────

@app.post("/api/facility/{facility_id}/rescore")
async def rescore_facility(facility_id: str, request: Request):
    body = await request.json()
    capability = body.get("capability")
    texts = body.get("texts", {})

    if not capability or capability not in CAPABILITY_KEYWORDS:
        return JSONResponse({"error": f"Invalid capability: {capability}"}, status_code=400)

    # Get current score
    fid = _safe(facility_id)
    current = run_query(f"""
        SELECT trust_level, match_count, fields_matched, evidence_citations
        FROM {SCORES_TABLE}
        WHERE facility_id = '{fid}' AND capability = '{_safe(capability)}'
    """)

    before = {
        "trust_level": current[0]["trust_level"] if current else "no_claim",
        "evidence_citations": json.loads(current[0]["evidence_citations"]) if current else [],
        "fields_matched": json.loads(current[0]["fields_matched"]) if current else [],
        "match_count": current[0]["match_count"] if current else 0,
    }

    after = score_facility(capability, texts)

    return {"before": before, "after": after}


@app.post("/api/facility/{facility_id}/confirm-override")
async def confirm_override(facility_id: str, request: Request):
    body = await request.json()
    capability = body.get("capability")
    texts = body.get("texts", {})
    old_result = body.get("old_result", {})
    new_result = body.get("new_result", {})
    note = body.get("note", "")

    fid = _safe(facility_id)
    override_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Insert override record
    run_statement(f"""
        INSERT INTO {OVERRIDES_TABLE} VALUES (
            '{override_id}', '{fid}', '{_safe(capability)}',
            '{_safe(texts.get("capability", ""))}',
            '{_safe(texts.get("procedure", ""))}',
            '{_safe(texts.get("equipment", ""))}',
            '{_safe(texts.get("specialties", ""))}',
            '{_safe(texts.get("description", ""))}',
            '{_safe(old_result.get("trust_level", ""))}',
            '{_safe(new_result.get("trust_level", ""))}',
            '{_safe(json.dumps(old_result.get("evidence_citations", [])))}',
            '{_safe(json.dumps(new_result.get("evidence_citations", [])))}',
            '{_safe(note)}',
            '{now}'
        )
    """)

    # Update score table
    new_citations = json.dumps(new_result.get("evidence_citations", []))
    new_fields = json.dumps(new_result.get("fields_matched", []))
    new_count = new_result.get("match_count", 0)

    run_statement(f"""
        UPDATE {SCORES_TABLE}
        SET trust_level = '{_safe(new_result.get("trust_level", "no_claim"))}',
            evidence_citations = '{_safe(new_citations)}',
            fields_matched = '{_safe(new_fields)}',
            match_count = {new_count},
            scored_at = '{now}'
        WHERE facility_id = '{fid}' AND capability = '{_safe(capability)}'
    """)

    return {"success": True, "override_id": override_id}


def _safe(val):
    if not val:
        return ""
    return str(val).replace("'", "''")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
