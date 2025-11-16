#!/usr/bin/env python3
"""
Initialize Claude Capital trading firm.

This script sets up the initial state for a new trading firm.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.state import initialize_state
from trading.wallet import encrypt_private_key, create_new_wallet


def main():
    """Main initialization function."""
    parser = argparse.ArgumentParser(
        description="Initialize Claude Capital trading firm"
    )

    parser.add_argument(
        '--name',
        type=str,
        default="Claude Capital",
        help="Name of the trading firm"
    )

    parser.add_argument(
        '--initial-capital',
        type=float,
        required=True,
        help="Initial capital in USD"
    )

    parser.add_argument(
        '--wallet-address',
        type=str,
        help="Existing wallet address (if you have one)"
    )

    parser.add_argument(
        '--wallet-key',
        type=str,
        help="Private key for existing wallet"
    )

    parser.add_argument(
        '--create-wallet',
        action='store_true',
        help="Create a new wallet"
    )

    parser.add_argument(
        '--chain',
        type=str,
        default='ethereum',
        help="Blockchain network (ethereum, polygon, etc.)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("CLAUDE CAPITAL - FIRM INITIALIZATION")
    print("=" * 80)
    print()

    # Handle wallet
    wallet_address = args.wallet_address
    private_key = args.wallet_key

    if args.create_wallet:
        print("Creating new wallet...")
        wallet_data = create_new_wallet(args.chain)
        wallet_address = wallet_data['address']
        private_key = wallet_data['private_key']
        print(f"  Address: {wallet_address}")
        print(f"  Private Key: {private_key}")
        print()
        print("  ⚠️  IMPORTANT: Save your private key securely!")
        print("  You will need it to access your funds.")
        print()

    elif not wallet_address or not private_key:
        print("Error: You must either:")
        print("  1. Use --create-wallet to create a new wallet")
        print("  2. Provide both --wallet-address and --wallet-key")
        sys.exit(1)

    # Encrypt private key
    print("Encrypting private key...")
    encryption_key = encrypt_private_key(
        private_key,
        "secrets/wallet.enc"
    )

    print(f"  Private key encrypted and saved to secrets/wallet.enc")
    print(f"  Encryption key: {encryption_key}")
    print()
    print("  ⚠️  IMPORTANT: Save your encryption key!")
    print("  Add it to your .env file as WALLET_ENCRYPTION_KEY")
    print()

    # Initialize state
    print("Initializing firm state...")
    state = initialize_state(
        name=args.name,
        initial_capital_usd=args.initial_capital,
        wallet_address=wallet_address,
        chain=args.chain
    )

    print(f"  Firm: {args.name}")
    print(f"  Initial Capital: ${args.initial_capital:.2f}")
    print(f"  Wallet: {wallet_address}")
    print(f"  Chain: {args.chain}")
    print()

    print("=" * 80)
    print("INITIALIZATION COMPLETE!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Add your encryption key to .env:")
    print(f"     WALLET_ENCRYPTION_KEY={encryption_key}")
    print()
    print("  2. Add your exchange API keys to .env:")
    print("     BINANCE_API_KEY=your_key")
    print("     BINANCE_SECRET_KEY=your_secret")
    print()
    print("  3. Test the loop:")
    print("     python src/loop.py")
    print()
    print("  4. Set up the scheduler (cron):")
    print("     crontab -e")
    print("     */30 * * * * cd /path/to/claude-capital && python src/loop.py")
    print()
    print("Happy trading! 🚀")
    print()


if __name__ == '__main__':
    main()
