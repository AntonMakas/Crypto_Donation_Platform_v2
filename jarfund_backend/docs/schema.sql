-- ════════════════════════════════════════════════════════════════
--  JarFund — PostgreSQL Database Schema
--  Generated for documentation purposes.
--  Use Django migrations (python manage.py migrate) — DO NOT run this directly.
-- ════════════════════════════════════════════════════════════════


-- ── USERS ──────────────────────────────────────────────────────
CREATE TABLE users_user (
    id               BIGSERIAL PRIMARY KEY,
    password         VARCHAR(128)    NOT NULL,
    last_login       TIMESTAMPTZ,
    is_superuser     BOOLEAN         NOT NULL DEFAULT FALSE,
    first_name       VARCHAR(150)    NOT NULL DEFAULT '',
    last_name        VARCHAR(150)    NOT NULL DEFAULT '',
    email            VARCHAR(254)    NOT NULL DEFAULT '',
    is_staff         BOOLEAN         NOT NULL DEFAULT FALSE,
    is_active        BOOLEAN         NOT NULL DEFAULT TRUE,
    date_joined      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Wallet auth
    wallet_address   VARCHAR(42)     NOT NULL UNIQUE,
    nonce            VARCHAR(64)     NOT NULL,
    is_verified      BOOLEAN         NOT NULL DEFAULT FALSE,

    -- Profile
    username         VARCHAR(80)     NOT NULL DEFAULT '',
    bio              TEXT            NOT NULL DEFAULT '',
    avatar_url       VARCHAR(200)    NOT NULL DEFAULT '',

    -- Timestamps
    created_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ     NOT NULL,
    last_login_at    TIMESTAMPTZ
);

CREATE INDEX idx_user_wallet ON users_user (wallet_address);


-- ── JARS ───────────────────────────────────────────────────────
CREATE TABLE jars_jar (
    id                   BIGSERIAL PRIMARY KEY,

    -- On-chain reference
    chain_jar_id         BIGINT          UNIQUE,          -- uint256 from contract
    creation_tx_hash     VARCHAR(66)     NOT NULL DEFAULT '',
    is_verified_on_chain BOOLEAN         NOT NULL DEFAULT FALSE,
    withdrawal_tx_hash   VARCHAR(66)     NOT NULL DEFAULT '',
    withdrawn_at         TIMESTAMPTZ,

    -- Creator (FK + denormalized)
    creator_id           BIGINT          NOT NULL REFERENCES users_user(id) ON DELETE RESTRICT,
    creator_wallet       VARCHAR(42)     NOT NULL,

    -- Campaign content
    title                VARCHAR(120)    NOT NULL,
    description          TEXT            NOT NULL,
    category             VARCHAR(20)     NOT NULL DEFAULT 'other',
    cover_emoji          VARCHAR(8)      NOT NULL DEFAULT '🫙',
    cover_image_url      VARCHAR(200)    NOT NULL DEFAULT '',

    -- Financials
    target_amount_matic  NUMERIC(20,6)   NOT NULL CHECK (target_amount_matic >= 0.01),
    amount_raised_matic  NUMERIC(20,6)   NOT NULL DEFAULT 0 CHECK (amount_raised_matic >= 0),

    -- Timeline
    deadline             TIMESTAMPTZ     NOT NULL,

    -- State
    status               VARCHAR(12)     NOT NULL DEFAULT 'active',
    donor_count          INTEGER         NOT NULL DEFAULT 0,

    -- Timestamps
    created_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ     NOT NULL
);

CREATE INDEX idx_jar_status_deadline    ON jars_jar (status, deadline);
CREATE INDEX idx_jar_creator_status     ON jars_jar (creator_wallet, status);
CREATE INDEX idx_jar_category_status    ON jars_jar (category, status);
CREATE INDEX idx_jar_verified           ON jars_jar (is_verified_on_chain);
CREATE INDEX idx_jar_chain_id           ON jars_jar (chain_jar_id);
CREATE INDEX idx_jar_created_at         ON jars_jar (created_at DESC);


-- ── DONATIONS ──────────────────────────────────────────────────
CREATE TABLE donations_donation (
    id                    BIGSERIAL PRIMARY KEY,

    -- Relations
    jar_id                BIGINT          NOT NULL REFERENCES jars_jar(id) ON DELETE RESTRICT,
    donor_id              BIGINT          REFERENCES users_user(id) ON DELETE SET NULL,

    -- Donor
    donor_wallet          VARCHAR(42)     NOT NULL,

    -- Amount
    amount_matic          NUMERIC(20,6)   NOT NULL CHECK (amount_matic >= 0.001),
    amount_wei            VARCHAR(78)     NOT NULL DEFAULT '0',

    -- Transaction
    tx_hash               VARCHAR(66)     NOT NULL UNIQUE,
    tx_status             VARCHAR(10)     NOT NULL DEFAULT 'pending',
    block_number          BIGINT,
    block_timestamp       TIMESTAMPTZ,
    gas_used              BIGINT,
    gas_price_gwei        NUMERIC(20,9),
    confirmations         INTEGER         NOT NULL DEFAULT 0,

    -- Verification
    is_verified           BOOLEAN         NOT NULL DEFAULT FALSE,
    verified_at           TIMESTAMPTZ,
    verification_attempts SMALLINT        NOT NULL DEFAULT 0,
    last_verified_at      TIMESTAMPTZ,

    -- Optional
    message               VARCHAR(280)    NOT NULL DEFAULT '',
    is_anonymous          BOOLEAN         NOT NULL DEFAULT FALSE,

    -- Timestamps
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     NOT NULL
);

