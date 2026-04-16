"""
Custom exceptions for the blockchain service layer.

These are raised by BlockchainService and caught by Celery tasks
to decide whether to retry, log, or give up.
"""


class BlockchainError(Exception):
    """Base class for all blockchain-related errors."""
    pass


class RPCConnectionError(BlockchainError):
    """
    Cannot connect to the Polygon RPC node.
    Retryable — node may be temporarily unavailable.
    """
    pass


class RPCTimeoutError(BlockchainError):
    """
    RPC call timed out.
    Retryable.
    """
    pass


class ContractNotConfiguredError(BlockchainError):
    """
    CONTRACT_ADDRESS is missing or invalid in settings.
    Not retryable — requires configuration fix.
    """
    pass


class ABINotFoundError(BlockchainError):
    """
    JarFund.json ABI file not found at expected path.
    Not retryable — requires deployment step to copy ABI.
    """
    pass


class TransactionNotFoundError(BlockchainError):
    """
    Transaction hash not found on-chain.
    May be retryable — tx could still be propagating.
    """
    pass


class TransactionRevertedError(BlockchainError):
    """
    Transaction was mined but reverted (status == 0).
    Not retryable — this is a permanent failure.
    """
    pass


class InsufficientConfirmationsError(BlockchainError):
    """
    Transaction found but doesn't have enough confirmations yet.
    Retryable — wait for more blocks.
    """
    def __init__(self, current: int, required: int):
        self.current  = current
        self.required = required
        super().__init__(
            f"Only {current}/{required} confirmations. Waiting for more blocks."
        )


class InvalidReceiptError(BlockchainError):
    """
    Receipt structure is malformed or missing expected fields.
    Not retryable — data integrity issue.
    """
    pass


class WrongContractError(BlockchainError):
    """
    Transaction was sent to a different contract address.
    Not retryable — this tx does not belong to JarFund.
    """
    pass


class ChainIdMismatchError(BlockchainError):
    """
    Connected to wrong network (e.g. mainnet when expecting Amoy).
    Not retryable — configuration error.
    """
    def __init__(self, expected: int, actual: int):
        super().__init__(
            f"Chain ID mismatch: expected {expected}, connected to {actual}."
        )
