# JarFund REST API — Complete Reference
**Base URL:** `https://api.jarfund.io/api/v1/`  
**Dev URL:** `http://localhost:8000/api/v1/`  
**Interactive docs:** `/api/docs/` (Swagger) · `/api/redoc/` (ReDoc)

---

## Authentication

All write endpoints require a JWT Bearer token:
```
Authorization: Bearer <access_token>
```

### Wallet Auth Flow

| # | Step | Request | Response |
|---|------|---------|----------|
| 1 | Get nonce | `GET /auth/nonce/?wallet=0x…` | `{ nonce, message }` |
| 2 | Sign in MetaMask | User signs `"Sign in to JarFund: {nonce}"` | — |
| 3 | Submit signature | `POST /auth/verify/` `{ wallet, signature }` | `{ access, refresh, user }` |
| 4 | Refresh token | `POST /auth/refresh/` `{ refresh }` | `{ access }` |
| 5 | Logout | `POST /auth/logout/` `{ refresh }` | `{ success: true }` |

---

## Endpoints

### 🔐 Auth  `/auth/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/auth/nonce/` | — | Get signing challenge for wallet |
| POST | `/auth/verify/` | — | Verify signature → JWT tokens |
| POST | `/auth/refresh/` | — | Refresh access token |
| POST | `/auth/logout/` | ✅ | Blacklist refresh token |
| GET | `/auth/profile/` | ✅ | Get own full profile |
| PATCH | `/auth/profile/` | ✅ | Update username / bio / avatar_url |

---

### 🫙 Jars  `/jars/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/jars/` | — | List / explore jars (paginated, filterable) |
| POST | `/jars/` | ✅ | Create a new jar |
| GET | `/jars/my/` | ✅ | Jars created by current user |
| GET | `/jars/{id}/` | — | Jar detail with embedded donations |
| PATCH | `/jars/{id}/` | ✅ creator | Update jar metadata |
| POST | `/jars/{id}/confirm/` | ✅ creator | Confirm on-chain creation |
| POST | `/jars/{id}/withdraw/` | ✅ creator | Record withdrawal transaction |
| GET | `/jars/{id}/donations/` | — | Paginated donations for jar |
| GET | `/jars/{id}/stats/` | — | Donation statistics |

#### Query Params for `GET /jars/`
```
?status=active          active | completed | expired | withdrawn
?category=education     education | technology | humanitarian | …
?search=community       full-text search on title, description
?creator_wallet=0x…     filter by creator
?is_verified=true       only on-chain verified jars
?min_target=10          target_amount_matic >= 10
?max_target=1000        target_amount_matic <= 1000
?ordering=-created_at   sort field (prefix - for desc)
?page=2&page_size=12    pagination
?include_all=1          include expired/withdrawn (hidden by default)
```

#### POST `/jars/` — Create Jar
```json
{
    "title":               "My Fundraiser",
    "description":         "Full description here",
    "category":            "education",
    "cover_emoji":         "🎓",
    "target_amount_matic": "100.0",
    "deadline":            "2026-06-01T12:00:00Z",
    "creation_tx_hash":    "0x…"  // optional, set after tx submitted
}
```

#### POST `/jars/{id}/confirm/` — Confirm On-Chain
```json
{
    "chain_jar_id":     1,
    "creation_tx_hash": "0x…"
}
```

#### POST `/jars/{id}/withdraw/` — Record Withdrawal
```json
{
    "withdrawal_tx_hash": "0x…"
}
```

---

### 💸 Donations  `/donations/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/donations/` | ✅ | Submit a donation transaction |
| GET | `/donations/` | — | List donations (filterable) |
| GET | `/donations/{id}/` | — | Single donation detail |
| GET | `/donations/my/` | ✅ | Current user's donations + stats |
| GET | `/donations/leaderboard/` | — | Top donors |

#### POST `/donations/` — Submit Donation
```json
{
    "jar_id":       1,
    "donor_wallet": "0x…",
    "amount_matic": "0.5",
    "amount_wei":   "500000000000000000",
    "tx_hash":      "0x…",
    "message":      "Good luck! 🚀",
    "is_anonymous": false
}
```
> ⚠️ `donor_wallet` must match your authenticated wallet. Tx is stored as `pending`; Celery verifies async.

#### Query Params for `GET /donations/`
```
?jar_id=1           filter by jar
?donor_wallet=0x…   filter by donor
?tx_status=confirmed pending | confirmed | failed
?is_verified=true   only verified
```

---

### ⛓️ Blockchain  `/blockchain/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/blockchain/verify/` | — | Trigger async tx verification |
| GET | `/blockchain/tx/{tx_hash}/` | — | Get tx verification status |
| GET | `/blockchain/events/` | — | Contract event log |
| GET | `/blockchain/events/{id}/` | — | Single event detail |
| GET | `/blockchain/stats/` | — | Platform aggregate stats (cached 60s) |

#### GET `/blockchain/tx/{tx_hash}/` Response
```json
{
    "success": true,
    "data": {
        "tx_hash":       "0x…",
        "status":        "confirmed",
        "is_verified":   true,
        "block_number":  12345678,
        "confirmations": 5,
        "gas_used":      65000,
        "gas_price_gwei": "30.5",
        "verified_at":   "2026-03-01T10:00:00Z",
        "explorer_url":  "https://amoy.polygonscan.com/tx/0x…",
        "source":        "db"
    }
}
```

#### GET `/blockchain/stats/` Response
```json
{
    "success": true,
    "data": {
        "total_jars":          42,
        "active_jars":         31,
        "completed_jars":      8,
        "total_raised_matic":  "15420.500000",
        "total_donors":        312,
        "total_donations":     589,
        "verified_donations":  581,
        "donations_last_24h":  12,
        "raised_last_24h":     "340.000000"
    },
    "cached": true
}
```

---

## Standard Response Envelope

### Success
```json
{
    "success": true,
    "data":    { ... },
    "message": "Optional human-readable message"
}
```

### Paginated List
```json
{
    "count":       42,
    "total_pages": 4,
    "next":        "http://…/jars/?page=3",
    "previous":    "http://…/jars/?page=1",
    "results":     [ ... ]
}
```

### Error
```json
{
    "success": false,
    "error": {
        "code":    "validation_error",
        "message": "One or more fields failed validation.",
        "details": {
            "title": ["This field is required."]
        }
    }
}
```

### Error Codes
| Code | HTTP | Meaning |
|------|------|---------|
| `validation_error` | 400 | Field-level validation failed |
| `wallet_mismatch` | 403 | donor_wallet ≠ authenticated wallet |
| `not_found` | 404 | Resource doesn't exist |
| `forbidden` | 403 | No permission for this action |
| `already_confirmed` | 409 | Jar already confirmed on-chain |
| `already_withdrawn` | 409 | Jar already withdrawn |
| `withdrawal_conditions_not_met` | 400 | Deadline not reached and target not met |
| `duplicate_chain_id` | 409 | chain_jar_id already in use |
| `invalid_token` | 401 | JWT token invalid or expired |
| `missing_token` | 400 | Required token not provided |

---

## Health Check
```
GET /health/
→ 200 { "status": "ok", "checks": { "db": "ok", "cache": "ok" } }
→ 503 { "status": "degraded", "checks": { "db": "error", ... } }
```
