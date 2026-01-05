"""SNAP-eligible and ineligible categories"""

# Allowed categories (SNAP-eligible)
ALLOWED_CATEGORIES = {
    # Food & Groceries
    "groceries",
    "food",
    "fresh_produce",
    "meat",
    "dairy",
    "bakery",
    "frozen_food",
    "canned_goods",
    "beverages_non_alcoholic",
    "snacks",
    "cereal",
    "pasta",
    "rice",
    "bread",
    "seafood",
    
    # Pharmacy & Health
    "pharmacy",
    "prescription",
    "over_the_counter",
    "vitamins",
    "health_supplements",
    "medical_supplies",
    "baby_formula",
    "baby_food",
}

# Disallowed categories (NOT SNAP-eligible)
DISALLOWED_CATEGORIES = {
    # Alcohol & Tobacco
    "alcohol",
    "beer",
    "wine",
    "liquor",
    "tobacco",
    "cigarettes",
    "cigars",
    "vaping",
    "smoking_products",
    
    # Hot Prepared Foods
    "hot_food",
    "prepared_food",
    "deli_hot",
    "hot_deli",
    "restaurant",
    "fast_food",
    
    # Non-Food Items
    "non_food",
    "household",
    "cleaning_supplies",
    "paper_products",
    "pet_food",  # Note: Some states allow, but default deny
    "cosmetics",
    "toiletries_non_essential",
    "clothing",
    "electronics",
    "appliances",
}

# UPC/SKU patterns for classification
# These are example patterns - in production, use a comprehensive database
UPC_PATTERNS = {
    # Alcohol patterns (example)
    "alcohol": [
        "beer", "wine", "liquor", "spirits", "alcohol",
    ],
    # Tobacco patterns
    "tobacco": [
        "cigarette", "cigar", "tobacco", "smoking",
    ],
    # Hot food indicators
    "hot_food": [
        "hot", "prepared", "deli_hot", "ready_to_eat",
    ],
}

# Merchant categories that are generally allowed (grocery stores, pharmacies)
ALLOWED_MERCHANT_TYPES = {
    "grocery_store",
    "supermarket",
    "pharmacy",
    "drugstore",
    "convenience_store",  # For eligible items only
}

