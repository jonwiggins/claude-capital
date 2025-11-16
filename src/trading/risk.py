"""
Risk management for Claude Capital.

Implements multi-layer risk controls including position limits,
loss limits, circuit breakers, and pre-trade validation.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal


class RiskValidator:
    """Validates trades against risk limits before execution."""

    def __init__(self, risk_limits: Dict[str, Any]):
        """
        Initialize risk validator.

        Args:
            risk_limits: Dictionary of risk limit parameters
        """
        self.limits = risk_limits
        self.daily_loss_start = None
        self.daily_loss_amount = 0.0

    def validate_trade(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        current_state: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a trade against all risk limits.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            size: Order size
            price: Order price
            current_state: Current firm state

        Returns:
            (is_valid, error_message)
        """
        # Calculate trade value in USD
        trade_value_usd = size * price

        # Check 1: Position size limit
        max_position_size = self.limits.get('max_position_size_usd', float('inf'))
        if trade_value_usd > max_position_size:
            return False, (
                f"Trade value ${trade_value_usd:.2f} exceeds max position size "
                f"${max_position_size:.2f}"
            )

        # Check 2: Total number of positions
        current_positions = len(current_state.get('positions', []))
        max_positions = self.limits.get('max_total_positions', float('inf'))

        if side == 'buy' and current_positions >= max_positions:
            return False, (
                f"Already at max positions ({current_positions}/{max_positions})"
            )

        # Check 3: Total allocated capital
        total_capital = current_state['capital']['current_total_usd']
        current_allocated = current_state['capital']['allocated_usd']
        max_allocated_pct = self.limits.get('max_total_allocated_pct', 1.0)

        if side == 'buy':
            new_allocated_pct = (current_allocated + trade_value_usd) / total_capital
            if new_allocated_pct > max_allocated_pct:
                return False, (
                    f"Trade would allocate {new_allocated_pct:.1%} of capital, "
                    f"exceeding limit of {max_allocated_pct:.1%}"
                )

        # Check 4: Sufficient liquid capital
        liquid_capital = current_state['capital']['liquid_usd']
        if side == 'buy' and trade_value_usd > liquid_capital:
            return False, (
                f"Insufficient liquid capital. Need ${trade_value_usd:.2f}, "
                f"have ${liquid_capital:.2f}"
            )

        # Check 5: Daily loss circuit breaker
        if self.limits.get('daily_loss_circuit_breaker', True):
            if self._check_daily_loss_limit(current_state):
                return False, "Daily loss limit reached - circuit breaker active"

        # Check 6: Leverage limit (if applicable)
        max_leverage = self.limits.get('max_leverage', 1.0)
        if max_leverage < 1.0:
            # For now, we're spot-only, but check for future margin trading
            return False, "Leverage trading not permitted"

        # Check 7: Price sanity check
        if not self._validate_price(symbol, price, tolerance=0.05):
            return False, f"Price ${price:.2f} outside acceptable range for {symbol}"

        return True, None

    def _check_daily_loss_limit(self, current_state: Dict[str, Any]) -> bool:
        """
        Check if daily loss limit has been exceeded.

        Returns:
            True if limit exceeded, False otherwise
        """
        max_daily_loss = self.limits.get('max_daily_loss_usd', float('inf'))

        # Get today's P&L
        today_pnl = self._calculate_daily_pnl(current_state)

        return today_pnl < -max_daily_loss

    def _calculate_daily_pnl(self, current_state: Dict[str, Any]) -> float:
        """Calculate P&L for the current day."""
        today = datetime.utcnow().date()

        daily_pnl = 0.0

        # Sum P&L from trades executed today
        for trade in current_state.get('trade_history', []):
            trade_date = datetime.fromisoformat(trade['timestamp']).date()
            if trade_date == today:
                # This is simplified - would need to track realized P&L properly
                daily_pnl += trade.get('pnl', 0)

        # Add unrealized P&L from positions opened today
        for position in current_state.get('positions', []):
            entry_date = datetime.fromisoformat(position['entry_timestamp']).date()
            if entry_date == today:
                daily_pnl += position.get('unrealized_pnl_usd', 0)

        return daily_pnl

    def _validate_price(
        self,
        symbol: str,
        price: float,
        tolerance: float = 0.05
    ) -> bool:
        """
        Validate that price is within acceptable range.

        This is a basic sanity check. In production, you'd fetch recent
        market price and compare.

        Args:
            symbol: Trading pair
            price: Proposed price
            tolerance: Acceptable deviation (5% by default)

        Returns:
            True if price seems reasonable
        """
        # TODO: Fetch actual market price and compare
        # For now, just check that price is positive
        return price > 0

    def get_max_position_size(
        self,
        current_state: Dict[str, Any],
        price: float
    ) -> float:
        """
        Calculate maximum allowable position size.

        Args:
            current_state: Current firm state
            price: Current price

        Returns:
            Maximum position size in USD
        """
        # Limit 1: Absolute position size limit
        max_by_limit = self.limits.get('max_position_size_usd', float('inf'))

        # Limit 2: Available liquid capital
        liquid_capital = current_state['capital']['liquid_usd']

        # Limit 3: Remaining allocation capacity
        total_capital = current_state['capital']['current_total_usd']
        current_allocated = current_state['capital']['allocated_usd']
        max_allocated_pct = self.limits.get('max_total_allocated_pct', 1.0)
        remaining_allocation = (total_capital * max_allocated_pct) - current_allocated

        # Return the most restrictive limit
        return min(max_by_limit, liquid_capital, remaining_allocation)

    def update_risk_limits(self, new_limits: Dict[str, Any]) -> None:
        """Update risk limits."""
        self.limits.update(new_limits)


