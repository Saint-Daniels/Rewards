"""Tests for ledger/transaction system"""

import pytest
from decimal import Decimal
from uuid import uuid4
from src.ledger.transactions import (
    create_transaction,
    get_user_balance,
    get_transaction_history,
    calculate_balance_from_ledger,
)


def test_create_transaction_earn(db_session, test_user):
    """Test creating an earn transaction"""
    txn = create_transaction(
        db_session,
        test_user.user_id,
        Decimal("10.00"),
        "earn",
        category="groceries",
    )
    
    assert txn.amount == Decimal("10.00")
    assert txn.reason == "earn"
    assert txn.user_id == test_user.user_id


def test_create_transaction_spend(db_session, test_user):
    """Test creating a spend transaction"""
    # First earn some rewards
    create_transaction(
        db_session,
        test_user.user_id,
        Decimal("20.00"),
        "earn",
    )
    
    # Then spend
    txn = create_transaction(
        db_session,
        test_user.user_id,
        Decimal("-5.00"),
        "spend",
        category="groceries",
    )
    
    assert txn.amount == Decimal("-5.00")
    assert txn.reason == "spend"


def test_get_user_balance(db_session, test_user):
    """Test balance calculation"""
    # Initial balance should be zero
    balance = get_user_balance(db_session, test_user.user_id)
    assert balance == Decimal("0.00")
    
    # Earn rewards
    create_transaction(db_session, test_user.user_id, Decimal("10.00"), "earn")
    create_transaction(db_session, test_user.user_id, Decimal("5.00"), "earn")
    
    balance = get_user_balance(db_session, test_user.user_id)
    assert balance == Decimal("15.00")
    
    # Spend some
    create_transaction(db_session, test_user.user_id, Decimal("-3.00"), "spend")
    
    balance = get_user_balance(db_session, test_user.user_id)
    assert balance == Decimal("12.00")


def test_transaction_history(db_session, test_user):
    """Test getting transaction history"""
    # Create multiple transactions
    for i in range(5):
        create_transaction(
            db_session,
            test_user.user_id,
            Decimal(f"{i+1}.00"),
            "earn",
        )
    
    history = get_transaction_history(db_session, test_user.user_id, limit=10)
    assert len(history) == 5
    
    # Should be ordered by created_at descending
    amounts = [txn.amount for txn in history]
    assert amounts == sorted(amounts, reverse=True)


def test_invalid_transaction_reason(db_session, test_user):
    """Test that invalid transaction reason raises error"""
    with pytest.raises(ValueError):
        create_transaction(
            db_session,
            test_user.user_id,
            Decimal("10.00"),
            "invalid_reason",
        )


def test_zero_amount_transaction(db_session, test_user):
    """Test that zero amount raises error"""
    with pytest.raises(ValueError):
        create_transaction(
            db_session,
            test_user.user_id,
            Decimal("0.00"),
            "earn",
        )

