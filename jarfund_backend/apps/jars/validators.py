"""
Custom Django field validators for the jars app.
"""
import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone


_ETH_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def validate_wallet_address(value: str) -> None:
    """
    Validate that the value is a well-formed Ethereum address.
    Accepts both checksummed and lowercase formats.
    """
    if not value:
        raise ValidationError("Wallet address cannot be empty.")

    if not _ETH_ADDRESS_RE.match(value):
        raise ValidationError(
            f"'{value}' is not a valid Ethereum address. "
            "Must be 42 characters starting with '0x' followed by 40 hex characters."
        )


def validate_future_deadline(value) -> None:
    """
    Validate that the deadline is at least 1 hour in the future
    (mirrors the smart contract MIN_DEADLINE_GAP check).
    """
    min_deadline = timezone.now() + timezone.timedelta(hours=1)
    if value < min_deadline:
        raise ValidationError(
            "Deadline must be at least 1 hour in the future."
        )


def validate_tx_hash(value: str) -> None:
    """
    Validate that a value looks like a valid Ethereum transaction hash.
    Format: 0x followed by exactly 64 hex characters.
    """
    pattern = re.compile(r"^0x[0-9a-fA-F]{64}$")
    if not pattern.match(value):
        raise ValidationError(
            f"'{value}' is not a valid transaction hash. "
            "Must be 66 characters: '0x' + 64 hex digits."
        )


def validate_positive_matic(value: Decimal) -> None:
    """Value must be > 0 MATIC."""
    if value <= 0:
        raise ValidationError("Amount must be greater than 0 MATIC.")


def validate_min_donation(value: Decimal) -> None:
    """Minimum donation is 0.001 MATIC — matches smart contract MIN_DONATION."""
    if value < Decimal("0.001"):
        raise ValidationError(
            f"Minimum donation is 0.001 MATIC. Got: {value}."
        )
