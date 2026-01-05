"""Tests for Stripe integration"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from src.stripe_integration.connect import (
    create_stripe_account,
    get_stripe_account,
    authorize_transaction,
)


@patch('src.stripe_integration.connect.stripe')
def test_create_stripe_account(mock_stripe, db_session, test_user):
    """Test creating Stripe account"""
    # Mock Stripe API response
    mock_account = MagicMock()
    mock_account.id = "acct_test123"
    mock_stripe.Account.create.return_value = mock_account
    
    account = create_stripe_account(
        db_session,
        test_user.user_id,
        account_type="express",
    )
    
    assert account.stripe_account_id == "acct_test123"
    assert account.user_id == test_user.user_id
    assert account.account_type == "express"


def test_get_stripe_account_none(db_session, test_user):
    """Test getting non-existent Stripe account"""
    account = get_stripe_account(db_session, test_user.user_id)
    assert account is None


@patch('src.stripe_integration.connect.stripe')
def test_authorize_transaction(mock_stripe, db_session, test_user):
    """Test authorizing a transaction"""
    # Create Stripe account first
    from src.db.models import StripeAccount
    stripe_account = StripeAccount(
        user_id=test_user.user_id,
        stripe_account_id="acct_test123",
        account_type="express",
        is_active=True,
    )
    db_session.add(stripe_account)
    db_session.commit()
    
    # Mock Stripe PaymentIntent
    mock_payment_intent = MagicMock()
    mock_payment_intent.id = "pi_test123"
    mock_stripe.PaymentIntent.create.return_value = mock_payment_intent
    
    authorized, payment_intent_id = authorize_transaction(
        db_session,
        test_user.user_id,
        Decimal("10.00"),
        [{"product_name": "Milk"}],
    )
    
    assert authorized is True
    assert payment_intent_id == "pi_test123"


def test_authorize_transaction_no_account(db_session, test_user):
    """Test authorizing without Stripe account"""
    with pytest.raises(ValueError, match="No Stripe account"):
        authorize_transaction(
            db_session,
            test_user.user_id,
            Decimal("10.00"),
            [],
        )

