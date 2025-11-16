"""
State management for Claude Capital.

This module handles loading, updating, and persisting the firm's state.
All state is stored in state/firm_state.json as a single source of truth.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from copy import deepcopy


class StateManager:
    """Manages the persistent state of the trading firm."""

    def __init__(self, state_path: str = "state/firm_state.json"):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir = self.state_path.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load the current state from disk."""
        if not self.state_path.exists():
            raise FileNotFoundError(
                f"State file not found: {self.state_path}. "
                "Run initialize_firm.py first."
            )

        with open(self.state_path, 'r') as f:
            state = json.load(f)

        return state

    def save(self, state: Dict[str, Any], backup: bool = True) -> None:
        """
        Save state to disk.

        Args:
            state: The state dictionary to save
            backup: Whether to create a backup of the previous state
        """
        # Backup existing state before overwriting
        if backup and self.state_path.exists():
            self._backup_state()

        # Update system metadata
        state['system']['last_run'] = datetime.utcnow().isoformat()

        # Write state atomically (write to temp file, then rename)
        temp_path = self.state_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(state, f, indent=2, default=str)

        # Atomic rename
        temp_path.replace(self.state_path)

    def _backup_state(self) -> None:
        """Create a timestamped backup of the current state."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"firm_state_{timestamp}.json"

        # Keep only last 100 backups
        backups = sorted(self.backup_dir.glob("firm_state_*.json"))
        if len(backups) >= 100:
            for old_backup in backups[:-99]:
                old_backup.unlink()

        shutil.copy2(self.state_path, backup_path)

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update specific fields in the state.

        Args:
            updates: Dictionary of updates to apply (deep merge)
        """
        state = self.load()
        self._deep_merge(state, updates)
        self.save(state)

    def _deep_merge(self, base: Dict, updates: Dict) -> None:
        """Deep merge updates into base dictionary."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def add_position(self, position: Dict[str, Any]) -> None:
        """Add a new position to the state."""
        state = self.load()
        state['positions'].append(position)
        self.save(state)

    def update_position(self, position_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing position."""
        state = self.load()
        for pos in state['positions']:
            if pos['id'] == position_id:
                pos.update(updates)
                break
        self.save(state)

    def remove_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Remove a position and return it."""
        state = self.load()
        for i, pos in enumerate(state['positions']):
            if pos['id'] == position_id:
                removed = state['positions'].pop(i)
                self.save(state)
                return removed
        return None

    def add_trade(self, trade: Dict[str, Any]) -> None:
        """Add a trade to the history."""
        state = self.load()
        state['trade_history'].append(trade)
        self.save(state)

    def add_decision(self, decision: str, reasoning: str, confidence: float = 0.5) -> None:
        """Log a trading decision."""
        state = self.load()
        decision_entry = {
            "id": f"decision_{len(state['decision_log']) + 1:03d}",
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
            "outcome": "pending"
        }
        state['decision_log'].append(decision_entry)
        self.save(state)

    def add_research_note(self, topic: str, findings: str, action_taken: str = None) -> None:
        """Add a research note."""
        state = self.load()
        research_entry = {
            "id": f"research_{len(state['research_log']) + 1:03d}",
            "timestamp": datetime.utcnow().isoformat(),
            "topic": topic,
            "findings": findings,
            "action_taken": action_taken,
            "outcome": "TBD"
        }
        state['research_log'].append(research_entry)
        self.save(state)

    def log_session(self, actions: list, errors: list = None,
                   next_priorities: list = None, duration: float = 0) -> None:
        """Log a session's activities."""
        state = self.load()
        session_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": duration,
            "actions_taken": actions,
            "errors": errors or [],
            "next_priorities": next_priorities or []
        }
        state['session_log'].append(session_entry)

        # Keep only last 100 sessions in memory
        if len(state['session_log']) > 100:
            state['session_log'] = state['session_log'][-100:]

        self.save(state)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of current performance metrics."""
        state = self.load()
        return {
            "total_capital_usd": state['capital']['current_total_usd'],
            "initial_capital_usd": state['capital']['initial_usd'],
            "total_pnl_usd": state['performance']['total_pnl_usd'],
            "total_trades": state['performance']['total_trades'],
            "win_rate": state['performance']['win_rate'],
            "sharpe_ratio": state['performance'].get('sharpe_ratio', 0),
            "max_drawdown_usd": state['performance'].get('max_drawdown_usd', 0),
            "active_positions": len(state['positions']),
            "active_strategies": len(state['strategies']['active'])
        }

    def check_emergency_stop(self) -> bool:
        """Check if emergency stop is active."""
        state = self.load()
        return state['system'].get('emergency_stop', False)

    def set_emergency_stop(self, active: bool) -> None:
        """Set or clear emergency stop flag."""
        state = self.load()
        state['system']['emergency_stop'] = active
        self.save(state)

        # Also create/remove flag file for external monitoring
        flag_file = self.state_path.parent / "emergency_stop.flag"
        if active:
            flag_file.touch()
        elif flag_file.exists():
            flag_file.unlink()


def initialize_state(
    name: str,
    initial_capital_usd: float,
    wallet_address: str,
    chain: str = "ethereum",
    state_path: str = "state/firm_state.json"
) -> Dict[str, Any]:
    """
    Initialize a new firm state.

    Args:
        name: Name of the trading firm
        initial_capital_usd: Starting capital in USD
        wallet_address: Crypto wallet address
        chain: Blockchain network (default: ethereum)
        state_path: Path to save state file

    Returns:
        Initial state dictionary
    """
    state = {
        "firm": {
            "name": name,
            "inception_date": datetime.utcnow().isoformat(),
            "wallet": {
                "address": wallet_address,
                "chain": chain,
                "encrypted_key_path": "secrets/wallet.enc"
            }
        },
        "capital": {
            "initial_usd": initial_capital_usd,
            "current_total_usd": initial_capital_usd,
            "liquid_usd": initial_capital_usd,
            "allocated_usd": 0
        },
        "positions": [],
        "strategies": {
            "active": [],
            "research": [],
            "retired": []
        },
        "trade_history": [],
        "performance": {
            "total_pnl_usd": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "win_rate": 0,
            "sharpe_ratio": 0,
            "max_drawdown_usd": 0,
            "best_trade_usd": 0,
            "worst_trade_usd": 0,
            "daily_pnl": []
        },
        "risk_limits": {
            "max_position_size_usd": 1000,
            "max_total_positions": 5,
            "max_daily_loss_usd": 500,
            "max_total_allocated_pct": 0.8,
            "max_leverage": 1.0,
            "daily_loss_circuit_breaker": True
        },
        "research_log": [],
        "decision_log": [],
        "session_log": [],
        "system": {
            "version": "0.1.0",
            "last_run": None,
            "emergency_stop": False,
            "alerts": []
        }
    }

    # Save initial state
    manager = StateManager(state_path)
    manager.save(state, backup=False)

    return state
