# agent/app/core/medical_knowledge.py

# 1. BODY PART MAPPING
BODY_PART_ALIASES = {
    "face": ["face", "cheek", "forehead", "nose", "chin", "jaw", "lips"],
    "hair": ["hair", "scalp", "roots", "ends", "bangs"],
    "body": ["body", "back", "chest", "arms", "legs", "hands", "feet", "skin"],
    "eyes": ["eyes", "under-eye", "bags", "lids"],
    "nails": ["nails", "fingernails", "toenails", "cuticles"]
}

# 2. SYMPTOM / TERM MAPPING
TERM_MAPPING = {
    # SLANG
    "panda": {"symptom": "Dark Circles", "likely_part": "eyes"},
    "raccoon": {"symptom": "Dark Circles", "likely_part": "eyes"},
    "pizza": {"symptom": "Severe Acne", "likely_part": "face"},
    "strawberry": {"symptom": "Redness/Pores", "likely_part": "face"},
    "hay": {"symptom": "Dry/Damaged Hair", "likely_part": "hair"},
    "greaseball": {"symptom": "Excess Oil", "likely_part": "face"},
    "chicken skin": {"symptom": "Keratosis Pilaris", "likely_part": "body"},
    
    # COMMON TERMS
    "zit": {"symptom": "Acne", "likely_part": "face"},
    "pimple": {"symptom": "Acne", "likely_part": "face"},
    "breakout": {"symptom": "Acne", "likely_part": "face"},
    "dry": {"symptom": "Dryness", "likely_part": "skin"},
    "itchy": {"symptom": "Itching", "likely_part": "skin"},
    "red": {"symptom": "Inflammation", "likely_part": "skin"},
    "wrinkles": {"symptom": "Aging", "likely_part": "face"},
}

def analyze_input(text: str) -> dict:
    """Scans text for medical hints."""
    text = text.lower()
    found_symptoms = []
    found_parts = []
    
    # Check Terms
    for term, info in TERM_MAPPING.items():
        if term in text:
            found_symptoms.append(f"'{term}' implies {info['symptom']}")
            if info['likely_part'] not in found_parts:
                found_parts.append(info['likely_part'])

    # Check Body Parts
    for standard_part, aliases in BODY_PART_ALIASES.items():
        for alias in aliases:
            if alias in text:
                if standard_part not in found_parts:
                    found_parts.append(standard_part)
                break
                
    return {
        "hints": "; ".join(found_symptoms),
        "detected_parts": ", ".join(set(found_parts))
    }