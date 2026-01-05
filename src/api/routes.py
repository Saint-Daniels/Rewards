"""FastAPI routes for Rewards service"""

from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from decimal import Decimal
from uuid import UUID
import structlog

from ..db.connection import get_db
from ..auth.jwt_verifier import get_current_user
from ..ledger.transactions import (
    get_user_balance,
    create_transaction,
    get_transaction_history,
)
from ..ledger.models import (
    TransactionResponse,
    BalanceResponse,
    TransactionHistoryResponse,
    TransactionCreate,
)
from ..policy_engine.snap_policy_engine import (
    check_transaction_eligibility,
    PolicyDecision,
)
from ..stripe_integration.connect import (
    create_stripe_account,
    get_stripe_account,
    authorize_transaction,
)
from ..stripe_integration.webhooks import handle_stripe_webhook
from ..audit.audit_log import (
    log_transaction,
    log_policy_decision,
    log_api_request,
)
from ..db.models import User

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="Rewards Service",
    description="Rewards service for Saint-Daniels project with SNAP-like eligibility",
    version="1.0.0",
)


def get_user_from_db(db: Session, user_id: UUID) -> User:
    """Get or create user in database"""
    user = db.query(User).filter(User.external_core_id == str(user_id)).first()
    if not user:
        # Create user if doesn't exist
        user = User(external_core_id=str(user_id))
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("user_created", user_id=str(user.user_id), external_core_id=str(user_id))
    return user


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Get current reward balance for authenticated user.
    """
    user_id = UUID(current_user["user_id"])
    user = get_user_from_db(db, user_id)
    
    balance = get_user_balance(db, user.user_id)
    
    # Log API request
    log_api_request(
        db,
        user.user_id,
        "/balance",
        "GET",
        {"balance": float(balance)},
        ip_address=request.client.host if request else None,
    )
    
    return BalanceResponse(
        user_id=user.user_id,
        balance=balance,
        currency="USD",
    )


@app.get("/transactions", response_model=TransactionHistoryResponse)
async def get_transactions(
    limit: int = 100,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Get transaction history for authenticated user.
    """
    user_id = UUID(current_user["user_id"])
    user = get_user_from_db(db, user_id)
    
    transactions = get_transaction_history(db, user.user_id, limit, offset)
    
    # Log API request
    log_api_request(
        db,
        user.user_id,
        "/transactions",
        "GET",
        {"limit": limit, "offset": offset},
        ip_address=request.client.host if request else None,
    )
    
    return TransactionHistoryResponse(
        transactions=[TransactionResponse.model_validate(t) for t in transactions],
        total=len(transactions),
        limit=limit,
        offset=offset,
    )


