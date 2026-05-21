import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .exceptions import (
    BlockchainError,
    InsufficientConfirmationsError,
    RPCConnectionError,
    RPCTimeoutError,
    TransactionNotFoundError,
    TransactionRevertedError,
    WrongContractError,
    ContractNotConfiguredError,
    ABINotFoundError,
)

logger = logging.getLogger(__name__)

MAX_VERIFICATION_ATTEMPTS = 20
STALE_THRESHOLD_HOURS     = 4

@shared_task(
    bind=True,
    name="apps.blockchain.tasks.verify_pending_donations",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=240,
    time_limit=300,
)
def verify_pending_donations(self):
    from apps.donations.models import Donation, TxStatus

    try:
        pending_qs = Donation.objects.filter(
            tx_status=TxStatus.PENDING,
            verification_attempts__lt=MAX_VERIFICATION_ATTEMPTS,
        ).values_list("tx_hash", flat=True)

        tx_hashes = list(pending_qs)
        count     = len(tx_hashes)

        if count == 0:
            logger.debug("verify_pending_donations: nothing pending")
            return {"dispatched": 0}

        logger.info(
            "verify_pending_donations: dispatching %d verification task(s)",
            count,
        )

        for tx_hash in tx_hashes:
            async_result = verify_single_transaction.apply_async(
                args=[tx_hash],
                queue='celery',
                countdown=0,
            )
            logger.info(
                "verify_pending_donations: queued tx=%s task_id=%s queue=celery",
                tx_hash[:14],
                async_result.id,
            )

        return {"dispatched": count, "tx_hashes": tx_hashes}

    except Exception as exc:
        logger.error("verify_pending_donations error: %s", exc, exc_info=True)
        raise self.retry(exc=exc)

@shared_task(
    bind=True,
    name="apps.blockchain.tasks.verify_single_transaction",
    max_retries=15,
    soft_time_limit=55,
    time_limit=60,
)
def verify_single_transaction(self, tx_hash: str):
    from apps.donations.models import Donation, TxStatus
    from .service import BlockchainService
    from .processor import ReceiptProcessor

    logger.info("verify_single_transaction: starting tx=%s (attempt %d)", tx_hash[:14], self.request.retries + 1)

    # Fetch donation
    try:
        donation = Donation.objects.select_related("jar").get(tx_hash=tx_hash)
    except Donation.DoesNotExist:
        logger.warning("verify_single_transaction: tx_hash not in DB — %s", tx_hash[:14])
        return {"status": "not_found", "tx_hash": tx_hash}

    if donation.tx_status != TxStatus.PENDING:
        logger.debug("Donation #%s already %s — skipping", donation.id, donation.tx_status)
        return {"status": "already_processed", "donation_id": donation.id}

    donation.increment_verification_attempt()

    try:
        svc       = BlockchainService()
        processor = ReceiptProcessor(svc)
    except (ContractNotConfiguredError, ABINotFoundError) as exc:
        # Config errors — log loudly but don't retry (won't fix itself)
        logger.error(
            "verify_single_transaction: config error for %s — %s",
            tx_hash[:14], exc,
        )
        return {"status": "config_error", "error": str(exc)}
    try:
        receipt = svc.get_receipt(tx_hash)
    except (RPCConnectionError, RPCTimeoutError) as exc:
        # RPC problems — retry with back-off
        delay = _backoff_delay(self.request.retries)
        logger.warning(
            "RPC error for %s (attempt %d) — retrying in %ds: %s",
            tx_hash[:14], self.request.retries + 1, delay, exc,
        )
        raise self.retry(exc=exc, countdown=delay)

    if receipt is None:
        delay = _backoff_delay(self.request.retries)
        logger.info(
            "Tx %s not yet mined (attempt %d) — retrying in %ds",
            tx_hash[:14], self.request.retries + 1, delay,
        )
        raise self.retry(
            exc=TransactionNotFoundError(f"Tx {tx_hash[:14]}… not yet mined"),
            countdown=delay,
        )

    try:
        result = processor.process_donation_receipt(donation, receipt)
        logger.info(
            "verify_single_transaction: %s → %s",
            tx_hash[:14], result.get("status"),
        )



        return result

    except InsufficientConfirmationsError as exc:

        delay = 20
        logger.info(
            "Tx %s: %d/%d confirmations — retrying in %ds",
            tx_hash[:14], exc.current, exc.required, delay,
        )
        raise self.retry(exc=exc, countdown=delay)

    except TransactionRevertedError as exc:
        # Terminal: tx reverted on-chain
        logger.warning("Tx %s reverted: %s", tx_hash[:14], exc)
        processor.process_donation_failure(donation, reason="reverted")
        return {"status": "failed_reverted", "tx_hash": tx_hash}

    except WrongContractError as exc:
        # Terminal: tx sent to wrong contract
        logger.warning("Tx %s wrong contract: %s", tx_hash[:14], exc)
        processor.process_donation_failure(donation, reason="wrong_contract")
        return {"status": "failed_wrong_contract", "tx_hash": tx_hash}

    except (RPCConnectionError, RPCTimeoutError) as exc:
        delay = _backoff_delay(self.request.retries)
        raise self.retry(exc=exc, countdown=delay)

    except Exception as exc:
        logger.error(
            "Unexpected error verifying %s: %s",
            tx_hash[:14], exc, exc_info=True,
        )
        delay = _backoff_delay(self.request.retries)
        raise self.retry(exc=exc, countdown=delay)


