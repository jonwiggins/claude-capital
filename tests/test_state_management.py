"""
Tests for state management system.
"""

import pytest
import json
import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.state import StateManager, initialize_state


class TestStateManager:
    """Test state manager functionality."""

    @pytest.fixture
    def temp_state_file(self):
        """Create a temporary state file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
        # Cleanup backup dir
        backup_dir = Path(temp_path).parent / "backups"
        if backup_dir.exists():
            for file in backup_dir.glob("*"):
                file.unlink()
            backup_dir.rmdir()

    def test_initialize_state(self, temp_state_file):
        """Test state initialization."""
        state = initialize_state(
            name="Test Firm",
            initial_capital_usd=10000.0,
            wallet_address="0x1234567890123456789012345678901234567890",
            chain="ethereum",
            state_path=temp_state_file
        )

        assert state['firm']['name'] == "Test Firm"
        assert state['capital']['initial_usd'] == 10000.0
        assert state['capital']['current_total_usd'] == 10000.0
        assert state['firm']['wallet']['address'] == "0x1234567890123456789012345678901234567890"
        assert len(state['positions']) == 0
        assert len(state['trade_history']) == 0

    def test_load_save_state(self, temp_state_file):
        """Test loading and saving state."""
        # Initialize
        state = initialize_state(
            name="Test Firm",
            initial_capital_usd=5000.0,
            wallet_address="0x" + "1" * 40,
            state_path=temp_state_file
        )

        # Load
        manager = StateManager(temp_state_file)
        loaded_state = manager.load()

        assert loaded_state['capital']['initial_usd'] == 5000.0

        # Modify and save
        loaded_state['capital']['current_total_usd'] = 5500.0
        manager.save(loaded_state)

        # Load again
        reloaded_state = manager.load()
        assert reloaded_state['capital']['current_total_usd'] == 5500.0

    def test_add_position(self, temp_state_file):
        """Test adding a position."""
        initialize_state(
            name="Test",
            initial_capital_usd=10000.0,
            wallet_address="0x" + "1" * 40,
            state_path=temp_state_file
        )

        manager = StateManager(temp_state_file)

        position = {
            "id": "pos_001",
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "side": "long",
            "size": 0.1,
            "entry_price": 50000.0,
            "current_price": 50000.0,
            "unrealized_pnl_usd": 0,
            "entry_timestamp": "2024-01-01T00:00:00",
            "strategy_name": "test_strategy",
            "notes": "Test position"
        }

        manager.add_position(position)

        state = manager.load()
        assert len(state['positions']) == 1
        assert state['positions'][0]['symbol'] == "BTC/USDT"

    def test_remove_position(self, temp_state_file):
        """Test removing a position."""
        initialize_state(
            name="Test",
            initial_capital_usd=10000.0,
            wallet_address="0x" + "1" * 40,
            state_path=temp_state_file
        )

        manager = StateManager(temp_state_file)

        position = {
            "id": "pos_001",
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "side": "long",
            "size": 0.1,
            "entry_price": 50000.0,
            "current_price": 50000.0,
            "unrealized_pnl_usd": 0,
            "entry_timestamp": "2024-01-01T00:00:00",
            "strategy_name": "test_strategy",
            "notes": "Test position"
        }

        manager.add_position(position)
        removed = manager.remove_position("pos_001")

        assert removed is not None
        assert removed['id'] == "pos_001"

        state = manager.load()
        assert len(state['positions']) == 0

    def test_add_trade(self, temp_state_file):
        """Test adding a trade to history."""
        initialize_state(
            name="Test",
            initial_capital_usd=10000.0,
            wallet_address="0x" + "1" * 40,
            state_path=temp_state_file
        )

        manager = StateManager(temp_state_file)

        trade = {
            "id": "trade_001",
            "timestamp": "2024-01-01T00:00:00",
            "symbol": "BTC/USDT",
            "side": "buy",
            "size": 0.1,
            "price": 50000.0,
            "fees_usd": 5.0,
            "exchange": "binance",
            "strategy": "test",
            "order_id": "order_123"
        }

        manager.add_trade(trade)

        state = manager.load()
        assert len(state['trade_history']) == 1
        assert state['trade_history'][0]['symbol'] == "BTC/USDT"

    def test_add_decision(self, temp_state_file):
        """Test logging a decision."""
        initialize_state(
            name="Test",
            initial_capital_usd=10000.0,
            wallet_address="0x" + "1" * 40,
            state_path=temp_state_file
        )

        manager = StateManager(temp_state_file)

        manager.add_decision(
            decision="Buy 0.1 BTC",
            reasoning="Strong momentum signal",
            confidence=0.8
        )

        state = manager.load()
        assert len(state['decision_log']) == 1
        assert state['decision_log'][0]['decision'] == "Buy 0.1 BTC"
        assert state['decision_log'][0]['confidence'] == 0.8

    def test_emergency_stop(self, temp_state_file):
        """Test emergency stop functionality."""
        initialize_state(
            name="Test",
            initial_capital_usd=10000.0,
            wallet_address="0x" + "1" * 40,
            state_path=temp_state_file
        )

        manager = StateManager(temp_state_file)

        # Initially should be False
        assert not manager.check_emergency_stop()

        # Set emergency stop
        manager.set_emergency_stop(True)
        assert manager.check_emergency_stop()

        # Clear emergency stop
        manager.set_emergency_stop(False)
        assert not manager.check_emergency_stop()

    def test_get_performance_summary(self, temp_state_file):
        """Test performance summary retrieval."""
        initialize_state(
            name="Test",
            initial_capital_usd=10000.0,
            wallet_address="0x" + "1" * 40,
            state_path=temp_state_file
        )

        manager = StateManager(temp_state_file)

        summary = manager.get_performance_summary()

        assert summary['total_capital_usd'] == 10000.0
        assert summary['initial_capital_usd'] == 10000.0
        assert summary['total_pnl_usd'] == 0
        assert summary['active_positions'] == 0
