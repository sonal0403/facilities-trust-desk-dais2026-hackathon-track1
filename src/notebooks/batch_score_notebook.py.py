# Databricks notebook source
# MAGIC %md
# MAGIC # Facility Trust Desk — Batch Scoring
# MAGIC
# MAGIC Scores all 10k facilities across 15 capabilities.
# MAGIC Writes results to `workspace.default.facility_trust_scores`.
# MAGIC
# MAGIC **Run**: Attach to Serverless compute and Run All.

# COMMAND ----------

import json
import re
from datetime import datetime, timezone

# COMMAND ----------

# MAGIC %md
# MAGIC ## Keyword Definitions (15 Capabilities)

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md
# MAGIC ## Scoring Engine

# COMMAND ----------

def parse_json_array(raw):
    """Parse a JSON array string into a list of strings."""
    if not raw or raw == "null" or raw == "[]":
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
        return [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        return [raw] if isinstance(raw, str) else []


def find_matches(text_items, keywords, field_name):
    """Find text items containing any keyword. Returns citations with source field."""
    citations = []
    for item in text_items:
        item_lower = item.lower()
        for kw in keywords:
            if kw.lower() in item_lower:
                citations.append({"field": field_name, "text": item.strip()})
                break
    return citations


def find_specialty_matches(specialties_raw, target_specialties):
    """Check for exact specialty matches."""
    items = parse_json_array(specialties_raw)
    target_set = set(target_specialties)
    seen = set()
    deduped = []
    for item in items:
        if item in target_set:
            if item not in seen:
                seen.add(item)
                deduped.append({"field": "specialties", "text": item})
    return deduped


def has_quantitative_claim(citations):
    """Check if any citation contains quantitative capacity info."""
    quant_pattern = re.compile(r'\d+[\s-]*(bed|unit|theatre|ot |ventilator|machine|doctor)', re.IGNORECASE)
    for cite in citations:
        if quant_pattern.search(cite["text"]):
            return True
    return False


def determine_trust_level(fields_matched, match_count, has_quant):
    """
    Trust level rules:
    - strong: 3+ fields, OR 5+ hits, OR quantitative + 2+ fields
    - partial: 2 fields, OR 3-4 hits
    - weak: 1 field, OR 1-2 hits
    - no_claim: zero
    """
    num_fields = len(fields_matched)
    if match_count == 0:
        return "no_claim"
    if num_fields >= 3 or match_count >= 5 or (has_quant and num_fields >= 2):
        return "strong_evidence"
    if num_fields >= 2 or match_count >= 3:
        return "partial_evidence"
    return "weak_evidence"


def score_facility(capability, texts):
    """
    Score one facility for one capability.
    Returns dict with trust_level, evidence_citations (with field attribution), fields_matched, match_count.
    """
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
            items = parse_json_array(raw_value)
        matches = find_matches(items, field_keywords, field_name)
        if matches:
            fields_matched.append(field_name)
            total_match_count += len(matches)
            all_citations.extend(matches)

    # Specialties (exact match)
    specialties_raw = texts.get("specialties", "")
    specialty_keywords = keywords_by_field.get("specialties", [])
    if specialties_raw and specialties_raw != "null" and specialty_keywords:
        specialty_matches = find_specialty_matches(specialties_raw, specialty_keywords)
        if specialty_matches:
            fields_matched.append("specialties")
            total_match_count += len(specialty_matches)
            all_citations.extend(specialty_matches)

    has_quant = has_quantitative_claim(all_citations)
    trust_level = determine_trust_level(fields_matched, total_match_count, has_quant)

    # Deduplicate citations
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

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Batch Scoring

# COMMAND ----------

SOURCE_TABLE = "databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities"
TARGET_TABLE = "workspace.default.facility_trust_scores"

print(f"[{datetime.now()}] Reading facilities from {SOURCE_TABLE}...")
df = spark.table(SOURCE_TABLE).select("unique_id", "capability", "procedure", "equipment", "specialties", "description")
facilities = df.collect()
print(f"[{datetime.now()}] Loaded {len(facilities)} facilities. Scoring across {len(CAPABILITY_KEYWORDS)} capabilities...")

# COMMAND ----------

scored_at = datetime.now(timezone.utc).isoformat()
results = []

for i, row in enumerate(facilities):
    facility_id = row["unique_id"]
    if not facility_id:
        continue

    texts = {
        "capability": row["capability"] or "",
        "procedure": row["procedure"] or "",
        "equipment": row["equipment"] or "",
        "specialties": row["specialties"] or "",
        "description": row["description"] or "",
    }

    for cap_name in CAPABILITY_KEYWORDS:
        result = score_facility(cap_name, texts)
        results.append({
            "facility_id": facility_id,
            "capability": cap_name,
            "trust_level": result["trust_level"],
            "evidence_citations": json.dumps(result["evidence_citations"]),
            "fields_matched": json.dumps(result["fields_matched"]),
            "match_count": result["match_count"],
            "scored_at": scored_at,
        })

    if (i + 1) % 2000 == 0:
        print(f"[{datetime.now()}] Scored {i + 1}/{len(facilities)} facilities...")

print(f"[{datetime.now()}] Scoring complete. Total rows: {len(results)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write Results to Delta

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType, IntegerType

schema = StructType([
    StructField("facility_id", StringType()),
    StructField("capability", StringType()),
    StructField("trust_level", StringType()),
    StructField("evidence_citations", StringType()),
    StructField("fields_matched", StringType()),
    StructField("match_count", IntegerType()),
    StructField("scored_at", StringType()),
])

results_df = spark.createDataFrame(results, schema=schema)
results_df.write.mode("overwrite").saveAsTable(TARGET_TABLE)
print(f"Written {len(results)} rows to {TARGET_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation — Trust Level Distribution

# COMMAND ----------

display(spark.sql(f"""
    SELECT capability, trust_level, COUNT(*) as count
    FROM {TARGET_TABLE}
    GROUP BY capability, trust_level
    ORDER BY capability, trust_level
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample: Strong Evidence Facilities

# COMMAND ----------

display(spark.sql(f"""
    SELECT s.facility_id, f.name, f.address_city, f.address_stateOrRegion,
           s.capability, s.trust_level, s.match_count, s.evidence_citations
    FROM {TARGET_TABLE} s
    JOIN databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities f
      ON s.facility_id = f.unique_id
    WHERE s.trust_level = 'strong_evidence'
    LIMIT 20
"""))