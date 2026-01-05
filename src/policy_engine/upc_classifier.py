"""UPC/SKU classification for item eligibility"""

from typing import Optional, Dict, List
import structlog

from .categories import ALLOWED_CATEGORIES, DISALLOWED_CATEGORIES, UPC_PATTERNS

logger = structlog.get_logger()


class UPCClassifier:
    """Classifies items by UPC/SKU to determine SNAP eligibility"""
    
    def __init__(self):
        # In production, this would load from a database or external service
        self.category_cache: Dict[str, str] = {}
    
    def classify_item(
        self,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
        product_name: Optional[str] = None,
        category: Optional[str] = None,
    ) -> str:
        """
        Classify an item based on UPC, SKU, product name, or category.
        
        Args:
            upc: Universal Product Code
            sku: Stock Keeping Unit
            product_name: Product name/description
            category: Pre-classified category
            
        Returns:
            Category string (e.g., 'groceries', 'alcohol', 'hot_food')
        """
        # If category is provided and valid, use it
        if category and category in (ALLOWED_CATEGORIES | DISALLOWED_CATEGORIES):
            return category
        
        # Check UPC/SKU cache
        identifier = upc or sku
        if identifier and identifier in self.category_cache:
            return self.category_cache[identifier]
        
        # Classify based on product name patterns
        if product_name:
            product_lower = product_name.lower()
            
            # Check for disallowed patterns first (more restrictive)
            for disallowed_cat, patterns in UPC_PATTERNS.items():
                for pattern in patterns:
                    if pattern in product_lower:
                        logger.info(
                            "item_classified",
                            identifier=identifier,
                            category=disallowed_cat,
                            method="pattern_match",
                        )
                        if identifier:
                            self.category_cache[identifier] = disallowed_cat
                        return disallowed_cat
        
        # Default to unknown if we can't classify
        logger.warning(
            "item_unclassified",
            upc=upc,
            sku=sku,
            product_name=product_name,
        )
        return "unknown"
    
    def is_eligible(self, category: str) -> bool:
        """
        Check if a category is SNAP-eligible.
        
        Args:
            category: Item category
            
        Returns:
            True if eligible, False otherwise
        """
        if category in ALLOWED_CATEGORIES:
            return True
        if category in DISALLOWED_CATEGORIES:
            return False
        # Unknown categories are default-deny
        return False


# Global classifier instance
classifier = UPCClassifier()

