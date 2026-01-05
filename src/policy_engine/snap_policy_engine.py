"""SNAP-like policy engine for eligibility enforcement"""

from typing import List, Dict, Optional
from decimal import Decimal
from enum import Enum
import structlog

from .upc_classifier import classifier
from .categories import ALLOWED_CATEGORIES, DISALLOWED_CATEGORIES

logger = structlog.get_logger()


class PolicyDecision(Enum):
    """Policy decision result"""
    APPROVE = "approve"
    DENY = "deny"
    PARTIAL = "partial"  # Some items approved, some denied


class Item:
    """Represents an item in a transaction"""
    def __init__(
        self,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
        product_name: Optional[str] = None,
        category: Optional[str] = None,
        price: Decimal = Decimal("0.00"),
        quantity: int = 1,
    ):
        self.upc = upc
        self.sku = sku
        self.product_name = product_name
        self.category = category or classifier.classify_item(upc, sku, product_name)
        self.price = price
        self.quantity = quantity
        self.is_eligible = classifier.is_eligible(self.category)


class PolicyEngine:
    """Main policy engine for SNAP-like eligibility"""
    
    def __init__(self):
        self.classifier = classifier
    
    def check_item_eligibility(
        self,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
        product_name: Optional[str] = None,
        category: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Check if a single item is eligible.
        
        Args:
            upc: Universal Product Code
            sku: Stock Keeping Unit
            product_name: Product name
            category: Pre-classified category
            
        Returns:
            Tuple of (is_eligible: bool, category: str)
        """
        category = classifier.classify_item(upc, sku, product_name, category)
        is_eligible = classifier.is_eligible(category)
        
        logger.info(
            "item_eligibility_checked",
            upc=upc,
            sku=sku,
            category=category,
            is_eligible=is_eligible,
        )
        
        return is_eligible, category
    
    def check_transaction_eligibility(
        self,
        items: List[Dict],
    ) -> tuple[PolicyDecision, List[Item], Decimal]:
        """
        Check eligibility for a transaction with multiple items.
        
        Args:
            items: List of item dicts with upc, sku, product_name, category, price, quantity
            
        Returns:
            Tuple of (decision: PolicyDecision, processed_items: List[Item], approved_amount: Decimal)
        """
        processed_items = []
        approved_amount = Decimal("0.00")
        denied_items = []
        
        for item_data in items:
            item = Item(
                upc=item_data.get("upc"),
                sku=item_data.get("sku"),
                product_name=item_data.get("product_name"),
                category=item_data.get("category"),
                price=Decimal(str(item_data.get("price", 0))),
                quantity=int(item_data.get("quantity", 1)),
            )
            
            processed_items.append(item)
            
            if item.is_eligible:
                approved_amount += item.price * item.quantity
            else:
                denied_items.append(item)
        
        # Determine decision
        if len(denied_items) == 0:
            decision = PolicyDecision.APPROVE
        elif len(denied_items) == len(processed_items):
            decision = PolicyDecision.DENY
        else:
            decision = PolicyDecision.PARTIAL
        
        logger.info(
            "transaction_eligibility_checked",
            total_items=len(processed_items),
            approved_items=len(processed_items) - len(denied_items),
            denied_items=len(denied_items),
            approved_amount=float(approved_amount),
            decision=decision.value,
        )
        
        return decision, processed_items, approved_amount


# Global policy engine instance
policy_engine = PolicyEngine()


def check_item_eligibility(
    upc: Optional[str] = None,
    sku: Optional[str] = None,
    product_name: Optional[str] = None,
    category: Optional[str] = None,
) -> tuple[bool, str]:
    """Convenience function to check item eligibility"""
    return policy_engine.check_item_eligibility(upc, sku, product_name, category)


def check_transaction_eligibility(items: List[Dict]) -> tuple[PolicyDecision, List[Item], Decimal]:
    """Convenience function to check transaction eligibility"""
    return policy_engine.check_transaction_eligibility(items)

