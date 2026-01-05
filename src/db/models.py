"""SQLAlchemy models for the rewards service"""

from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .connection import Base


class User(Base):
    """User model - links to external Core service user"""
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_core_id = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="user")
    stripe_account = relationship("StripeAccount", back_populates="user", uselist=False)


class Transaction(Base):
    """Immutable transaction ledger"""
    __tablename__ = "transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)  # Positive for earn, negative for spend
    reason = Column(String(50), nullable=False)  # 'earn', 'spend', 'redeem'
    stripe_ref = Column(String(255), nullable=True, index=True)  # Stripe transaction reference
    category = Column(String(100), nullable=True)  # Item category if applicable
    metadata = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="transactions")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_user_created", "user_id", "created_at"),
        Index("idx_stripe_ref", "stripe_ref"),
    )


class StripeAccount(Base):
    """Stripe Connect account mapping"""
    __tablename__ = "stripe_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), unique=True, nullable=False, index=True)
    stripe_account_id = Column(String(255), unique=True, nullable=False, index=True)
    account_type = Column(String(50), nullable=False)  # 'express' or 'custom'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="stripe_account")


class Campaign(Base):
    """Reward campaigns/promotions (optional)"""
    __tablename__ = "campaigns"

    campaign_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    reward_multiplier = Column(Numeric(5, 2), default=1.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    """Immutable audit log for compliance"""
    __tablename__ = "audit_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of user_id
    action = Column(String(100), nullable=False)  # 'transaction', 'policy_decision', 'webhook', etc.
    event_type = Column(String(100), nullable=False)  # 'earn', 'spend', 'approve', 'deny', etc.
    details = Column(Text, nullable=True)  # JSON string with event details
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indexes
    __table_args__ = (
        Index("idx_user_action_created", "user_id_hash", "action", "created_at"),
    )

