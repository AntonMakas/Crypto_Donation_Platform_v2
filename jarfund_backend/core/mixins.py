"""
Reusable view mixins shared across all JarFund API views.
"""
from rest_framework.response import Response


class SuccessResponseMixin:
    """
    Wraps all successful responses in a consistent envelope:
        { "success": true, "data": { ... } }
    """
    def success_response(self, data, status=200, message=None):
        payload = {"success": True, "data": data}
        if message:
            payload["message"] = message
        return Response(payload, status=status)


class WalletValidationMixin:
    """
    Provides helper methods for validating Ethereum wallet addresses.
    Used in views that accept wallet addresses as parameters.
    """
    def validate_wallet_address(self, address: str) -> str:
        """
        Validate and checksum an Ethereum address.
        Raises ValidationError if invalid.
        """
        from web3 import Web3
        from rest_framework.exceptions import ValidationError

        if not address:
            raise ValidationError("Wallet address is required.")

        if not Web3.is_address(address):
            raise ValidationError(
                f"Invalid Ethereum address: {address}. "
                "Must be a 42-character hex string starting with '0x'."
            )

        # Return checksum version (EIP-55)
        return Web3.to_checksum_address(address)
