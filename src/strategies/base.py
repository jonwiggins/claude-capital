"""
Base strategy class for trading strategies.

All trading strategies should inherit from BaseStrategy and implement
the required methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.

    Subclasses must implement:
    - analyze(): Analyze market conditions
    - generate_signals(): Generate trading signals
    - should_enter(): Determine if should enter position
    - should_exit(): Determine if should exit position
    """

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy.

        Args:
            name: Strategy name
            params: Strategy parameters
        """
        self.name = name
        self.params = params or {}
        self.id = f"{name}_{uuid.uuid4().hex[:8]}"

        # Performance tracking
        self.performance = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl_usd": 0,
            "win_rate": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0
        }

        # Trade history for this strategy
        self.trades = []

        # Strategy state
        self.active = False
        self.created_at = datetime.utcnow().isoformat()

    @abstractmethod
    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market conditions.

        Args:
            market_data: Market data (OHLCV, indicators, etc.)

        Returns:
            Analysis results
        """
        pass

    @abstractmethod
    def generate_signals(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate trading signals.

        Args:
            symbol: Trading pair
            market_data: Market data

        Returns:
            List of signals [{
                "action": "buy" or "sell",
                "symbol": str,
                "size": float,
                "reason": str,
                "confidence": float
            }]
        """
        pass

    def should_enter(
        self,
        symbol: str,
        current_price: float,
        market_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if should enter a position.

        Args:
            symbol: Trading pair
            current_price: Current price
            market_data: Market data

        Returns:
            (should_enter, reason)
        """
        signals = self.generate_signals(symbol, market_data)

        for signal in signals:
            if signal['action'] == 'buy' and signal['symbol'] == symbol:
                return True, signal.get('reason', 'Signal generated')

        return False, None

    def should_exit(
        self,
        position: Dict[str, Any],
        current_price: float,
        market_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if should exit a position.

        Args:
            position: Current position data
            current_price: Current price
            market_data: Market data

        Returns:
            (should_exit, reason)
        """
        signals = self.generate_signals(position['symbol'], market_data)

        for signal in signals:
            if signal['action'] == 'sell' and signal['symbol'] == position['symbol']:
                return True, signal.get('reason', 'Exit signal generated')

        return False, None

    def update_performance(self, trade: Dict[str, Any]) -> None:
        """
        Update strategy performance metrics.

        Args:
            trade: Completed trade
        """
        self.trades.append(trade)
        self.performance['total_trades'] += 1

        pnl = trade.get('pnl_usd', 0)
        self.performance['total_pnl_usd'] += pnl

        if pnl > 0:
            self.performance['winning_trades'] += 1
        elif pnl < 0:
            self.performance['losing_trades'] += 1

        # Update win rate
        total = self.performance['total_trades']
        if total > 0:
            self.performance['win_rate'] = self.performance['winning_trades'] / total

        # Update average win/loss
        winning_trades = [t for t in self.trades if t.get('pnl_usd', 0) > 0]
        losing_trades = [t for t in self.trades if t.get('pnl_usd', 0) < 0]

        if winning_trades:
            self.performance['avg_win'] = sum(t['pnl_usd'] for t in winning_trades) / len(winning_trades)

        if losing_trades:
            self.performance['avg_loss'] = sum(t['pnl_usd'] for t in losing_trades) / len(losing_trades)

    def get_state(self) -> Dict[str, Any]:
        """
        Get strategy state for persistence.

        Returns:
            Strategy state dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.__class__.__name__,
            "params": self.params,
            "performance": self.performance,
            "active": self.active,
            "created_at": self.created_at,
            "total_trades": len(self.trades)
        }

    def activate(self) -> None:
        """Activate the strategy."""
        self.active = True

    def deactivate(self) -> None:
        """Deactivate the strategy."""
        self.active = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', active={self.active})"
