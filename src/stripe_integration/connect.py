"""Stripe Connect account management and transactions"""

import os
import stripe
from typing import Optional
from uuid import UUID
from decimal import Decimal
from sqlalchemy.orm import Session
import structlog

from ..db.models import User, StripeAccount
from ..db.connection import db_session

logger = structlog.get_logger()

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

if not stripe.api_key:
    logger.warning("stripe_api_key_missing")


def create_stripe_account(
    db: Session,
    user_id: UUID,
    account_type: str = "express",
    email: Optional[str] = None,
) -> StripeAccount:
    """
    Create a Stripe Connect account for a user.
    
    Args:
        db: Database session
        user_id: User UUID
        account_type: 'express' or 'custom'
        email: User email (optional)
        
    Returns:
        StripeAccount object
        
    Raises:
        ValueError: If account type is invalid
        Exception: If Stripe API call fails
    """
    if account_type not in ["express", "custom"]:
        raise ValueError(f"Invalid account type: {account_type}")
    
    # Check if account already exists
    existing = db.query(StripeAccount).filter(
        StripeAccount.user_id == user_id
    ).first()
    
    if existing:
        logger.info("stripe_account_exists", user_id=str(user_id))
        return existing
    
    try:
        # Create Stripe Connect account
        if account_type == "express":
            account = stripe.Account.create(
                type="express",
                country="US",
                email=email,
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
            )
        else:  # custom
            account = stripe.Account.create(
                type="custom",
                country="US",
                email=email,
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
            )
        
        # Store in database
        stripe_account = StripeAccount(
            user_id=user_id,
            stripe_account_id=account.id,
            account_type=account_type,
            is_active=True,
        )
        
        db.add(stripe_account)
        db.commit()
        db.refresh(stripe_account)
        
        logger.info(
            "stripe_account_created",
            user_id=str(user_id),
            stripe_account_id=account.id,
            account_type=account_type,
        )
        
        return stripe_account
        
    except stripe.error.StripeError as e:
        logger.error("stripe_account_creation_failed", error=str(e))
        raise Exception(f"Failed to create Stripe account: {str(e)}")


def get_stripe_account(db: Session, user_id: UUID) -> Optional[StripeAccount]:
    """
    Get Stripe account for a user.
    
    Args:
        db: Database session
        user_id: User UUID
        
    Returns:
        StripeAccount object or None
    """
    return db.query(StripeAccount).filter(
        StripeAccount.user_id == user_id,
        StripeAccount.is_active == True,
    ).first()


def update_stripe_balance(
    db: Session,
    user_id: UUID,
    amount: Decimal,
    description: str,
) -> str:
    """
    Update Stripe balance for a user (add funds).
    This would typically be called when rewards are earned.
    
    Args:
        db: Database session
        user_id: User UUID
        amount: Amount to add (positive)
        description: Transaction description
        
    Returns:
        Stripe transaction reference
        
    Raises:
        ValueError: If amount is not positive
        Exception: If Stripe API call fails
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    stripe_account = get_stripe_account(db, user_id)
    if not stripe_account:
        raise ValueError(f"No Stripe account found for user {user_id}")
    
    try:
        # Create a transfer to the connected account
        # In production, this would use Stripe Connect transfers
        transfer = stripe.Transfer.create(
            amount=int(amount * 100),  # Convert to cents
            currency="usd",
            destination=stripe_account.stripe_account_id,
            description=description,
        )
        
        logger.info(
            "stripe_balance_updated",
            user_id=str(user_id),
            amount=float(amount),
            transfer_id=transfer.id,
        )
        
        return transfer.id
        
    except stripe.error.StripeError as e:
        logger.error("stripe_balance_update_failed", error=str(e))
        raise Exception(f"Failed to update Stripe balance: {str(e)}")


def authorize_transaction(
    db: Session,
    user_id: UUID,
    amount: Decimal,
    items: list,
    merchant_id: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Authorize a transaction in Stripe (only if all items are eligible).
    This creates a payment intent that can be captured later.
    
    Args:
        db: Database session
        user_id: User UUID
        amount: Transaction amount (positive, will be deducted)
        items: List of items (for logging)
        merchant_id: Optional merchant identifier
        
    Returns:
        Tuple of (authorized: bool, payment_intent_id: Optional[str])
        
    Raises:
        ValueError: If amount is not positive
        Exception: If Stripe API call fails
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    stripe_account = get_stripe_account(db, user_id)
    if not stripe_account:
        raise ValueError(f"No Stripe account found for user {user_id}")
    
    try:
        # Create a payment intent on the connected account
        # In production, this would be more complex with actual payment methods
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency="usd",
            customer=None,  # Would be linked to user's payment method
            description=f"Rewards redemption - {len(items)} items",
            metadata={
                "user_id": str(user_id),
                "merchant_id": merchant_id or "unknown",
                "item_count": str(len(items)),
            },
        )
        
        logger.info(
            "stripe_transaction_authorized",
            user_id=str(user_id),
            amount=float(amount),
            payment_intent_id=payment_intent.id,
        )
        
        return True, payment_intent.id
        
    except stripe.error.StripeError as e:
        logger.error("stripe_authorization_failed", error=str(e))
        return False, None

