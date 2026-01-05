"""Immutable ledger transaction operations"""

from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import structlog

from ..db.models import Transaction, User
from ..db.connection import db_session

logger = structlog.get_logger()


def calculate_balance_from_ledger(db: Session, user_id: UUID) -> Decimal:
    """
    Calculate user balance by summing all transactions.
    Balance is never stored - always derived from ledger.
    
    Args:
        db: Database session
        user_id: User UUID
        
    Returns:
        Current balance as Decimal
    """
    result = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id
    ).scalar()
    
    return Decimal(result or 0)


def get_user_balance(db: Session, user_id: UUID) -> Decimal:
    """
    Get current user balance.
    
    Args:
        db: Database session
        user_id: User UUID
        
    Returns:
        Current balance
    """
    balance = calculate_balance_from_ledger(db, user_id)
    logger.info("balance_retrieved", user_id=str(user_id), balance=float(balance))
    return balance


def create_transaction(
    db: Session,
    user_id: UUID,
    amount: Decimal,
    reason: str,
    stripe_ref: Optional[str] = None,
    category: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Transaction:
    """
    Create an immutable transaction in the ledger.
    
    Args:
        db: Database session
        user_id: User UUID
        amount: Transaction amount (positive for earn, negative for spend)
        reason: Transaction reason ('earn', 'spend', 'redeem')
        stripe_ref: Optional Stripe transaction reference
        category: Optional item category
        metadata: Optional additional metadata as dict
        
    Returns:
        Created Transaction object
        
    Raises:
        ValueError: If reason is invalid or amount is zero
    """
    if reason not in ["earn", "spend", "redeem"]:
        raise ValueError(f"Invalid transaction reason: {reason}")
    
    if amount == 0:
        raise ValueError("Transaction amount cannot be zero")
    
    import json
    metadata_json = json.dumps(metadata) if metadata else None
    
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        reason=reason,
        stripe_ref=stripe_ref,
        category=category,
        metadata=metadata_json,
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    logger.info(
        "transaction_created",
        transaction_id=str(transaction.transaction_id),
        user_id=str(user_id),
        amount=float(amount),
        reason=reason,
        stripe_ref=stripe_ref,
    )
    
    return transaction


def get_transaction_history(
    db: Session,
    user_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> List[Transaction]:
    """
    Get transaction history for a user.
    
    Args:
        db: Database session
        user_id: User UUID
        limit: Maximum number of transactions to return
        offset: Offset for pagination
        
    Returns:
        List of Transaction objects, ordered by created_at descending
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(
        desc(Transaction.created_at)
    ).limit(limit).offset(offset).all()
    
    logger.info(
        "transaction_history_retrieved",
        user_id=str(user_id),
        count=len(transactions),
        limit=limit,
        offset=offset,
    )
    
    return transactions


def get_transaction_by_id(db: Session, transaction_id: UUID) -> Optional[Transaction]:
    """
    Get a specific transaction by ID.
    
    Args:
        db: Database session
        transaction_id: Transaction UUID
        
    Returns:
        Transaction object or None if not found
    """
    return db.query(Transaction).filter(
        Transaction.transaction_id == transaction_id
    ).first()

