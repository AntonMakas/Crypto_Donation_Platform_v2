"""
ReceiptProcessor — bridges raw web3.py receipts to Django model updates.

Separates the blockchain parsing logic from the Celery task orchestration.
Each process_*() method is atomic: it reads a receipt and writes the
minimal set of model changes needed, then returns a result dict for logging.

Usage (in Celery tasks):
    processor = ReceiptProcessor(service)
    result    = processor.process_donation_receipt(donation, receipt)
"""
import logging
from decimal import Decimal
from datetime import datetime, timezone

from django.db import transaction
from django.utils import timezone as dj_timezone

from .exceptions import (
    InsufficientConfirmationsError,
    TransactionRevertedError,
    WrongContractError,
    InvalidReceiptError,
)

logger = logging.getLogger(__name__)


class ReceiptProcessor:
    """
    Stateless processor. Pass a BlockchainService instance at construction.
    All methods are safe to call multiple times (idempotent).
    """

    def __init__(self, service):
        self.service = service

    # ─────────────────────────────────────────────────────────────
    #  DONATION RECEIPT
    # ─────────────────────────────────────────────────────────────

    @transaction.atomic
    def process_donation_receipt(self, donation, receipt: dict) -> dict:
        """
        Parse a donate() transaction receipt and update the Donation record.

        Steps:
          1. Validate receipt (status, contract, confirmations)
          2. Extract gas info and block timestamp
          3. Decode DonationReceived event to cross-check amount
          4. Mark donation as CONFIRMED
          5. Create/update TransactionLog and ContractEvent records
          6. Trigger jar sync (amount_raised_matic + status)

        Returns a result dict describing what changed.

        Raises:
          TransactionRevertedError         — tx failed on-chain
          InsufficientConfirmationsError   — need more blocks
          WrongContractError               — tx to wrong address
        """
        from apps.donations.models import TxStatus

        # Already confirmed? Nothing to do.
        if donation.tx_status == TxStatus.CONFIRMED:
            return {"status": "already_confirmed", "donation_id": donation.id}

        # ── 1. Validate ──────────────────────────────────────────
        self.service.validate_receipt(receipt, donation.tx_hash)

        block_number = receipt["blockNumber"]
        gas_used     = receipt.get("gasUsed", 0)
        confs        = self.service.get_confirmations(block_number)

        # ── 2. Block timestamp ───────────────────────────────────
        block_ts = self.service.get_block_timestamp(block_number)

        # ── 3. Gas price ─────────────────────────────────────────
        try:
            tx_data = self.service.get_transaction(donation.tx_hash)
        except Exception:
            tx_data = None
        gas_price_gwei = self.service.get_gas_price_gwei(receipt, tx_data)

        # ── 4. Cross-check amount via event ──────────────────────
        event_args = self.service.decode_donation_event(receipt)
        if event_args:
            on_chain_amount = self.service.wei_to_matic(event_args.get("amount", 0))
            if abs(on_chain_amount - donation.amount_matic) > Decimal("0.000001"):
                logger.warning(
                    "Donation #%s: amount mismatch — DB=%s, chain=%s MATIC. "
                    "Updating DB to match chain.",
                    donation.id,
                    donation.amount_matic,
                    on_chain_amount,
                )
                donation.amount_matic = on_chain_amount
                donation.amount_wei   = str(event_args.get("amount", 0))

        # ── 5. Mark confirmed ────────────────────────────────────
        donation.mark_confirmed(
            block_number=block_number,
            block_timestamp=block_ts,
            gas_used=gas_used,
            gas_price_gwei=gas_price_gwei,
            confirmations=confs,
        )

        # ── 6. Create / update TransactionLog ────────────────────
        tx_log = self._upsert_transaction_log(
            tx_hash=donation.tx_hash,
            tx_type="donate",
            from_wallet=donation.donor_wallet,
            receipt=receipt,
            value_matic=donation.amount_matic,
            gas_price_gwei=gas_price_gwei,
            block_ts=block_ts,
            jar_id_ref=donation.jar_id,
            donation_id_ref=donation.id,
        )

        # ── 7. Create ContractEvent records ──────────────────────
        decoded_events = self.service.decode_events(receipt)
        self._store_events(decoded_events, tx_log)

        # ── 8. Sync jar status ───────────────────────────────────
        donation.jar.sync_status()

        # ── 9. Sync jar amount from chain ────────────────────────
        if donation.jar.chain_jar_id:
            try:
                on_chain_jar = self.service.get_on_chain_jar(donation.jar.chain_jar_id)
                if on_chain_jar:
                    donation.jar.amount_raised_matic = Decimal(str(on_chain_jar["amount_raised"]))
                    donation.jar.donor_count = on_chain_jar["donor_count"]
                    donation.jar.save(update_fields=["amount_raised_matic", "donor_count", "updated_at"])
                    logger.info(
                        "Jar #%s synced from chain: amount_raised=%s MATIC",
                        donation.jar.id,
                        donation.jar.amount_raised_matic,
                    )
            except Exception as exc:
                logger.warning("Failed to sync jar #%s from chain: %s", donation.jar.id, exc)

        logger.info(
            "✅ Donation #%s confirmed: %s MATIC, block #%s, %d confs",
            donation.id, donation.amount_matic, block_number, confs,
        )

        return {
            "status":        "confirmed",
            "donation_id":   donation.id,
            "block_number":  block_number,
            "confirmations": confs,
            "amount_matic":  str(donation.amount_matic),
        }

    @transaction.atomic
    def process_donation_failure(self, donation, reason: str) -> dict:
        """
        Mark a donation as failed and create a TransactionLog entry.
        Called when a receipt has status=0 or another terminal error.
        """
        from apps.donations.models import TxStatus

        if donation.tx_status != TxStatus.PENDING:
            return {"status": "no_change", "donation_id": donation.id}

        donation.mark_failed()

        logger.warning(
            "❌ Donation #%s failed: tx=%s reason=%s",
            donation.id, donation.tx_hash[:12], reason,
        )
        return {
            "status":      "failed",
            "donation_id": donation.id,
            "reason":      reason,
        }

    # ─────────────────────────────────────────────────────────────
    #  JAR CREATION RECEIPT
    # ─────────────────────────────────────────────────────────────

    @transaction.atomic
    def process_jar_creation_receipt(self, jar, receipt: dict) -> dict:
        """
        Validate a createJar() receipt and mark the jar as verified on-chain.
        Extracts the on-chain jarId from the JarCreated event.
        """
        if jar.is_verified_on_chain:
            return {"status": "already_verified", "jar_id": jar.id}

        # Validate (revert, contract address, confirmations)
        self.service.validate_receipt(receipt, jar.creation_tx_hash)

        block_number = receipt["blockNumber"]
        block_ts     = self.service.get_block_timestamp(block_number)

        # Extract chain_jar_id from JarCreated event
        event_args = self.service.decode_jar_created_event(receipt)
        chain_jar_id = None
        if event_args:
            chain_jar_id = event_args.get("jarId")
            logger.debug(
                "JarCreated event: jarId=%s, creator=%s",
                chain_jar_id,
                event_args.get("creator", ""),
            )

        # Update jar
        update_fields = ["is_verified_on_chain", "updated_at"]
        jar.is_verified_on_chain = True

        if chain_jar_id and not jar.chain_jar_id:
            jar.chain_jar_id = chain_jar_id
            update_fields.append("chain_jar_id")

        jar.save(update_fields=update_fields)

        # TransactionLog
        gas_price_gwei = self.service.get_gas_price_gwei(receipt)
        tx_log = self._upsert_transaction_log(
            tx_hash=jar.creation_tx_hash,
            tx_type="create_jar",
            from_wallet=jar.creator_wallet,
            receipt=receipt,
            value_matic=Decimal("0"),
            gas_price_gwei=gas_price_gwei,
            block_ts=block_ts,
            jar_id_ref=jar.id,
        )

        decoded_events = self.service.decode_events(receipt)
        self._store_events(decoded_events, tx_log)

        logger.info(
            "✅ Jar #%s verified on-chain (chain_jar_id=%s, block #%s)",
            jar.id, chain_jar_id, block_number,
        )

        return {
            "status":       "verified",
            "jar_id":       jar.id,
            "chain_jar_id": chain_jar_id,
            "block_number": block_number,
        }

    # ─────────────────────────────────────────────────────────────
    #  PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────

    def _upsert_transaction_log(
        self,
        tx_hash: str,
        tx_type: str,
        from_wallet: str,
        receipt: dict,
        value_matic: Decimal,
        gas_price_gwei: Decimal,
        block_ts: datetime | None,
        jar_id_ref: int | None = None,
        donation_id_ref: int | None = None,
    ):
        """
        Create or update a TransactionLog record for the given tx_hash.
        Uses update_or_create so it's safe to call multiple times.
        """
        from apps.blockchain.models import TransactionLog, TxLogStatus
        from django.conf import settings

        block_number = receipt.get("blockNumber")
        block_hash   = receipt.get("blockHash")
        if hasattr(block_hash, "hex"):
            block_hash = block_hash.hex()
        block_hash = block_hash or ""

        confs = self.service.get_confirmations(block_number) if block_number else 0

        # Safely sanitise raw receipt for JSON storage
        safe_receipt = _make_json_safe(dict(receipt))

        tx_log, created = TransactionLog.objects.update_or_create(
            tx_hash=tx_hash,
            defaults={
                "tx_type":         tx_type,
                "from_wallet":     from_wallet,
                "to_wallet":       self.service._contract_addr,
                "chain_id":        self.service._chain_id,
                "block_number":    block_number,
                "block_hash":      block_hash,
                "block_timestamp": block_ts,
                "value_matic":     value_matic,
                "value_wei":       str(self.service.matic_to_wei(value_matic)),
                "gas_used":        receipt.get("gasUsed"),
                "gas_price_gwei":  gas_price_gwei,
                "status":          TxLogStatus.CONFIRMED,
                "confirmations":   confs,
                "jar_id_ref":      jar_id_ref,
                "donation_id_ref": donation_id_ref,
                "raw_receipt":     safe_receipt,
                "confirmed_at":    dj_timezone.now(),
            },
        )
        return tx_log

    def _store_events(self, decoded_events: list[dict], tx_log) -> None:
        """
        Persist decoded contract events as ContractEvent rows.
        Uses get_or_create on (tx_hash, log_index) for idempotency.
        """
        from apps.blockchain.models import ContractEvent

        for ev in decoded_events:
            args          = ev.get("args", {})
            chain_jar_id  = args.get("jarId") or args.get("jarId") or None
            emitter_wallet = (
                args.get("creator") or args.get("donor") or
                args.get("collector") or ""
            )

            ContractEvent.objects.get_or_create(
                tx_hash=ev["tx_hash"] or (tx_log.tx_hash if tx_log else ""),
                log_index=ev.get("log_index", 0),
                defaults={
                    "tx_log":         tx_log,
                    "event_type":     ev["event"],
                    "block_number":   ev.get("block_number") or (tx_log.block_number if tx_log else 0),
                    "event_data":     _make_json_safe(args),
                    "chain_jar_id":   chain_jar_id,
                    "emitter_wallet": emitter_wallet,
                },
            )


# ─────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────

def _make_json_safe(data: Any) -> Any:
    """
    Recursively convert web3.py types (HexBytes, AttributeDict, etc.)
    to JSON-serialisable Python primitives.
    """
    if isinstance(data, dict):
        return {k: _make_json_safe(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [_make_json_safe(i) for i in data]
    if hasattr(data, "hex"):          # HexBytes
        return data.hex()
    if isinstance(data, bytes):
        return data.hex()
    if isinstance(data, Decimal):
        return str(data)
    return data


# Type alias for the Any import
from typing import Any
