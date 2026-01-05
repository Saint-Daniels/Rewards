"""Pydantic models for ledger operations"""

from pydantic import BaseModel, Field
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any


class TransactionCreate(BaseModel):
    """Request model for creating a transaction"""
    amount: Decimal = Field(..., description="Transaction amount (positive for earn, negative for spend)")
    reason: str = Field(..., description="Transaction reason: 'earn', 'spend', or 'redeem'")
    stripe_ref: Optional[str] = Field(None, description="Stripe transaction reference")
    category: Optional[str] = Field(None, description="Item category")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TransactionResponse(BaseModel):
    """Response model for transaction"""
    transaction_id: UUID
    user_id: UUID
    amount: Decimal
    reason: str
    stripe_ref: Optional[str]
    category: Optional[str]
    metadata: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class BalanceResponse(BaseModel):
    """Response model for user balance"""
    user_id: UUID
    balance: Decimal
    currency: str = "USD"


class TransactionHistoryResponse(BaseModel):
    """Response model for transaction history"""
    transactions: list[TransactionResponse]
    total: int
    limit: int
    offset: int