@shared_task(
    bind=True,
    name="apps.blockchain.tasks.verify_jar_creation",
    max_retries=10,
    soft_time_limit=55,
    time_limit=60,
)
def verify_jar_creation(self, jar_id: int):
    """
    Verify a createJar() transaction and mark the Jar as is_verified_on_chain=True.
    Spawned by JarViewSet.confirm() with a 10-second countdown.
    """
    from apps.jars.models import Jar
    from .service import BlockchainService
    from .processor import ReceiptProcessor

    try:
        jar = Jar.objects.get(pk=jar_id)
    except Jar.DoesNotExist:
        logger.error("verify_jar_creation: Jar #%s not found", jar_id)
        return {"status": "not_found", "jar_id": jar_id}

    if jar.is_verified_on_chain:
        return {"status": "already_verified", "jar_id": jar_id}

    if not jar.creation_tx_hash:
        logger.warning("verify_jar_creation: Jar #%s has no creation_tx_hash", jar_id)
        return {"status": "no_tx_hash", "jar_id": jar_id}

    try:
        svc       = BlockchainService()
        processor = ReceiptProcessor(svc)
        receipt   = svc.get_receipt(jar.creation_tx_hash)

        if receipt is None:
            delay = _backoff_delay(self.request.retries)
            logger.info("Jar #%s creation tx not yet mined — retrying in %ds", jar_id, delay)
            raise self.retry(
                exc=TransactionNotFoundError("Not yet mined"),
                countdown=delay,
            )

        result = processor.process_jar_creation_receipt(jar, receipt)
        logger.info("verify_jar_creation: Jar #%s → %s", jar_id, result.get("status"))
        return result

    except InsufficientConfirmationsError as exc:
        raise self.retry(exc=exc, countdown=20)

    except (RPCConnectionError, RPCTimeoutError) as exc:
        raise self.retry(exc=exc, countdown=_backoff_delay(self.request.retries))

    except (ContractNotConfiguredError, ABINotFoundError) as exc:
        logger.error("verify_jar_creation: config error — %s", exc)
        return {"status": "config_error", "error": str(exc)}

    except Exception as exc:
        logger.error(
            "verify_jar_creation Jar #%s unexpected error: %s",
            jar_id, exc, exc_info=True,
        )
        raise self.retry(exc=exc, countdown=_backoff_delay(self.request.retries))

