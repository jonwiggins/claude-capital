"""
Wallet management for Claude Capital.

Handles secure storage and usage of private keys, balance checking,
and transaction signing for blockchain operations.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from web3 import Web3
from eth_account import Account
from decimal import Decimal


class WalletManager:
    """Manages cryptocurrency wallet operations."""

    def __init__(
        self,
        wallet_address: str,
        chain: str = "ethereum",
        encrypted_key_path: Optional[str] = None,
        rpc_url: Optional[str] = None
    ):
        """
        Initialize wallet manager.

        Args:
            wallet_address: The wallet's public address
            chain: Blockchain network (ethereum, polygon, etc.)
            encrypted_key_path: Path to encrypted private key file
            rpc_url: RPC endpoint for blockchain connection
        """
        self.address = Web3.to_checksum_address(wallet_address)
        self.chain = chain
        self.encrypted_key_path = encrypted_key_path

        # Set up Web3 connection
        if rpc_url is None:
            # Default RPC endpoints (consider using Infura/Alchemy in production)
            rpc_urls = {
                "ethereum": os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com"),
                "polygon": os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
                "arbitrum": os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
            }
            rpc_url = rpc_urls.get(chain, rpc_urls["ethereum"])

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self._private_key: Optional[str] = None

        # Verify connection
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {chain} RPC: {rpc_url}")

    def load_private_key(self, encryption_key: str) -> None:
        """
        Load and decrypt the private key.

        Args:
            encryption_key: Key used to decrypt the private key file
        """
        if not self.encrypted_key_path:
            raise ValueError("No encrypted key path configured")

        key_path = Path(self.encrypted_key_path)
        if not key_path.exists():
            raise FileNotFoundError(f"Encrypted key file not found: {key_path}")

        # Decrypt private key
        fernet = Fernet(encryption_key.encode())
        with open(key_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted_key = fernet.decrypt(encrypted_data).decode()
        self._private_key = decrypted_key

        # Verify the key matches the address
        account = Account.from_key(self._private_key)
        if account.address.lower() != self.address.lower():
            raise ValueError(
                f"Private key does not match wallet address. "
                f"Expected {self.address}, got {account.address}"
            )

    def get_balance(self, token_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Get wallet balance.

        Args:
            token_address: Address of ERC20 token (None for native token)

        Returns:
            Dictionary with balance information
        """
        if token_address is None:
            # Get native token balance (ETH, MATIC, etc.)
            balance_wei = self.w3.eth.get_balance(self.address)
            balance = Web3.from_wei(balance_wei, 'ether')

            return {
                "token": self._get_native_token_symbol(),
                "balance": float(balance),
                "balance_wei": balance_wei,
                "address": None
            }
        else:
            # Get ERC20 token balance
            token_address = Web3.to_checksum_address(token_address)

            # ERC20 balanceOf ABI
            balance_abi = [{
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }, {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }, {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            }]

            contract = self.w3.eth.contract(address=token_address, abi=balance_abi)

            # Get balance, decimals, and symbol
            balance_raw = contract.functions.balanceOf(self.address).call()
            decimals = contract.functions.decimals().call()
            symbol = contract.functions.symbol().call()

            balance = Decimal(balance_raw) / Decimal(10 ** decimals)

            return {
                "token": symbol,
                "balance": float(balance),
                "balance_raw": balance_raw,
                "decimals": decimals,
                "address": token_address
            }

    def get_all_balances(self, token_addresses: Optional[list] = None) -> Dict[str, Any]:
        """
        Get balances for native token and specified ERC20 tokens.

        Args:
            token_addresses: List of token addresses to check

        Returns:
            Dictionary with all balances
        """
        balances = {
            "native": self.get_balance(),
            "tokens": {}
        }

        if token_addresses:
            for token_addr in token_addresses:
                try:
                    token_balance = self.get_balance(token_addr)
                    balances["tokens"][token_balance["token"]] = token_balance
                except Exception as e:
                    balances["tokens"][token_addr] = {
                        "error": str(e)
                    }

        return balances

    def _get_native_token_symbol(self) -> str:
        """Get the symbol for the native token based on chain."""
        symbols = {
            "ethereum": "ETH",
            "polygon": "MATIC",
            "arbitrum": "ETH",
            "optimism": "ETH",
            "base": "ETH",
        }
        return symbols.get(self.chain, "ETH")

    def estimate_gas(self, transaction: Dict) -> int:
        """
        Estimate gas for a transaction.

        Args:
            transaction: Transaction dictionary

        Returns:
            Estimated gas units
        """
        return self.w3.eth.estimate_gas(transaction)

    def get_gas_price(self) -> int:
        """Get current gas price in wei."""
        return self.w3.eth.gas_price

    def sign_transaction(self, transaction: Dict) -> str:
        """
        Sign a transaction.

        Args:
            transaction: Transaction dictionary

        Returns:
            Signed transaction hash
        """
        if not self._private_key:
            raise ValueError("Private key not loaded. Call load_private_key() first.")

        # Add missing transaction fields
        if 'nonce' not in transaction:
            transaction['nonce'] = self.w3.eth.get_transaction_count(self.address)

        if 'gasPrice' not in transaction and 'maxFeePerGas' not in transaction:
            transaction['gasPrice'] = self.get_gas_price()

        if 'chainId' not in transaction:
            transaction['chainId'] = self.w3.eth.chain_id

        # Sign transaction
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction,
            private_key=self._private_key
        )

        return signed_txn.rawTransaction.hex()

    def send_transaction(self, transaction: Dict, wait_for_receipt: bool = True) -> Dict:
        """
        Sign and send a transaction.

        Args:
            transaction: Transaction dictionary
            wait_for_receipt: Whether to wait for transaction confirmation

        Returns:
            Transaction hash or receipt
        """
        signed_txn_hex = self.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn_hex)

        if wait_for_receipt:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return {
                "hash": tx_hash.hex(),
                "receipt": receipt,
                "status": "success" if receipt['status'] == 1 else "failed"
            }
        else:
            return {
                "hash": tx_hash.hex(),
                "status": "pending"
            }

    def get_transaction_status(self, tx_hash: str) -> Optional[Dict]:
        """
        Get the status of a transaction.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction receipt or None if not found
        """
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            return {
                "hash": tx_hash,
                "status": "success" if receipt['status'] == 1 else "failed",
                "block_number": receipt['blockNumber'],
                "gas_used": receipt['gasUsed']
            }
        except Exception:
            return None


def encrypt_private_key(private_key: str, output_path: str) -> str:
    """
    Encrypt a private key and save to file.

    Args:
        private_key: The private key to encrypt
        output_path: Path to save encrypted key

    Returns:
        The encryption key (store this securely!)
    """
    # Generate encryption key
    encryption_key = Fernet.generate_key()
    fernet = Fernet(encryption_key)

    # Encrypt private key
    encrypted_key = fernet.encrypt(private_key.encode())

    # Save to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'wb') as f:
        f.write(encrypted_key)

    return encryption_key.decode()


def create_new_wallet(chain: str = "ethereum") -> Dict[str, str]:
    """
    Create a new wallet.

    Args:
        chain: Blockchain network

    Returns:
        Dictionary with address and private key
    """
    account = Account.create()

    return {
        "address": account.address,
        "private_key": account.key.hex(),
        "chain": chain
    }
