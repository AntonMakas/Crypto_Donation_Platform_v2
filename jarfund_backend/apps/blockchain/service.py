"""
BlockchainService — the central web3.py integration layer.

Responsibilities:
  ─ Maintain a Web3 connection to the Polygon Amoy RPC node
  ─ Fetch and validate transaction receipts
  ─ Decode contract event logs from ABI
  ─ Read on-chain jar state
  ─ Provide helper methods for Celery tasks

Design decisions:
  ─ Singleton-style: a single instance is reused across tasks (connection pooling)
  ─ Lazy initialization: Web3 connection only established when first needed
  ─ All public methods raise typed exceptions from blockchain/exceptions.py
  ─ No Django model imports here — service is pure web3.py logic
"""
import json
import logging
import time
from decimal import Decimal
from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.exceptions import TransactionNotFound, BadFunctionCallOutput
from web3.middleware import ExtraDataToPOAMiddleware

from .exceptions import (
    ABINotFoundError,
    ChainIdMismatchError,
    ContractNotConfiguredError,
    InsufficientConfirmationsError,
    InvalidReceiptError,
    RPCConnectionError,
    RPCTimeoutError,
    TransactionNotFoundError,
    TransactionRevertedError,
    WrongContractError,
)

logger = logging.getLogger(__name__)


