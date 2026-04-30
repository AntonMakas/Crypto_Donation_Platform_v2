"""
Tests for the blockchain verification service layer.

Run:
    pytest tests/test_blockchain.py -v
    pytest tests/test_blockchain.py -v -k "not integration"
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# ─────────────────────────────────────────────────────────────────
#  FIXTURES
# ─────────────────────────────────────────────────────────────────

MOCK_TX_HASH    = "0x" + "a" * 64
MOCK_WALLET     = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
MOCK_CONTRACT   = "0x2b5AD5c4795c026514f8317c7a215E218DcCD6cF"

# A minimal valid receipt — mirrors what web3.py returns
MOCK_RECEIPT = {
    "status":              1,
    "transactionHash":     bytes.fromhex(MOCK_TX_HASH[2:]),
    "blockNumber":         12345000,
    "blockHash":           bytes.fromhex("b" * 64),
    "gasUsed":             65000,
    "effectiveGasPrice":   30_000_000_000,     # 30 gwei in wei
    "to":                  MOCK_CONTRACT,
    "from":                MOCK_WALLET,
    "logs":                [],
}

# A reverted receipt
MOCK_REVERTED_RECEIPT = {**MOCK_RECEIPT, "status": 0}


@pytest.fixture
def mock_settings(settings):
    settings.BLOCKCHAIN = {
        "POLYGON_AMOY_RPC_URL": "https://mock-rpc.example.com",
        "CONTRACT_ADDRESS":     MOCK_CONTRACT,
        "CHAIN_ID":             80002,
        "REQUIRED_CONFIRMATIONS": 3,
        "EXPLORER_URL":         "https://amoy.polygonscan.com",
    }
    return settings


@pytest.fixture
def mock_w3():
    """Mock Web3 instance that appears connected on chain 80002."""
    w3 = MagicMock()
    w3.is_connected.return_value = True
    w3.eth.chain_id = 80002
    w3.eth.block_number = 12345010   # 10 blocks ahead of receipt
    return w3


@pytest.fixture
def service(mock_settings, mock_w3):
    """BlockchainService with a mocked Web3 provider."""
    from apps.blockchain.service import BlockchainService

    with patch("apps.blockchain.service.Web3") as MockWeb3, \
         patch("apps.blockchain.service.ExtraDataToPOAMiddleware"):
        instance = BlockchainService.__new__(BlockchainService)
        instance.__init__()
        instance._w3 = mock_w3
        instance._w3.eth.chain_id = 80002
        yield instance


@pytest.fixture
def pending_donation(db, active_jar, donor_user):
    from apps.donations.models import Donation, TxStatus
    return Donation.objects.create(
        jar=active_jar,
        donor=donor_user,
        donor_wallet=MOCK_WALLET,
        amount_matic=Decimal("1.0"),
        amount_wei="1000000000000000000",
        tx_hash=MOCK_TX_HASH,
        tx_status=TxStatus.PENDING,
    )


@pytest.fixture
def creator_user(db):
    return User.objects.create(wallet_address=MOCK_CONTRACT, is_verified=True)


@pytest.fixture
def donor_user(db):
    return User.objects.create(wallet_address=MOCK_WALLET, is_verified=True)


@pytest.fixture
def active_jar(db, creator_user):
    from apps.jars.models import Jar, JarStatus
    return Jar.objects.create(
        creator=creator_user,
        creator_wallet=MOCK_CONTRACT,
        title="Test Jar",
        description="desc",
        target_amount_matic=Decimal("10.0"),
        deadline=timezone.now() + timezone.timedelta(days=7),
        status=JarStatus.ACTIVE,
    )


# ─────────────────────────────────────────────────────────────────
#  SERVICE UNIT TESTS
# ─────────────────────────────────────────────────────────────────

class TestBlockchainServiceConnection:

    def test_is_connected_returns_true_when_w3_connected(self, service, mock_w3):
        mock_w3.is_connected.return_value = True
        assert service.is_connected() is True

    def test_is_connected_returns_false_on_exception(self, service, mock_w3):
        mock_w3.is_connected.side_effect = Exception("network error")
        assert service.is_connected() is False


class TestReceiptFetching:

    def test_get_receipt_returns_dict(self, service, mock_w3):
        mock_w3.eth.get_transaction_receipt.return_value = MagicMock(**MOCK_RECEIPT)
        receipt = service.get_receipt(MOCK_TX_HASH)
        assert receipt is not None

    def test_get_receipt_returns_none_when_not_found(self, service, mock_w3):
        from web3.exceptions import TransactionNotFound
        mock_w3.eth.get_transaction_receipt.side_effect = TransactionNotFound()
        receipt = service.get_receipt(MOCK_TX_HASH)
        assert receipt is None

    def test_get_receipt_raises_on_connection_error(self, service, mock_w3):
        from apps.blockchain.exceptions import RPCConnectionError
        mock_w3.eth.get_transaction_receipt.side_effect = ConnectionError("refused")
        with pytest.raises(RPCConnectionError):
            service.get_receipt(MOCK_TX_HASH)


class TestReceiptValidation:

    def test_valid_receipt_passes(self, service, mock_w3):
        mock_w3.eth.block_number = 12345010
        # Should not raise
        service.validate_receipt(MOCK_RECEIPT, MOCK_TX_HASH)

    def test_reverted_receipt_raises(self, service, mock_w3):
        from apps.blockchain.exceptions import TransactionRevertedError
        mock_w3.eth.block_number = 12345010
        with pytest.raises(TransactionRevertedError):
            service.validate_receipt(MOCK_REVERTED_RECEIPT, MOCK_TX_HASH)

    def test_insufficient_confirmations_raises(self, service, mock_w3):
        from apps.blockchain.exceptions import InsufficientConfirmationsError
        # Only 2 confirmations total — need 3
        mock_w3.eth.block_number = 12345001
        with pytest.raises(InsufficientConfirmationsError) as exc_info:
            service.validate_receipt(MOCK_RECEIPT, MOCK_TX_HASH)
        assert exc_info.value.current == 2
        assert exc_info.value.required == 3

    def test_wrong_contract_raises(self, service, mock_w3):
        from apps.blockchain.exceptions import WrongContractError
        mock_w3.eth.block_number = 12345010
        bad_receipt = {**MOCK_RECEIPT, "to": "0x" + "f" * 40}
        with pytest.raises(WrongContractError):
            service.validate_receipt(bad_receipt, MOCK_TX_HASH)

    def test_empty_receipt_raises_invalid(self, service):
        from apps.blockchain.exceptions import InvalidReceiptError
        with pytest.raises(InvalidReceiptError):
            service.validate_receipt({}, MOCK_TX_HASH)


class TestConfirmationHelpers:

    def test_get_confirmations_calculates_correctly(self, service, mock_w3):
        mock_w3.eth.block_number = 12345010
        assert service.get_confirmations(12345000) == 11

    def test_get_confirmations_never_negative(self, service, mock_w3):
        mock_w3.eth.block_number = 100
        assert service.get_confirmations(200) == 0


class TestWeiMaticConversion:

    def test_wei_to_matic(self, service):
        assert service.wei_to_matic(1_000_000_000_000_000_000) == Decimal("1")
        assert service.wei_to_matic("500000000000000000") == Decimal("0.5")

    def test_matic_to_wei(self, service):
        assert service.matic_to_wei(Decimal("1")) == 1_000_000_000_000_000_000
        assert service.matic_to_wei("0.001") == 1_000_000_000_000_000


class TestGasHelpers:

    def test_get_gas_price_gwei_from_effective(self, service):
        receipt = {"effectiveGasPrice": 30_000_000_000}  # 30 gwei
        gwei = service.get_gas_price_gwei(receipt)
        assert gwei == Decimal("30")

    def test_get_gas_price_gwei_fallback_to_tx(self, service):
        receipt = {}
        tx_data = {"gasPrice": 25_000_000_000}  # 25 gwei
        gwei = service.get_gas_price_gwei(receipt, tx_data)
        assert gwei == Decimal("25")


# ─────────────────────────────────────────────────────────────────
#  PROCESSOR UNIT TESTS
# ─────────────────────────────────────────────────────────────────

class TestReceiptProcessor:

    @patch("apps.blockchain.processor.ReceiptProcessor._upsert_transaction_log")
    @patch("apps.blockchain.processor.ReceiptProcessor._store_events")
    def test_process_donation_receipt_marks_confirmed(
        self, mock_store, mock_upsert, service, mock_w3, pending_donation
    ):
        from apps.blockchain.processor import ReceiptProcessor
        from apps.donations.models import TxStatus

        mock_w3.eth.block_number = 12345010
        service.decode_donation_event = MagicMock(return_value=None)
        service.decode_events         = MagicMock(return_value=[])
        service.get_block_timestamp   = MagicMock(return_value=timezone.now())
        service.get_transaction       = MagicMock(return_value=None)
        mock_upsert.return_value      = MagicMock()

        processor = ReceiptProcessor(service)
        result    = processor.process_donation_receipt(pending_donation, MOCK_RECEIPT)

        assert result["status"] == "confirmed"
        pending_donation.refresh_from_db()
        assert pending_donation.tx_status == TxStatus.CONFIRMED
        assert pending_donation.is_verified is True

    def test_process_already_confirmed_is_noop(
        self, service, db, active_jar, donor_user
    ):
        from apps.blockchain.processor import ReceiptProcessor
        from apps.donations.models import Donation, TxStatus

        already_confirmed = Donation.objects.create(
            jar=active_jar,
            donor=donor_user,
            donor_wallet=MOCK_WALLET,
            amount_matic=Decimal("1.0"),
            amount_wei="1000000000000000000",
            tx_hash="0x" + "c" * 64,
            tx_status=TxStatus.CONFIRMED,
            is_verified=True,
        )
        processor = ReceiptProcessor(service)
        result    = processor.process_donation_receipt(already_confirmed, MOCK_RECEIPT)
        assert result["status"] == "already_confirmed"

    def test_process_reverted_marks_failed(
        self, service, mock_w3, pending_donation
    ):
        from apps.blockchain.exceptions import TransactionRevertedError
        from apps.blockchain.processor import ReceiptProcessor
        from apps.donations.models import TxStatus

        mock_w3.eth.block_number = 12345010
        service.validate_receipt = MagicMock(
            side_effect=TransactionRevertedError("reverted")
        )
        processor = ReceiptProcessor(service)
        result    = processor.process_donation_failure(pending_donation, "reverted")

        assert result["status"] == "failed"
        pending_donation.refresh_from_db()
        assert pending_donation.tx_status == TxStatus.FAILED


# ─────────────────────────────────────────────────────────────────
#  CELERY TASK TESTS (mocked — no real Celery needed)
# ─────────────────────────────────────────────────────────────────

class TestVerifySingleTransactionTask:

    @patch("apps.blockchain.tasks.BlockchainService")
    @patch("apps.blockchain.tasks.ReceiptProcessor")
    def test_task_confirms_donation(
        self, MockProcessor, MockService, pending_donation
    ):
        from apps.blockchain.tasks import verify_single_transaction

        mock_svc       = MockService.return_value
        mock_proc      = MockProcessor.return_value
        mock_svc.get_receipt.return_value = MOCK_RECEIPT
        mock_proc.process_donation_receipt.return_value = {
            "status": "confirmed", "donation_id": pending_donation.id
        }

        result = verify_single_transaction.apply(args=[MOCK_TX_HASH]).get()
        assert result["status"] == "confirmed"

    @patch("apps.blockchain.tasks.BlockchainService")
    def test_task_returns_not_found_for_missing_tx(self, MockService, db):
        from apps.blockchain.tasks import verify_single_transaction

        result = verify_single_transaction.apply(
            args=["0x" + "f" * 64]
        ).get()
        assert result["status"] == "not_found"

    @patch("apps.blockchain.tasks.BlockchainService")
    @patch("apps.blockchain.tasks.ReceiptProcessor")
    def test_task_handles_reverted_tx(
        self, MockProcessor, MockService, pending_donation
    ):
        from apps.blockchain.tasks import verify_single_transaction
        from apps.blockchain.exceptions import TransactionRevertedError

        mock_svc  = MockService.return_value
        mock_proc = MockProcessor.return_value
        mock_svc.get_receipt.return_value = MOCK_REVERTED_RECEIPT
        mock_proc.process_donation_receipt.side_effect = TransactionRevertedError("revert")
        mock_proc.process_donation_failure.return_value = {"status": "failed"}

        result = verify_single_transaction.apply(args=[MOCK_TX_HASH]).get()
        assert "failed" in result["status"]


class TestBackoffDelay:
    def test_early_retries_are_short(self):
        from apps.blockchain.tasks import _backoff_delay
        assert _backoff_delay(0) == 15
        assert _backoff_delay(3) == 15

    def test_mid_retries_are_medium(self):
        from apps.blockchain.tasks import _backoff_delay
        assert _backoff_delay(4) == 30
        assert _backoff_delay(5) == 30

    def test_late_retries_are_long(self):
        from apps.blockchain.tasks import _backoff_delay
        assert _backoff_delay(6) == 60
        assert _backoff_delay(10) == 120
