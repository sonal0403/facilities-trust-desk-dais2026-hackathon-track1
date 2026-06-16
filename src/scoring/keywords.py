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
            "critical care unit", "ventilator beds", "ventilator bed",
            "level ii icu", "level iii icu", "medical icu", "surgical icu", "cardiac icu",
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
            "obstetrics", "obstetric", "antenatal", "postnatal", "prenatal",
            "maternity ward", "delivery services", "birthing",
            "normal delivery", "cesarean", "c-section", "labor", "delivery",
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
            "labor room", "antenatal", "birthing", "prenatal", "postnatal",
        ],
    },
    "Emergency": {
        "capability": [
            "emergency", "24x7", "24/7", "24 x 7", "round the clock",
            "accident", "casualty", "trauma centre", "trauma center",
            "emergency department", "emergency room",
            "emergency services", "urgent care",
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
            "accident", "round the clock", "urgent care",
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
            "tumor", "malignancy",
        ],
    },
    "Trauma": {
        "capability": [
            "trauma", "polytrauma", "trauma centre", "trauma center",
            "trauma unit", "fracture management", "trauma care",
            "trauma surgery", "burns management", "burn unit",
            "level i trauma", "level ii trauma", "level iii trauma",
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
            "nicu", "neonatal intensive care", "neonatal intensive care unit",
            "neonatal icu", "newborn icu", "newborn intensive care",
            "neonatal care", "newborn care",
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
    "Cardiology": {
        "capability": [
            "cardiology", "cardiac", "heart", "cardiovascular",
            "coronary", "interventional cardiology",
            "cardiac surgery", "open heart", "bypass",
            "cath lab", "cardiac catheterization",
        ],
        "equipment": [
            "cath lab", "echocardiography", "ecg", "ekg",
            "holter", "treadmill", "angiography",
            "pacemaker", "defibrillator", "stent",
        ],
        "procedure": [
            "angioplasty", "angiography", "bypass", "cabg",
            "stenting", "pacemaker", "valve replacement",
            "echocardiography", "cardiac catheterization",
            "coronary intervention",
        ],
        "specialties": [
            "cardiology",
            "interventionalCardiology",
            "cardiothoracicSurgery",
            "cardiacSurgery",
            "pediatricCardiology",
        ],
        "description": [
            "cardiology", "cardiac", "heart", "cardiovascular",
            "coronary",
        ],
    },
    "Orthopedics": {
        "capability": [
            "orthopedic", "orthopaedic", "joint replacement",
            "bone", "fracture", "spine", "joint",
            "musculoskeletal", "sports medicine",
        ],
        "equipment": [
            "c-arm", "fluoroscopy", "arthroscopy",
            "orthopedic implant", "external fixator",
            "traction", "bone drill",
        ],
        "procedure": [
            "joint replacement", "knee replacement", "hip replacement",
            "arthroscopy", "fracture fixation", "spinal surgery",
            "spine surgery", "total knee", "total hip",
            "orif", "open reduction", "internal fixation",
        ],
        "specialties": [
            "orthopedicSurgery",
            "pediatricOrthopedicSurgery",
            "shoulderAndElbowOrthopedicSurgery",
            "jointReconstructionSurgery",
            "spineNeurosurgery",
            "orthopedicOncology",
        ],
        "description": [
            "orthopedic", "orthopaedic", "joint replacement",
            "fracture", "spine", "bone",
        ],
    },
    "Pediatrics": {
        "capability": [
            "pediatric", "paediatric", "children", "child health",
            "pediatrics", "paediatrics", "child care",
            "children's hospital",
        ],
        "equipment": [
            "pediatric", "paediatric", "infant",
            "neonatal", "child",
        ],
        "procedure": [
            "pediatric", "paediatric", "vaccination",
            "immunization", "child",
        ],
        "specialties": [
            "pediatrics",
            "pediatricSurgery",
            "pediatricCardiology",
            "pediatricOrthopedicSurgery",
            "pediatricEmergencyMedicine",
            "pediatricHematologyOncology",
        ],
        "description": [
            "pediatric", "paediatric", "children", "child health",
        ],
    },
    "Nephrology": {
        "capability": [
            "nephrology", "kidney", "renal", "dialysis",
            "kidney transplant", "hemodialysis", "haemodialysis",
            "peritoneal dialysis",
        ],
        "equipment": [
            "dialysis", "hemodialysis", "haemodialysis",
            "dialysis machine", "reverse osmosis",
        ],
        "procedure": [
            "dialysis", "hemodialysis", "haemodialysis",
            "peritoneal dialysis", "kidney transplant",
            "renal transplant", "av fistula",
        ],
        "specialties": [
            "nephrology",
        ],
        "description": [
            "nephrology", "kidney", "renal", "dialysis",
        ],
    },
    "Neurology": {
        "capability": [
            "neurology", "neurological", "brain", "stroke",
            "neurosurgery", "neuro", "epilepsy",
            "parkinson", "multiple sclerosis",
        ],
        "equipment": [
            "eeg", "emg", "ncv",
            "neurosurgery", "operating microscope",
            "neuro navigation",
        ],
        "procedure": [
            "craniotomy", "brain surgery", "spine surgery",
            "neurosurgery", "stroke", "thrombectomy",
            "deep brain stimulation", "dbs",
        ],
        "specialties": [
            "neurology",
            "neurosurgery",
            "spineNeurosurgery",
            "peripheralNerveNeurosurgery",
            "neuropsychiatry",
        ],
        "description": [
            "neurology", "neurological", "brain", "stroke",
            "neurosurgery",
        ],
    },
    "Ophthalmology": {
        "capability": [
            "ophthalmology", "eye", "vision", "cataract",
            "retina", "glaucoma", "eye care", "eye hospital",
            "lasik", "cornea",
        ],
        "equipment": [
            "slit lamp", "ophthalmoscope", "fundus camera",
            "oct", "phaco", "laser", "keratometer",
            "autorefractor",
        ],
        "procedure": [
            "cataract surgery", "lasik", "phacoemulsification",
            "retina surgery", "glaucoma surgery",
            "corneal transplant", "vitrectomy",
        ],
        "specialties": [
            "ophthalmology",
            "cataractAndAnteriorSegmentSurgery",
            "refractiveSurgeryOphthalmology",
            "glaucomaOphthalmology",
            "corneaOphthalmology",
            "retinaAndVitreoretinalOphthalmology",
            "oculoplasticsAndReconstructiveOrbitalSurgery",
            "pediatricsAndStrabismusOphthalmology",
        ],
        "description": [
            "ophthalmology", "eye", "cataract", "retina",
            "glaucoma", "eye care",
        ],
    },
    "Dental": {
        "capability": [
            "dental", "dentistry", "oral surgery", "tooth",
            "oral health", "endodontics", "orthodontics",
            "dental implant", "dental clinic",
        ],
        "equipment": [
            "dental chair", "dental x-ray", "opg",
            "dental laser", "autoclave",
        ],
        "procedure": [
            "root canal", "extraction", "dental implant",
            "orthodontic", "braces", "crown", "bridge",
            "scaling", "filling", "denture",
        ],
        "specialties": [
            "dentistry",
            "endodontics",
            "orthodontics",
            "periodontics",
            "prosthodontics",
            "oralAndMaxillofacialSurgery",
            "pediatricDentistry",
            "paediatricDentistry",
            "cosmeticDentistry",
            "laserDentistry",
            "dentalImplant",
        ],
        "description": [
            "dental", "dentistry", "oral", "tooth",
        ],
    },
    "Dermatology": {
        "capability": [
            "dermatology", "skin", "dermatological",
            "cosmetic dermatology", "skin care",
            "skin clinic", "hair", "cosmetology",
        ],
        "equipment": [
            "dermatoscope", "laser", "cryotherapy",
            "electrocautery", "phototherapy",
        ],
        "procedure": [
            "skin biopsy", "laser treatment", "chemical peel",
            "botox", "filler", "hair transplant",
            "microdermabrasion",
        ],
        "specialties": [
            "dermatology",
            "cosmeticDermatology",
        ],
        "description": [
            "dermatology", "skin", "dermatological",
            "cosmetic dermatology",
        ],
    },
    "Gastroenterology": {
        "capability": [
            "gastroenterology", "digestive", "gastrointestinal",
            "liver", "hepatology", "gi ", "endoscopy",
            "gastro",
        ],
        "equipment": [
            "endoscope", "colonoscope", "endoscopy",
            "ercp", "ultrasound",
        ],
        "procedure": [
            "endoscopy", "colonoscopy", "ercp",
            "liver transplant", "upper gi endoscopy",
            "polypectomy", "liver biopsy",
        ],
        "specialties": [
            "gastroenterology",
            "hepatology",
            "surgicalGastroenterology",
        ],
        "description": [
            "gastroenterology", "digestive", "gastrointestinal",
            "liver", "hepatology",
        ],
    },
}
