# Quick Start Guide

## Local Development Setup

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Stripe account (test mode is fine for development)

### 2. Clone and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp infra/secrets.example.env .env

# Edit .env with your values
# - DB_CONNECTION_STRING: PostgreSQL connection string
# - STRIPE_SECRET_KEY: Your Stripe test secret key
# - STRIPE_WEBHOOK_SECRET: Your Stripe webhook secret
# - JWT_PUBLIC_KEY: Public key from Core service for JWT verification
```

### 3. Database Setup
```bash
# Create database
createdb rewards

# Run migrations
alembic upgrade head
```

### 4. Run the Service
```bash
# Development mode
python src/main.py

# Or with uvicorn directly
uvicorn src.api.routes:app --reload --port 8000
```

### 5. Test the API
```bash
# Health check
curl http://localhost:8000/health

# Get balance (requires JWT token)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/balance
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_ledger.py
```

## Deployment

### Google Cloud Run

1. **Set up GCP project:**
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Create secrets in Secret Manager:**
   ```bash
   echo -n "your-db-connection-string" | gcloud secrets create db-connection-string --data-file=-
   echo -n "sk_test_..." | gcloud secrets create stripe-secret-key --data-file=-
   echo -n "whsec_..." | gcloud secrets create stripe-webhook-secret --data-file=-
   echo -n "-----BEGIN PUBLIC KEY-----..." | gcloud secrets create jwt-public-key --data-file=-
   ```

3. **Configure GitHub Secrets:**
   - `GCP_PROJECT_ID`: Your GCP project ID
   - `GCP_SA_KEY`: Service account JSON key
   - `DB_CONNECTION_STRING`: Database connection string

4. **Push to main branch:**
   - GitHub Actions will automatically build and deploy

## API Usage Examples

### Earn Rewards
```bash
curl -X POST http://localhost:8000/earn \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "10.00",
    "reason": "earn",
    "category": "groceries"
  }'
```

### Spend Rewards (with eligibility check)
```bash
curl -X POST http://localhost:8000/spend \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "product_name": "Milk",
        "category": "dairy",
        "price": "3.50",
        "quantity": 1
      }
    ],
    "amount": "3.50",
    "merchant_id": "kroger_123"
  }'
```

### Get Transaction History
```bash
curl http://localhost:8000/transactions?limit=10&offset=0 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Policy Engine

The policy engine enforces SNAP-like eligibility:

- **Allowed**: Groceries, fresh produce, dairy, bakery, pharmacy, prescriptions
- **Disallowed**: Alcohol, tobacco, hot prepared foods, non-food items
- **Default**: Unknown items are denied (default-deny)

## Architecture Notes

- **Immutable Ledger**: All transactions are append-only
- **Balance Calculation**: Always derived from ledger, never stored
- **Audit Trail**: Every action is logged with hashed user IDs (no PII)
- **Stripe Connect**: Platform-controlled balances, users can only spend on eligible items

