# Rewards Service - Saint-Daniels Project

A headless backend service for managing user rewards, balances, and redemptions with SNAP-like eligibility enforcement.

## Overview

This service provides a secure, auditable rewards system that:
- Tracks user balances and transactions via an immutable ledger
- Enforces SNAP-like eligibility rules (food, groceries, pharmacy only)
- Integrates with Stripe Connect for platform-controlled balances
- Supports iOS and Android clients via REST API
- Maintains full audit trails for compliance

## Architecture

- **Backend**: Python (FastAPI)
- **Database**: PostgreSQL (Cloud SQL)
- **Payment Processing**: Stripe Connect
- **Authentication**: JWT verification (issued by Core service)
- **Deployment**: Google Cloud Run
- **CI/CD**: GitHub Actions

## Features

### Core Functionality
- ✅ Immutable transaction ledger
- ✅ Balance tracking (derived from ledger)
- ✅ SNAP-like eligibility enforcement (UPC/SKU classification)
- ✅ Stripe Connect integration
- ✅ Full audit logging
- ✅ JWT authentication

### Policy Enforcement
- ✅ Item-level eligibility checks
- ✅ Default-deny for unknown items
- ✅ Blocked categories: alcohol, tobacco, hot food, non-food merchandise
- ✅ Allowed categories: groceries, pharmacy, prescriptions

## Project Structure

```
rewards/
├── src/
│   ├── api/              # REST API endpoints
│   ├── auth/             # JWT verification
│   ├── ledger/           # Immutable ledger system
│   ├── stripe_integration/  # Stripe Connect
│   ├── policy_engine/    # SNAP-like eligibility
│   ├── audit/            # Audit logging
│   └── db/               # Database connection & models
├── tests/                # Test suite
├── infra/                # Deployment configs
└── .github/workflows/    # CI/CD pipelines
```

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Stripe account with Connect enabled
- Google Cloud Platform account (for deployment)

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (copy from `infra/secrets.example.env`):
```bash
export DB_CONNECTION_STRING="postgresql://user:pass@localhost/rewards"
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
export JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the service:
```bash
uvicorn src.api.routes:app --host 0.0.0.0 --port 8000
```

## API Endpoints

All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

### Balance & Transactions
- `GET /balance` - Get current reward balance
- `GET /transactions` - Get transaction history

### Rewards Operations
- `POST /earn` - Register earned rewards
- `POST /spend` - Spend rewards (with eligibility check)
- `POST /redeem` - Convert rewards to partner credits

### Webhooks
- `POST /webhooks/stripe` - Stripe Connect webhook handler

## Testing

Run tests:
```bash
pytest tests/
```

## Deployment

Deployment is automated via GitHub Actions. On push to `main`, the service:
1. Builds Docker image
2. Pushes to Google Artifact Registry
3. Deploys to Cloud Run

See `.github/workflows/deploy.yml` for details.

## Security & Compliance

- All transactions are immutable and auditable
- JWT tokens verified on every request
- Secrets stored in Google Secret Manager
- Full audit trail for regulatory compliance
- No PII stored in logs (user IDs hashed)

## License

Proprietary - Saint-Daniels Project