CREATE INDEX idx_donation_status_verified      ON donations_donation (tx_status, is_verified);
CREATE INDEX idx_donation_donor_status         ON donations_donation (donor_wallet, tx_status);
CREATE INDEX idx_donation_jar_status           ON donations_donation (jar_id, tx_status);
CREATE INDEX idx_donation_pending_attempts     ON donations_donation (tx_status, verification_attempts)
    WHERE tx_status = 'pending';   -- Partial index — only pending rows
CREATE INDEX idx_donation_tx_hash              ON donations_donation (tx_hash);
CREATE INDEX idx_donation_created_at           ON donations_donation (created_at DESC);


-- ── TRANSACTION LOGS ───────────────────────────────────────────
CREATE TABLE blockchain_transactionlog (
    id               BIGSERIAL PRIMARY KEY,
    tx_hash          VARCHAR(66)     NOT NULL UNIQUE,
    tx_type          VARCHAR(12)     NOT NULL,

    from_wallet      VARCHAR(42)     NOT NULL,
    to_wallet        VARCHAR(42)     NOT NULL DEFAULT '',

    chain_id         INTEGER         NOT NULL DEFAULT 80002,
    block_number     BIGINT,
    block_hash       VARCHAR(66)     NOT NULL DEFAULT '',
    block_timestamp  TIMESTAMPTZ,

    value_wei        VARCHAR(78)     NOT NULL DEFAULT '0',
    value_matic      NUMERIC(20,6)   NOT NULL DEFAULT 0,

    gas_used         BIGINT,
    gas_limit        BIGINT,
    gas_price_wei    VARCHAR(30)     NOT NULL DEFAULT '',
    gas_price_gwei   NUMERIC(20,9),

    status           VARCHAR(10)     NOT NULL DEFAULT 'pending',
    confirmations    INTEGER         NOT NULL DEFAULT 0,

    -- Context refs
    jar_id_ref       BIGINT,
    donation_id_ref  BIGINT,
    raw_receipt      JSONB,

    -- Timestamps
    created_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    confirmed_at     TIMESTAMPTZ
);

CREATE INDEX idx_txlog_status_type  ON blockchain_transactionlog (status, tx_type);
CREATE INDEX idx_txlog_wallet_type  ON blockchain_transactionlog (from_wallet, tx_type);
CREATE INDEX idx_txlog_block        ON blockchain_transactionlog (block_number);
CREATE INDEX idx_txlog_hash         ON blockchain_transactionlog (tx_hash);


-- ── CONTRACT EVENTS ────────────────────────────────────────────
CREATE TABLE blockchain_contractevent (
    id              BIGSERIAL PRIMARY KEY,
    tx_log_id       BIGINT          REFERENCES blockchain_transactionlog(id) ON DELETE CASCADE,
    tx_hash         VARCHAR(66)     NOT NULL,
    event_type      VARCHAR(30)     NOT NULL,
    log_index       INTEGER         NOT NULL DEFAULT 0,
    block_number    BIGINT          NOT NULL,
    block_timestamp TIMESTAMPTZ,
    event_data      JSONB           NOT NULL DEFAULT '{}',
    chain_jar_id    BIGINT,
    emitter_wallet  VARCHAR(42)     NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE (tx_hash, log_index)
);

CREATE INDEX idx_event_type_block  ON blockchain_contractevent (event_type, block_number);
CREATE INDEX idx_event_jar_type    ON blockchain_contractevent (chain_jar_id, event_type);
CREATE INDEX idx_event_wallet      ON blockchain_contractevent (emitter_wallet);
CREATE INDEX idx_event_hash        ON blockchain_contractevent (tx_hash);


-- ════════════════════════════════════════════════════════════════
--  ENTITY RELATIONSHIP SUMMARY
--
--  users_user
--      │
--      ├─(1:N)─► jars_jar              (creator)
--      │             │
--      │             └─(1:N)─► donations_donation
--      │
--      └─(1:N)─► donations_donation    (donor)
--
--  donations_donation
--      └─(N:1)─► blockchain_transactionlog  (tx_hash)
--                    │
--                    └─(1:N)─► blockchain_contractevent
--
-- ════════════════════════════════════════════════════════════════