class PortfolioRiskAnalyzer:
    """Analyzes portfolio-level risk metrics."""

    def __init__(self):
        """Initialize portfolio risk analyzer."""
        pass

    def calculate_var(
        self,
        positions: List[Dict[str, Any]],
        confidence: float = 0.95,
        time_horizon_days: int = 1
    ) -> float:
        """
        Calculate Value at Risk (VaR).

        Args:
            positions: List of current positions
            confidence: Confidence level (0.95 = 95%)
            time_horizon_days: Time horizon in days

        Returns:
            VaR in USD
        """
        # Simplified VaR calculation
        # In production, would use historical volatility and correlations
        total_exposure = sum(
            pos.get('size', 0) * pos.get('current_price', 0)
            for pos in positions
        )

        # Assume 2% daily volatility (very simplified)
        daily_volatility = 0.02
        z_score = 1.65  # For 95% confidence

        var = total_exposure * daily_volatility * z_score * (time_horizon_days ** 0.5)

        return var

    def calculate_portfolio_concentration(
        self,
        positions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate concentration by asset.

        Args:
            positions: List of positions

        Returns:
            Dictionary of {symbol: percentage}
        """
        total_value = sum(
            pos.get('size', 0) * pos.get('current_price', 0)
            for pos in positions
        )

        if total_value == 0:
            return {}

        concentration = {}
        for pos in positions:
            position_value = pos.get('size', 0) * pos.get('current_price', 0)
            concentration[pos['symbol']] = position_value / total_value

        return concentration

    def calculate_max_drawdown(self, daily_pnl: List[float]) -> Dict[str, Any]:
        """
        Calculate maximum drawdown from P&L history.

        Args:
            daily_pnl: List of daily P&L values

        Returns:
            Dictionary with max drawdown info
        """
        if not daily_pnl:
            return {"max_drawdown": 0, "max_drawdown_pct": 0}

        # Calculate cumulative P&L
        cumulative = []
        total = 0
        for pnl in daily_pnl:
            total += pnl
            cumulative.append(total)

        # Find maximum drawdown
        max_dd = 0
        peak = cumulative[0]

        for value in cumulative:
            if value > peak:
                peak = value

            dd = peak - value
            if dd > max_dd:
                max_dd = dd

        # Calculate percentage drawdown
        max_dd_pct = (max_dd / peak) if peak > 0 else 0

        return {
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd_pct,
            "peak_value": peak
        }

    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.04
    ) -> float:
        """
        Calculate Sharpe ratio.

        Args:
            returns: List of period returns
            risk_free_rate: Annual risk-free rate

        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0

        import statistics

        # Calculate average return
        avg_return = statistics.mean(returns)

        # Calculate standard deviation
        std_dev = statistics.stdev(returns)

        if std_dev == 0:
            return 0

        # Annualize (assuming daily returns)
        annual_return = avg_return * 365
        annual_std = std_dev * (365 ** 0.5)

        # Sharpe ratio
        sharpe = (annual_return - risk_free_rate) / annual_std

        return sharpe


class CircuitBreaker:
    """Implements circuit breaker logic."""

    def __init__(self, state_manager):
        """
        Initialize circuit breaker.

        Args:
            state_manager: StateManager instance
        """
        self.state_manager = state_manager
        self.is_tripped = False

    def check(self, current_state: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if circuit breaker should trip.

        Args:
            current_state: Current firm state

        Returns:
            (should_trip, reason)
        """
        # Check emergency stop flag
        if current_state['system'].get('emergency_stop', False):
            return True, "Emergency stop flag is active"

        # Check daily loss limit
        risk_limits = current_state['risk_limits']
        max_daily_loss = risk_limits.get('max_daily_loss_usd', float('inf'))

        analyzer = PortfolioRiskAnalyzer()
        daily_pnl = current_state['performance'].get('daily_pnl', [])

        if daily_pnl:
            today_pnl = daily_pnl[-1] if daily_pnl else 0
            if today_pnl < -max_daily_loss:
                return True, f"Daily loss ${-today_pnl:.2f} exceeds limit ${max_daily_loss:.2f}"

        # Check max drawdown
        max_dd_info = analyzer.calculate_max_drawdown(
            [sum(current_state['performance'].get('daily_pnl', []))]
        )

        max_dd_threshold = 0.20  # 20% max drawdown
        if max_dd_info['max_drawdown_pct'] > max_dd_threshold:
            return True, f"Max drawdown {max_dd_info['max_drawdown_pct']:.1%} exceeds {max_dd_threshold:.1%}"

        return False, None

    def trip(self, reason: str) -> None:
        """
        Trip the circuit breaker and stop all trading.

        Args:
            reason: Reason for tripping
        """
        self.is_tripped = True
        self.state_manager.set_emergency_stop(True)

        # Add alert
        state = self.state_manager.load()
        state['system']['alerts'].append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "circuit_breaker",
            "severity": "critical",
            "message": f"Circuit breaker tripped: {reason}"
        })
        self.state_manager.save(state)

    def reset(self) -> None:
        """Reset the circuit breaker (requires manual intervention)."""
        self.is_tripped = False
        self.state_manager.set_emergency_stop(False)
