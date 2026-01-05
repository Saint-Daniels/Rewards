"""Stripe webhook handler with idempotency"""

import os
import stripe
import json
from typing import Dict, Any, Optional
from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
import structlog

from ..db.models import Transaction, StripeAccount
from ..ledger.transactions import create_transaction
from ..audit.audit_log import log_webhook_event

logger = structlog.get_logger()

# Get webhook secret
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Track processed events for idempotency
processed_events: Dict[str, bool] = {}


def handle_stripe_webhook(
    db: Session,
    payload: bytes,
    signature: str,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handle Stripe webhook event with idempotency.
    
    Args:
        db: Database session
        payload: Raw webhook payload
        signature: Stripe signature header
        ip_address: Optional IP address
        
    Returns:
        Response dict
        
    Raises:
        ValueError: If signature is invalid
        Exception: If webhook processing fails
    """
    if not WEBHOOK_SECRET:
        logger.error("stripe_webhook_secret_missing")
        raise ValueError("Stripe webhook secret not configured")
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            WEBHOOK_SECRET,
        )
        
        event_id = event.get("id")
        event_type = event.get("type")
        
        # Check idempotency
        if event_id in processed_events:
            logger.info("webhook_already_processed", event_id=event_id)
            return {"status": "already_processed", "event_id": event_id}
        
        # Log webhook event
        log_webhook_event(
            db,
            user_id=None,  # Will be extracted from event if available
            event_type=event_type,
            details={
                "event_id": event_id,
                "type": event_type,
                "data": event.get("data", {}),
            },
            ip_address=ip_address,
        )
        
        # Process event based on type
        if event_type == "payment_intent.succeeded":
            _handle_payment_succeeded(db, event)
        elif event_type == "payment_intent.payment_failed":
            _handle_payment_failed(db, event)
        elif event_type == "transfer.created":
            _handle_transfer_created(db, event)
        elif event_type == "account.updated":
            _handle_account_updated(db, event)
        else:
            logger.info("webhook_event_ignored", event_type=event_type)
        
        # Mark as processed
        processed_events[event_id] = True
        
        logger.info("webhook_processed", event_id=event_id, event_type=event_type)
        
        return {"status": "success", "event_id": event_id}
        
    except ValueError as e:
        logger.error("webhook_signature_invalid", error=str(e))
        raise
    except stripe.error.SignatureVerificationError as e:
        logger.error("webhook_signature_verification_failed", error=str(e))
        raise ValueError("Invalid webhook signature")
    except Exception as e:
        logger.error("webhook_processing_error", error=str(e))
        raise


def _handle_payment_succeeded(db: Session, event: Dict[str, Any]):
    """Handle payment_intent.succeeded event"""
    payment_intent = event["data"]["object"]
    metadata = payment_intent.get("metadata", {})
    user_id = metadata.get("user_id")
    
    if not user_id:
        logger.warning("payment_succeeded_no_user_id", payment_intent_id=payment_intent.get("id"))
        return
    
    # Create transaction record
    amount = Decimal(payment_intent["amount"]) / 100  # Convert from cents
    create_transaction(
        db,
        user_id=UUID(user_id),
        amount=-amount,  # Negative for spend
        reason="spend",
        stripe_ref=payment_intent["id"],
        metadata={"event_type": "payment_intent.succeeded"},
    )


def _handle_payment_failed(db: Session, event: Dict[str, Any]):
    """Handle payment_intent.payment_failed event"""
    payment_intent = event["data"]["object"]
    logger.warning("payment_failed", payment_intent_id=payment_intent.get("id"))


def _handle_transfer_created(db: Session, event: Dict[str, Any]):
    """Handle transfer.created event"""
    transfer = event["data"]["object"]
    destination = transfer.get("destination")
    
    # Find user by Stripe account ID
    stripe_account = db.query(StripeAccount).filter(
        StripeAccount.stripe_account_id == destination
    ).first()
    
    if stripe_account:
        amount = Decimal(transfer["amount"]) / 100
        create_transaction(
            db,
            user_id=stripe_account.user_id,
            amount=amount,  # Positive for earn
            reason="earn",
            stripe_ref=transfer["id"],
            metadata={"event_type": "transfer.created"},
        )


def _handle_account_updated(db: Session, event: Dict[str, Any]):
    """Handle account.updated event"""
    account = event["data"]["object"]
    logger.info("stripe_account_updated", account_id=account.get("id"))