@shared_task(
    bind=True,
    name="apps.blockchain.tasks.sync_jar_from_chain",
    max_retries=3,
    default_retry_delay=30,
)
def sync_jar_from_chain(self, jar_id: int):
    """
    Read the on-chain jar struct and reconcile it with the DB record.
    Useful for detecting discrepancies or after a manual withdrawal.
    """
    from apps.jars.models import Jar, JarStatus
    from .service import BlockchainService

    try:
        jar = Jar.objects.get(pk=jar_id)
    except Jar.DoesNotExist:
        return {"status": "not_found", "jar_id": jar_id}

    if not jar.chain_jar_id:
        return {"status": "no_chain_id", "jar_id": jar_id}

    try:
        svc         = BlockchainService()
        on_chain    = svc.get_on_chain_jar(jar.chain_jar_id)

        if not on_chain:
            logger.warning("sync_jar_from_chain: Jar #%s not found on-chain", jar_id)
            return {"status": "not_on_chain", "jar_id": jar_id}

        STATUS_MAP = {
            "active":    JarStatus.ACTIVE,
            "completed": JarStatus.COMPLETED,
            "expired":   JarStatus.EXPIRED,
            "withdrawn": JarStatus.WITHDRAWN,
        }

        updates = {}
        from decimal import Decimal

        new_raised = Decimal(str(on_chain["amount_raised"]))
        new_status = STATUS_MAP.get(on_chain["status"], jar.status)
        new_donors = on_chain["donor_count"]

        if abs(jar.amount_raised_matic - new_raised) > Decimal("0.000001"):
            updates["amount_raised_matic"] = new_raised

        if jar.status != new_status:
            updates["status"] = new_status

        if jar.donor_count != new_donors:
            updates["donor_count"] = new_donors

        if updates:
            updates["updated_at"] = timezone.now()
            Jar.objects.filter(pk=jar_id).update(**updates)
            logger.info(
                "sync_jar_from_chain: Jar #%s updated — %s",
                jar_id, list(updates.keys()),
            )
            return {"status": "updated", "jar_id": jar_id, "changes": list(updates.keys())}

        return {"status": "in_sync", "jar_id": jar_id}

    except (RPCConnectionError, RPCTimeoutError) as exc:
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error("sync_jar_from_chain Jar #%s error: %s", jar_id, exc, exc_info=True)
        raise self.retry(exc=exc)

@shared_task(
    name="apps.blockchain.tasks.sync_all_jars_from_chain",
    soft_time_limit=600,
    time_limit=660,
)
def sync_all_jars_from_chain():
    from apps.jars.models import Jar, JarStatus

    jars = Jar.objects.exclude(
        chain_jar_id__isnull=True
    ).exclude(
        status=JarStatus.WITHDRAWN
    ).values_list("id", flat=True)

    dispatched = 0
    for jar_id in jars:
        sync_jar_from_chain.apply_async(
            args=[jar_id],
            queue='celery',
            countdown=dispatched * 2,  # stagger by 2s each
        )
        dispatched += 1

    logger.info("sync_all_jars_from_chain: dispatched %d tasks", dispatched)
    return {"dispatched": dispatched}

@shared_task(
    name="apps.blockchain.tasks.report_stale_donations",
    soft_time_limit=60,
)
def report_stale_donations():
    from apps.donations.models import Donation, TxStatus

    threshold = timezone.now() - timedelta(hours=STALE_THRESHOLD_HOURS)

    stale = Donation.objects.filter(
        tx_status=TxStatus.PENDING,
        created_at__lte=threshold,
    ).values("id", "tx_hash", "amount_matic", "verification_attempts", "created_at")

    stale_list = list(stale)
    count = len(stale_list)

    if count:
        logger.warning(
            "⚠️  %d stale donation(s) pending for >%dh: %s",
            count,
            STALE_THRESHOLD_HOURS,
            [d["tx_hash"][:12] for d in stale_list],
        )
    else:
        logger.info("report_stale_donations: no stale donations found")

    return {"stale_count": count, "donations": stale_list}


def _backoff_delay(retry_count: int) -> int:
    if retry_count < 4:
        return 15
    if retry_count < 6:
        return 30
    if retry_count < 10:
        return 60
    return 120