@app.post("/earn", response_model=TransactionResponse)
async def earn_rewards(
    transaction: TransactionCreate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Register earned rewards for authenticated user.
    """
    if transaction.reason != "earn":
        raise HTTPException(
            status_code=400,
            detail="Use /earn endpoint only for earning rewards"
        )
    
    if transaction.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be positive for earning"
        )
    
    user_id = UUID(current_user["user_id"])
    user = get_user_from_db(db, user_id)
    
    # Create transaction
    txn = create_transaction(
        db,
        user.user_id,
        transaction.amount,
        "earn",
        stripe_ref=transaction.stripe_ref,
        category=transaction.category,
        metadata=transaction.metadata,
    )
    
    # Log transaction
    log_transaction(
        db,
        user.user_id,
        "earn",
        {
            "transaction_id": str(txn.transaction_id),
            "amount": float(transaction.amount),
            "stripe_ref": transaction.stripe_ref,
        },
        ip_address=request.client.host if request else None,
    )
    
    return TransactionResponse.model_validate(txn)


@app.post("/spend", response_model=Dict[str, Any])
async def spend_rewards(
    items: List[Dict[str, Any]],
    amount: Decimal,
    merchant_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Spend rewards with SNAP-like eligibility check.
    Requires items list with UPC/SKU for policy engine.
    """
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be positive"
        )
    
    if not items:
        raise HTTPException(
            status_code=400,
            detail="Items list cannot be empty"
        )
    
    user_id = UUID(current_user["user_id"])
    user = get_user_from_db(db, user_id)
    
    # Check current balance
    balance = get_user_balance(db, user.user_id)
    if balance < amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Current: ${balance}, Required: ${amount}"
        )
    
    # Check eligibility via policy engine
    decision, processed_items, approved_amount = check_transaction_eligibility(items)
    
    # Log policy decision
    log_policy_decision(
        db,
        user.user_id,
        decision.value,
        [{"upc": item.upc, "sku": item.sku, "category": item.category, "eligible": item.is_eligible} for item in processed_items],
        float(approved_amount),
        {"merchant_id": merchant_id},
        ip_address=request.client.host if request else None,
    )
    
    # If denied, reject transaction
    if decision == PolicyDecision.DENY:
        raise HTTPException(
            status_code=403,
            detail="Transaction denied: All items are ineligible for SNAP-like redemption"
        )
    
    # If partial, only approve eligible amount
    if decision == PolicyDecision.PARTIAL:
        if approved_amount < amount:
            raise HTTPException(
                status_code=403,
                detail=f"Transaction partially denied. Only ${approved_amount} eligible, requested ${amount}"
            )
        # Use approved amount
        amount = approved_amount
    
    # Authorize with Stripe
    stripe_account = get_stripe_account(db, user.user_id)
    if not stripe_account:
        # Create Stripe account if doesn't exist
        stripe_account = create_stripe_account(db, user.user_id)
    
    authorized, payment_intent_id = authorize_transaction(
        db,
        user.user_id,
        amount,
        items,
        merchant_id,
    )
    
    if not authorized:
        raise HTTPException(
            status_code=500,
            detail="Failed to authorize transaction with Stripe"
        )
    
    # Create transaction record
    txn = create_transaction(
        db,
        user.user_id,
        -amount,  # Negative for spend
        "spend",
        stripe_ref=payment_intent_id,
        category="mixed",
        metadata={
            "merchant_id": merchant_id,
            "item_count": len(items),
            "decision": decision.value,
            "approved_amount": float(approved_amount),
        },
    )
    
    # Log transaction
    log_transaction(
        db,
        user.user_id,
        "spend",
        {
            "transaction_id": str(txn.transaction_id),
            "amount": float(amount),
            "payment_intent_id": payment_intent_id,
            "merchant_id": merchant_id,
            "decision": decision.value,
        },
        ip_address=request.client.host if request else None,
    )
    
    return {
        "transaction_id": str(txn.transaction_id),
        "status": "approved",
        "amount": float(amount),
        "payment_intent_id": payment_intent_id,
        "decision": decision.value,
        "approved_amount": float(approved_amount),
    }


@app.post("/redeem", response_model=TransactionResponse)
async def redeem_rewards(
    transaction: TransactionCreate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Convert rewards to partner credits (if applicable).
    """
    if transaction.reason != "redeem":
        raise HTTPException(
            status_code=400,
            detail="Use /redeem endpoint only for redemption"
        )
    
    if transaction.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be positive"
        )
    
    user_id = UUID(current_user["user_id"])
    user = get_user_from_db(db, user_id)
    
    # Check balance
    balance = get_user_balance(db, user.user_id)
    if balance < transaction.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Current: ${balance}, Required: ${transaction.amount}"
        )
    
    # Create transaction
    txn = create_transaction(
        db,
        user.user_id,
        -transaction.amount,  # Negative for redeem
        "redeem",
        stripe_ref=transaction.stripe_ref,
        category=transaction.category,
        metadata=transaction.metadata,
    )
    
    # Log transaction
    log_transaction(
        db,
        user.user_id,
        "redeem",
        {
            "transaction_id": str(txn.transaction_id),
            "amount": float(transaction.amount),
        },
        ip_address=request.client.host if request else None,
    )
    
    return TransactionResponse.model_validate(txn)


@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(None),
):
    """
    Handle Stripe webhook events.
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Stripe signature header"
        )
    
    payload = await request.body()
    
    try:
        result = handle_stripe_webhook(
            db,
            payload,
            stripe_signature,
            ip_address=request.client.host,
        )
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

