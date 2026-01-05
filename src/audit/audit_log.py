"""Immutable audit logging system"""

import hashlib
import json
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
import structlog

from ..db.models import AuditLog

logger = structlog.get_logger()


def _hash_user_id(user_id: UUID) -> str:
    """Hash user ID for privacy (SHA-256)"""
    return hashlib.sha256(str(user_id).encode()).hexdigest()


def log_transaction(
    db: Session,
    user_id: UUID,
    event_type: str,
    details: Dict[str, Any],
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Log a transaction event.
    
    Args:
        db: Database session
        user_id: User UUID
        event_type: Event type ('earn', 'spend', 'redeem', etc.)
        details: Event details as dict
        ip_address: Optional IP address
        
    Returns:
        Created AuditLog entry
    """
    audit_entry = AuditLog(
        user_id_hash=_hash_user_id(user_id),
        action="transaction",
        event_type=event_type,
        details=json.dumps(details),
        ip_address=ip_address,
    )
    
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    
    logger.info(
        "audit_transaction_logged",
        user_id_hash=audit_entry.user_id_hash,
        event_type=event_type,
    )
    
    return audit_entry


def log_policy_decision(
    db: Session,
    user_id: UUID,
    decision: str,
    items: list,
    approved_amount: float,
    details: Dict[str, Any],
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Log a policy engine decision.
    
    Args:
        db: Database session
        user_id: User UUID
        decision: Decision result ('approve', 'deny', 'partial')
        items: List of items checked
        approved_amount: Amount approved
        details: Additional details
        ip_address: Optional IP address
        
    Returns:
        Created AuditLog entry
    """
    audit_entry = AuditLog(
        user_id_hash=_hash_user_id(user_id),
        action="policy_decision",
        event_type=decision,
        details=json.dumps({
            "items": items,
            "approved_amount": approved_amount,
            **details,
        }),
        ip_address=ip_address,
    )
    
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    
    logger.info(
        "audit_policy_decision_logged",
        user_id_hash=audit_entry.user_id_hash,
        decision=decision,
        approved_amount=approved_amount,
    )
    
    return audit_entry


def log_webhook_event(
    db: Session,
    user_id: Optional[UUID],
    event_type: str,
    details: Dict[str, Any],
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Log a webhook event.
    
    Args:
        db: Database session
        user_id: Optional user UUID (may not be available for all webhooks)
        event_type: Webhook event type
        details: Event details
        ip_address: Optional IP address
        
    Returns:
        Created AuditLog entry
    """
    user_id_hash = _hash_user_id(user_id) if user_id else None
    
    audit_entry = AuditLog(
        user_id_hash=user_id_hash or "system",
        action="webhook",
        event_type=event_type,
        details=json.dumps(details),
        ip_address=ip_address,
    )
    
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    
    logger.info(
        "audit_webhook_logged",
        event_type=event_type,
        user_id_hash=user_id_hash,
    )
    
    return audit_entry


def log_api_request(
    db: Session,
    user_id: UUID,
    endpoint: str,
    method: str,
    details: Dict[str, Any],
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Log an API request.
    
    Args:
        db: Database session
        user_id: User UUID
        endpoint: API endpoint
        method: HTTP method
        details: Request details
        ip_address: Optional IP address
        
    Returns:
        Created AuditLog entry
    """
    audit_entry = AuditLog(
        user_id_hash=_hash_user_id(user_id),
        action="api_request",
        event_type=f"{method} {endpoint}",
        details=json.dumps(details),
        ip_address=ip_address,
    )
    
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    
    return audit_entry

