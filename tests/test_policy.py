"""Tests for SNAP-like policy engine"""

import pytest
from decimal import Decimal
from src.policy_engine.snap_policy_engine import (
    check_item_eligibility,
    check_transaction_eligibility,
    PolicyDecision,
)


def test_eligible_item():
    """Test checking eligible item"""
    is_eligible, category = check_item_eligibility(
        product_name="Fresh Apples",
        category="groceries",
    )
    assert is_eligible is True
    assert category == "groceries"


def test_ineligible_alcohol():
    """Test that alcohol is ineligible"""
    is_eligible, category = check_item_eligibility(
        product_name="Beer",
        category="alcohol",
    )
    assert is_eligible is False
    assert category == "alcohol"


def test_ineligible_tobacco():
    """Test that tobacco is ineligible"""
    is_eligible, category = check_item_eligibility(
        product_name="Cigarettes",
        category="tobacco",
    )
    assert is_eligible is False


def test_ineligible_hot_food():
    """Test that hot food is ineligible"""
    is_eligible, category = check_item_eligibility(
        product_name="Hot Deli Pizza",
        category="hot_food",
    )
    assert is_eligible is False


def test_eligible_pharmacy():
    """Test that pharmacy items are eligible"""
    is_eligible, category = check_item_eligibility(
        product_name="Prescription Medication",
        category="prescription",
    )
    assert is_eligible is True


def test_transaction_all_eligible():
    """Test transaction with all eligible items"""
    items = [
        {"product_name": "Milk", "category": "dairy", "price": Decimal("3.50"), "quantity": 1},
        {"product_name": "Bread", "category": "bakery", "price": Decimal("2.00"), "quantity": 1},
    ]
    
    decision, processed_items, approved_amount = check_transaction_eligibility(items)
    
    assert decision == PolicyDecision.APPROVE
    assert approved_amount == Decimal("5.50")
    assert all(item.is_eligible for item in processed_items)


def test_transaction_all_ineligible():
    """Test transaction with all ineligible items"""
    items = [
        {"product_name": "Beer", "category": "alcohol", "price": Decimal("5.00"), "quantity": 1},
        {"product_name": "Cigarettes", "category": "tobacco", "price": Decimal("8.00"), "quantity": 1},
    ]
    
    decision, processed_items, approved_amount = check_transaction_eligibility(items)
    
    assert decision == PolicyDecision.DENY
    assert approved_amount == Decimal("0.00")
    assert not any(item.is_eligible for item in processed_items)


def test_transaction_partial():
    """Test transaction with mixed eligible/ineligible items"""
    items = [
        {"product_name": "Milk", "category": "dairy", "price": Decimal("3.50"), "quantity": 1},
        {"product_name": "Beer", "category": "alcohol", "price": Decimal("5.00"), "quantity": 1},
    ]
    
    decision, processed_items, approved_amount = check_transaction_eligibility(items)
    
    assert decision == PolicyDecision.PARTIAL
    assert approved_amount == Decimal("3.50")
    assert processed_items[0].is_eligible is True
    assert processed_items[1].is_eligible is False


def test_unknown_item_default_deny():
    """Test that unknown items are default-deny"""
    is_eligible, category = check_item_eligibility(
        product_name="Unknown Product XYZ123",
    )
    assert is_eligible is False
    assert category == "unknown"

