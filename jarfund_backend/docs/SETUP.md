# JarFund Backend — Setup Guide

## Prerequisites
- Python 3.12+
- Docker & Docker Compose (for PostgreSQL + Redis)
- Git

---

## 1. Clone & Virtual Environment

```bash
# Navigate to your project root
cd jarfund_backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

# Install all dependencies
pip install -r requirements.txt
```

---

## 2. Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env — fill in at minimum:
#   SECRET_KEY       → generate with the command below
#   CONTRACT_ADDRESS → fill after Step 1 (smart contract deploy)
#   DATABASE_URL     → already correct if using docker-compose

python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 3. Start PostgreSQL + Redis (Docker)

```bash
docker compose up -d

# Verify they're running:
docker compose ps
```

Expected output:
```
NAME                STATUS
jarfund_postgres    running (healthy)
jarfund_redis       running (healthy)
```

---

## 4. Database Setup

```bash
# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.settings.local

# Run migrations
python manage.py migrate

# Create a superuser for the admin panel
python manage.py createsuperuser
# (wallet_address will be asked — use your MetaMask address)
```

---

## 5. Copy Contract ABI

After deploying the smart contract (Step 1 of the project):

```bash
# Create the ABI directory
mkdir -p apps/blockchain/abi

# Copy the compiled ABI from your Hardhat project:
cp ../blockchain/artifacts/contracts/JarFund.sol/JarFund.json apps/blockchain/abi/
```

---

## 6. Run the Development Server

```bash
python manage.py runserver 8000
```

API is now available at:
- `http://localhost:8000/api/v1/`
- `http://localhost:8000/api/docs/` (Swagger UI)
- `http://localhost:8000/api/redoc/` (ReDoc)
- `http://localhost:8000/health/` (Health check)

---

## 7. Start Celery Workers (for blockchain verification)

Open two additional terminal windows:

```bash
# Terminal 2 — Celery worker
export DJANGO_SETTINGS_MODULE=config.settings.local
celery -A config.celery worker --loglevel=info

# Terminal 3 — Celery beat (periodic tasks)
export DJANGO_SETTINGS_MODULE=config.settings.local
celery -A config.celery beat --loglevel=info
```

---

## 8. Run Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=apps --cov-report=html
open htmlcov/index.html
```

---

## Project Structure

```
jarfund_backend/
├── config/
│   ├── settings/
│   │   ├── base.py          ← Shared settings
│   │   ├── local.py         ← Development overrides
│   │   └── production.py    ← Production (Railway/Render)
│   ├── urls.py              ← Root URL config
│   ├── wsgi.py              ← Gunicorn entry point
│   └── celery.py            ← Async task queue
│
├── apps/
│   ├── users/               ← Custom User model (wallet auth)
│   ├── jars/                ← Fundraising Jar model & API
│   ├── donations/           ← Donation model & API
│   └── blockchain/          ← web3.py verification service
│
├── core/
│   ├── pagination.py        ← Standard API pagination
│   ├── permissions.py       ← Custom DRF permissions
│   ├── exceptions.py        ← Consistent error envelopes
│   ├── mixins.py            ← Shared view helpers
│   └── urls.py              ← Health check endpoint
│
├── manage.py
├── requirements.txt
├── docker-compose.yml       ← PostgreSQL + Redis
├── Procfile                 ← Railway/Heroku process config
└── .env.example             ← Environment variable template
```

---

## API Authentication Flow

JarFund uses **wallet-based authentication** (no username/password):

1. **Frontend** calls `GET /api/v1/auth/nonce/?wallet=0x...`
2. **Backend** returns a nonce string
3. **Frontend** asks MetaMask to sign: `"Sign in to JarFund: {nonce}"`
4. **Frontend** calls `POST /api/v1/auth/verify/` with `{ wallet, signature }`
5. **Backend** recovers the signer address, verifies it matches the wallet
6. **Backend** returns JWT `access` + `refresh` tokens
7. **Frontend** stores tokens and includes `Authorization: Bearer {access}` on all authenticated requests

---

## Next Steps

- **STEP 3**: Django Models (Jar, Donation, TransactionLog)
- **STEP 4**: REST API endpoints
- **STEP 5**: web3.py verification service
