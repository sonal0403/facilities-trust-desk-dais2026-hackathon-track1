"""
Keyword definitions for each healthcare capability.

Each capability maps to a dict of {field_name: [keywords]}.
Keywords are lowercase — matching is case-insensitive.
Specialties are matched exactly (camelCase as they appear in the data).
"""

CAPABILITY_KEYWORDS = {
    "ICU": {
        "capability": [
            "icu", "intensive care unit", "intensive care", "critical care",
            "ventilator beds", "ventilator bed", "level ii icu", "level iii icu",
            "medical icu", "surgical icu", "cardiac icu",
        ],
        "equipment": [
            "ventilator", "icu", "cardiac monitor", "central monitoring",
            "bedside monitor", "defibrillator", "infusion pump",
            "pulse oximeter", "cpap", "bipap",
        ],
        "procedure": [
            "mechanical ventilation", "invasive ventilation",
            "non-invasive ventilation", "critical care",
            "intubation", "central line",
        ],
        "specialties": [
            "criticalCareMedicine",
        ],
        "description": [
            "icu", "intensive care", "critical care",
        ],
    },
    "Maternity": {
        "capability": [
            "maternity", "labour room", "labor room", "delivery room",
            "obstetric", "antenatal", "postnatal", "prenatal",
            "maternity ward", "delivery services", "birthing",
            "normal delivery", "cesarean", "c-section",
        ],
        "equipment": [
            "fetal monitor", "fetal doppler", "doppler",
            "ctg", "cardiotocograph", "delivery table",
            "infant warmer", "radiant warmer",
        ],
        "procedure": [
            "delivery", "deliveries", "c-section", "cesarean",
            "caesarean", "csection", "normal delivery",
            "vaginal delivery", "obstetric", "episiotomy",
            "labor", "labour",
        ],
        "specialties": [
            "gynecologyAndObstetrics",
            "obstetricsAndMaternityCare",
            "maternalFetalMedicineOrPerinatology",
            "familyPlanningAndComplexContraception",
        ],
        "description": [
            "maternity", "obstetric", "delivery", "labour room",
            "labor room", "antenatal",
        ],
    },
    "Emergency": {
        "capability": [
            "emergency", "24x7", "24/7", "24 x 7", "round the clock",
            "accident", "casualty", "trauma centre", "trauma center",
            "emergency department", "emergency room",
            "emergency services",
        ],
        "equipment": [
            "ambulance", "defibrillator", "crash cart",
            "emergency", "trauma",
        ],
        "procedure": [
            "emergency", "trauma", "resuscitation",
            "triage", "stabilization",
        ],
        "specialties": [
            "emergencyMedicine",
            "pediatricEmergencyMedicine",
        ],
        "description": [
            "emergency", "24x7", "24/7", "casualty",
            "accident", "round the clock",
        ],
    },
    "Oncology": {
        "capability": [
            "oncology", "cancer", "chemotherapy", "radiation therapy",
            "radiotherapy", "tumor", "tumour", "malignancy",
            "cancer care", "cancer treatment", "cancer hospital",
            "bone marrow transplant", "bmt",
        ],
        "equipment": [
            "linear accelerator", "linac", "cobalt",
            "brachytherapy", "pet-ct", "pet ct", "pet scan",
            "cyberknife", "gamma knife",
        ],
        "procedure": [
            "chemotherapy", "radiation", "radiotherapy",
            "bone marrow transplant", "bmt", "stem cell transplant",
            "mastectomy", "lumpectomy", "biopsy",
            "immunotherapy", "targeted therapy",
        ],
        "specialties": [
            "medicalOncology",
            "surgicalOncology",
            "gynecologicOncology",
            "gynecologicalOncology",
            "radiationOncology",
            "pediatricHematologyOncology",
        ],
        "description": [
            "oncology", "cancer", "chemotherapy", "radiation",
        ],
    },
    "Trauma": {
        "capability": [
            "trauma", "polytrauma", "trauma centre", "trauma center",
            "accident", "fracture management", "trauma care",
            "trauma surgery", "burns management", "burn unit",
        ],
        "equipment": [
            "trauma", "c-arm", "fluoroscopy",
            "orthopedic implant", "external fixator",
            "traction",
        ],
        "procedure": [
            "fracture", "trauma surgery", "polytrauma",
            "open reduction", "internal fixation", "orif",
            "external fixation", "debridement",
            "skin grafting", "flap surgery",
        ],
        "specialties": [
            "burnAndTraumaPlasticSurgery",
            "orthopedicSurgery",
            "traumaSurgery",
        ],
        "description": [
            "trauma", "polytrauma", "accident", "fracture",
            "burns",
        ],
    },
    "NICU": {
        "capability": [
            "nicu", "neonatal intensive care", "neonatal icu",
            "newborn icu", "neonatal care", "newborn care",
            "level ii nicu", "level iii nicu",
            "sick newborn", "preterm",
        ],
        "equipment": [
            "incubator", "infant warmer", "radiant warmer",
            "phototherapy", "neonatal ventilator",
            "cpap", "nasal cpap", "bubble cpap",
            "infant flow", "neonatal monitor",
        ],
        "procedure": [
            "neonatal resuscitation", "exchange transfusion",
            "surfactant", "phototherapy", "kangaroo care",
        ],
        "specialties": [
            "neonatologyPerinatalMedicine",
        ],
        "description": [
            "nicu", "neonatal", "newborn intensive",
        ],
    },
}
