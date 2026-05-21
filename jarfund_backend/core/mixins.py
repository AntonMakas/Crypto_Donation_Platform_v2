# Checl cheksum and one standart response format
from rest_framework.response import Response


class SuccessResponseMixin:
    def success_response(self, data, status=200, message=None):
        payload = {"success": True, "data": data}
        if message:
            payload["message"] = message
        return Response(payload, status=status)


class WalletValidationMixin:
    def validate_wallet_address(self, address: str) -> str:
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