class BlockchainService:
    """
    Stateless service layer wrapping web3.py for the JarFund contract.

    Usage (in Celery tasks):
        svc = BlockchainService()
        receipt = svc.get_receipt(tx_hash)
        events  = svc.decode_events(receipt)
    """

    # Cache the ABI in memory — only read from disk once
    _abi_cache: list | None = None

    # ─────────────────────────────────────────────────────────────
    #  INITIALISATION
    # ─────────────────────────────────────────────────────────────

    def __init__(self):
        from django.conf import settings
        self._settings        = settings.BLOCKCHAIN
        self._network_name    = self._settings.get("NETWORK_NAME", "amoy").lower()
        self._rpc_url         = self._select_rpc_url()
        self._contract_addr   = self._settings.get("CONTRACT_ADDRESS", "")
        self._chain_id        = self._settings.get("CHAIN_ID", 80002)
        self._required_confs  = self._settings.get("REQUIRED_CONFIRMATIONS", 3)
        self._explorer_url    = self._settings.get(
            "EXPLORER_URL",
            "https://polygonscan.com" if self._network_name == "polygon"
            else "https://amoy.polygonscan.com",
        )

        if not self._rpc_url:
            raise RPCConnectionError(
                f"RPC URL is not configured for network '{self._network_name}'."
            )

        self._w3: Web3 | None = None

    def _select_rpc_url(self) -> str:
        """Choose the correct RPC URL for the configured network."""
        if self._network_name == "polygon":
            return self._settings.get("POLYGON_MAINNET_RPC_URL", "")
        return self._settings.get("POLYGON_AMOY_RPC_URL", "")

    # ─────────────────────────────────────────────────────────────
    #  CONNECTION
    # ─────────────────────────────────────────────────────────────

    @property
    def w3(self) -> Web3:
        """
        Lazy Web3 instance.  Establishes connection on first access.
        Polygon Amoy uses PoA consensus, so ExtraDataToPOAMiddleware is required
        to handle the extra vanityData field in block headers.
        """
        if self._w3 is None:
            self._w3 = self._connect()
        return self._w3

    def _connect(self) -> Web3:
        logger.debug("Connecting to RPC: %s", self._rpc_url[:40])
        try:
            w3 = Web3(Web3.HTTPProvider(
                self._rpc_url,
                request_kwargs={"timeout": 30},
            ))
            # Required for Polygon PoA chains
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        except Exception as exc:
            raise RPCConnectionError(f"Failed to create Web3 provider: {exc}") from exc

        if not w3.is_connected():
            raise RPCConnectionError(
                f"Cannot connect to RPC node at {self._rpc_url[:40]}. "
                "Check POLYGON_AMOY_RPC_URL and network connectivity."
            )

        # Validate chain ID — prevents accidentally hitting mainnet
        actual_chain_id = w3.eth.chain_id
        if actual_chain_id != self._chain_id:
            raise ChainIdMismatchError(
                expected=self._chain_id,
                actual=actual_chain_id,
            )

        logger.info(
            "Connected to chain %s — block #%s",
            actual_chain_id,
            w3.eth.block_number,
        )
        return w3

    def is_connected(self) -> bool:
        """Safe connectivity check that never raises."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def reconnect(self) -> None:
        """Force a fresh connection — call after connection drops."""
        self._w3 = None
        _ = self.w3  # trigger reconnect

    # ─────────────────────────────────────────────────────────────
    #  ABI
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def _load_abi(cls) -> list:
        """Load the JarFund ABI from disk. Cached after first load."""
        if cls._abi_cache is not None:
            return cls._abi_cache

        abi_path = Path(__file__).parent / "abi" / "JarFund.json"

        if not abi_path.exists():
            raise ABINotFoundError(
                f"JarFund ABI not found at {abi_path}. "
                "Run: cp ../blockchain/artifacts/contracts/JarFund.sol/JarFund.json "
                "apps/blockchain/abi/"
            )

        try:
            raw = json.loads(abi_path.read_text())
            # Hardhat artifacts wrap the ABI; plain ABI files are a list directly
            cls._abi_cache = raw.get("abi", raw) if isinstance(raw, dict) else raw
            logger.debug("ABI loaded: %d entries", len(cls._abi_cache))
            return cls._abi_cache
        except (json.JSONDecodeError, KeyError) as exc:
            raise ABINotFoundError(f"Failed to parse JarFund ABI: {exc}") from exc

    # ─────────────────────────────────────────────────────────────
    #  CONTRACT INSTANCE
    # ─────────────────────────────────────────────────────────────

    @cached_property
    def contract(self):
        """
        web3.py contract instance bound to the deployed JarFund address.
        Cached on first access per BlockchainService instance.
        """
        if not self._contract_addr:
            raise ContractNotConfiguredError(
                "CONTRACT_ADDRESS is empty. Deploy the contract and set it in .env."
            )
        try:
            address = Web3.to_checksum_address(self._contract_addr)
        except ValueError as exc:
            raise ContractNotConfiguredError(
                f"CONTRACT_ADDRESS is not a valid Ethereum address: {exc}"
            ) from exc

        return self.w3.eth.contract(
            address=address,
            abi=self._load_abi(),
        )

    # ─────────────────────────────────────────────────────────────
    #  RECEIPT FETCHING
    # ─────────────────────────────────────────────────────────────

    def get_receipt(self, tx_hash: str, retries: int = 3, delay: float = 2.0) -> dict | None:
        """
        Fetch a transaction receipt from the RPC node.

        Args:
            tx_hash:  The 0x-prefixed transaction hash.
            retries:  Number of attempts before giving up.
            delay:    Seconds to wait between retries.

        Returns:
            The receipt dict, or None if the tx is not yet mined.

        Raises:
            RPCConnectionError   — node unreachable
            RPCTimeoutError      — call timed out
        """
        for attempt in range(1, retries + 1):
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                return dict(receipt) if receipt else None

            except TransactionNotFound:
                return None  # tx not yet mined — not an error

            except TimeoutError as exc:
                if attempt == retries:
                    raise RPCTimeoutError(
                        f"RPC timed out fetching receipt for {tx_hash[:12]}… after {retries} attempts."
                    ) from exc
                logger.warning("Receipt fetch timeout (attempt %d/%d), retrying…", attempt, retries)
                time.sleep(delay)

            except Exception as exc:
                err_str = str(exc).lower()
                if "connection" in err_str or "network" in err_str:
                    raise RPCConnectionError(f"RPC connection error: {exc}") from exc
                raise RPCConnectionError(f"Unexpected RPC error: {exc}") from exc

        return None

    def get_transaction(self, tx_hash: str) -> dict | None:
        """Fetch the full transaction (not receipt) — includes input data, gasPrice."""
        try:
            tx = self.w3.eth.get_transaction(tx_hash)
            return dict(tx) if tx else None
        except TransactionNotFound:
            return None
        except Exception as exc:
            raise RPCConnectionError(f"Failed to fetch transaction: {exc}") from exc

    # ─────────────────────────────────────────────────────────────
    #  BLOCK HELPERS
    # ─────────────────────────────────────────────────────────────

    def get_current_block(self) -> int:
        """Current block number on the connected chain."""
        try:
            return self.w3.eth.block_number
        except Exception as exc:
            raise RPCConnectionError(f"Failed to fetch block number: {exc}") from exc

    def get_confirmations(self, tx_block_number: int) -> int:
        """
        Calculate confirmations for a transaction in a given block.
        Returns 0 if the tx block is ahead of latest (shouldn't happen).
        """
        current = self.get_current_block()
        # Include the transaction's own block in the confirmation count.
        return max(0, current - tx_block_number + 1)

    def get_block_timestamp(self, block_number: int) -> datetime | None:
        """
        Fetch the Unix timestamp for a block and convert to a timezone-aware datetime.
        """
        try:
            block = self.w3.eth.get_block(block_number)
            ts    = block.get("timestamp")
            if ts is None:
                return None
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception as exc:
            logger.warning("Failed to fetch block %s timestamp: %s", block_number, exc)
            return None

    # ─────────────────────────────────────────────────────────────
    #  RECEIPT VALIDATION
    # ─────────────────────────────────────────────────────────────

    def validate_receipt(self, receipt: dict, tx_hash: str) -> None:
        """
        Validate a receipt against security constraints:
          1. Transaction status == 1 (not reverted)
          2. Contract address matches our deployment
          3. Required confirmations reached

        Raises typed exceptions for each failure case.
        """
        if not receipt:
            raise InvalidReceiptError(f"Empty receipt for {tx_hash[:12]}…")

        # ── 1. Revert check ──────────────────────────────────────
        tx_status = receipt.get("status")
        if tx_status == 0:
            raise TransactionRevertedError(
                f"Transaction {tx_hash[:12]}… was reverted (status=0). "
                "The donate() call failed on-chain."
            )
        if tx_status is None:
            raise InvalidReceiptError(
                f"Receipt for {tx_hash[:12]}… has no 'status' field."
            )

        # ── 2. Contract address check ────────────────────────────
        if self._contract_addr:
            to_addr = receipt.get("to") or receipt.get("contractAddress", "")
            if to_addr and to_addr.lower() != self._contract_addr.lower():
                raise WrongContractError(
                    f"Transaction {tx_hash[:12]}… was sent to {to_addr}, "
                    f"not the JarFund contract at {self._contract_addr}."
                )

        # ── 3. Confirmations check ───────────────────────────────
        block_number = receipt.get("blockNumber")
        if block_number is not None:
            confs = self.get_confirmations(block_number)
            if confs < self._required_confs:
                raise InsufficientConfirmationsError(
                    current=confs,
                    required=self._required_confs,
                )

    # ─────────────────────────────────────────────────────────────
    #  EVENT DECODING
    # ─────────────────────────────────────────────────────────────

    def decode_events(self, receipt: dict) -> list[dict]:
        """
        Decode all JarFund contract events from a transaction receipt.

        Returns a list of decoded event dicts:
            [
                {
                    "event":     "DonationReceived",
                    "log_index": 0,
                    "args": { "jarId": 1, "donor": "0x…", "amount": 500000000000000000 }
                },
                ...
            ]
        """
        if not receipt or not receipt.get("logs"):
            return []

        decoded = []

        # Events we know how to decode
        event_names = [
            "JarCreated",
            "DonationReceived",
            "FundsWithdrawn",
            "JarStatusChanged",
        ]

        for event_name in event_names:
            try:
                event_obj = getattr(self.contract.events, event_name)()
                logs = event_obj.process_receipt(receipt, errors="discard")
                for log in logs:
                    decoded.append({
                        "event":      event_name,
                        "log_index":  log.get("logIndex", 0),
                        "tx_hash":    log.get("transactionHash", b"").hex()
                                      if hasattr(log.get("transactionHash", ""), "hex")
                                      else str(log.get("transactionHash", "")),
                        "block_number": log.get("blockNumber"),
                        "args":       dict(log.get("args", {})),
                    })
            except Exception as exc:
                # Log but don't crash — one event failing shouldn't stop others
                logger.debug("Could not decode event %s: %s", event_name, exc)

        logger.debug(
            "Decoded %d event(s) from tx %s",
            len(decoded),
            str(receipt.get("transactionHash", ""))[:14],
        )
        return decoded

    def decode_donation_event(self, receipt: dict) -> dict | None:
        """
        Extract the DonationReceived event arguments from a receipt.
        Returns the args dict, or None if the event wasn't found.
        """
        events = self.decode_events(receipt)
        for ev in events:
            if ev["event"] == "DonationReceived":
                return ev["args"]
        return None

    def decode_jar_created_event(self, receipt: dict) -> dict | None:
        """Extract the JarCreated event arguments from a receipt."""
        events = self.decode_events(receipt)
        for ev in events:
            if ev["event"] == "JarCreated":
                return ev["args"]
        return None

    # ─────────────────────────────────────────────────────────────
    #  GAS HELPERS
    # ─────────────────────────────────────────────────────────────

    def get_gas_price_gwei(self, receipt: dict, tx_data: dict | None = None) -> Decimal:
        """
        Extract gas price in gwei from a transaction.
        Tries effective_gas_price (EIP-1559) first, then falls back to gasPrice.
        """
        # EIP-1559 fields
        effective = receipt.get("effectiveGasPrice")
        if effective:
            return Decimal(str(Web3.from_wei(effective, "gwei")))

        # Legacy gasPrice from the tx object
        if tx_data:
            gas_price = tx_data.get("gasPrice")
            if gas_price:
                return Decimal(str(Web3.from_wei(gas_price, "gwei")))

        return Decimal("0")

    # ─────────────────────────────────────────────────────────────
    #  ON-CHAIN JAR STATE READS (view calls)
    # ─────────────────────────────────────────────────────────────

    def get_on_chain_jar(self, chain_jar_id: int) -> dict | None:
        """
        Call getJar(jarId) on the contract and return the struct as a dict.
        Returns None if the jar doesn't exist (call reverts).

        On-chain status values:
            0=Active, 1=Completed, 2=Expired, 3=Withdrawn
        """
        STATUS_MAP = {0: "active", 1: "completed", 2: "expired", 3: "withdrawn"}

        try:
            raw = self.contract.functions.getJar(chain_jar_id).call()
            return {
                "id":            raw[0],
                "creator":       raw[1],
                "title":         raw[2],
                "description":   raw[3],
                "target_amount": Web3.from_wei(raw[4], "ether"),
                "amount_raised": Web3.from_wei(raw[5], "ether"),
                "deadline":      datetime.fromtimestamp(raw[6], tz=timezone.utc),
                "status":        STATUS_MAP.get(raw[7], "unknown"),
                "donor_count":   raw[8],
                "created_at":    datetime.fromtimestamp(raw[9], tz=timezone.utc),
            }
        except BadFunctionCallOutput:
            return None  # Jar doesn't exist
        except Exception as exc:
            logger.warning("getJar(%s) call failed: %s", chain_jar_id, exc)
            return None

    def get_on_chain_can_withdraw(self, chain_jar_id: int) -> bool:
        """Call canWithdraw(jarId) on the contract."""
        try:
            return self.contract.functions.canWithdraw(chain_jar_id).call()
        except Exception as exc:
            logger.warning("canWithdraw(%s) call failed: %s", chain_jar_id, exc)
            return False

    def get_on_chain_donor_amount(self, chain_jar_id: int, donor_address: str) -> Decimal:
        """Call getDonorAmount(jarId, donor) and convert from wei to MATIC."""
        try:
            address = Web3.to_checksum_address(donor_address)
            wei = self.contract.functions.getDonorAmount(chain_jar_id, address).call()
            return Decimal(str(Web3.from_wei(wei, "ether")))
        except Exception as exc:
            logger.warning("getDonorAmount call failed: %s", exc)
            return Decimal("0")

    def get_total_jars(self) -> int:
        """Read totalJars() from the contract."""
        try:
            return self.contract.functions.totalJars().call()
        except Exception as exc:
            logger.warning("totalJars() call failed: %s", exc)
            return 0

    def get_contract_balance(self) -> Decimal:
        """Read contractBalance() in MATIC."""
        try:
            wei = self.contract.functions.contractBalance().call()
            return Decimal(str(Web3.from_wei(wei, "ether")))
        except Exception as exc:
            logger.warning("contractBalance() call failed: %s", exc)
            return Decimal("0")

    # ─────────────────────────────────────────────────────────────
    #  UTILITY
    # ─────────────────────────────────────────────────────────────

    def wei_to_matic(self, wei: int | str) -> Decimal:
        """Convert wei (int or string) to MATIC as Decimal."""
        return Decimal(str(Web3.from_wei(int(wei), "ether")))

    def matic_to_wei(self, matic: Decimal | float | str) -> int:
        """Convert MATIC to wei."""
        return Web3.to_wei(matic, "ether")

    def is_valid_address(self, address: str) -> bool:
        """Check if a string is a valid Ethereum address."""
        return Web3.is_address(address)

    def to_checksum_address(self, address: str) -> str:
        """Return EIP-55 checksummed address."""
        return Web3.to_checksum_address(address)

    def explorer_tx_url(self, tx_hash: str) -> str:
        return f"{self._explorer_url}/tx/{tx_hash}"

    def explorer_address_url(self, address: str) -> str:
        return f"{self._explorer_url}/address/{address}"
