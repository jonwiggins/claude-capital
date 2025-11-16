"""
Tests for risk management system.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading.risk import RiskValidator, PortfolioRiskAnalyzer


class TestRiskValidator:
    """Test risk validation."""

    @pytest.fixture
    def risk_limits(self):
        """Standard risk limits."""
        return {
            "max_position_size_usd": 1000,
            "max_total_positions": 5,
            "max_daily_loss_usd": 500,
            "max_total_allocated_pct": 0.8,
            "max_leverage": 1.0,
            "daily_loss_circuit_breaker": True
        }

    @pytest.fixture
    def current_state(self):
        """Sample current state."""
        return {
            "capital": {
                "initial_usd": 10000,
                "current_total_usd": 10000,
                "liquid_usd": 8000,
                "allocated_usd": 2000
            },
            "positions": [
                {
                    "id": "pos_001",
                    "symbol": "BTC/USDT",
                    "size": 0.04,
                    "entry_price": 50000,
                    "current_price": 50000,
                    "unrealized_pnl_usd": 0
                }
            ],
            "trade_history": [],
            "performance": {
                "daily_pnl": []
            }
        }

    def test_validate_position_size(self, risk_limits, current_state):
        """Test position size validation."""
        validator = RiskValidator(risk_limits)

        # Valid trade
        is_valid, error = validator.validate_trade(
            symbol="ETH/USDT",
            side="buy",
            size=0.3,  # 0.3 ETH at $3000 = $900
            price=3000.0,
            current_state=current_state
        )
        assert is_valid

        # Exceeds max position size
        is_valid, error = validator.validate_trade(
            symbol="ETH/USDT",
            side="buy",
            size=1.0,  # 1 ETH at $3000 = $3000 > $1000 limit
            price=3000.0,
            current_state=current_state
        )
        assert not is_valid
        assert "exceeds max position size" in error

    def test_validate_max_positions(self, risk_limits, current_state):
        """Test maximum positions limit."""
        validator = RiskValidator(risk_limits)

        # Add 4 more positions (total would be 5, at limit)
        for i in range(4):
            current_state['positions'].append({
                "id": f"pos_{i:03d}",
                "symbol": f"TOKEN{i}/USDT",
                "size": 100,
                "entry_price": 10,
                "current_price": 10
            })

        # Should still allow one more
        is_valid, error = validator.validate_trade(
            symbol="SOL/USDT",
            side="buy",
            size=5.0,
            price=100.0,
            current_state=current_state
        )
        assert is_valid

        # Now at limit, should reject new position
        current_state['positions'].append({
            "id": "pos_005",
            "symbol": "SOL/USDT",
            "size": 5,
            "entry_price": 100,
            "current_price": 100
        })

        is_valid, error = validator.validate_trade(
            symbol="MATIC/USDT",
            side="buy",
            size=1000.0,
            price=1.0,
            current_state=current_state
        )
        assert not is_valid
        assert "max positions" in error.lower()

    def test_validate_allocation(self, risk_limits, current_state):
        """Test capital allocation limits."""
        validator = RiskValidator(risk_limits)

        # Current allocated: $2000 out of $10000 = 20%
        # Max allowed: 80% = $8000
        # Available: $6000

        # Valid trade within allocation
        is_valid, error = validator.validate_trade(
            symbol="BTC/USDT",
            side="buy",
            size=0.1,  # $5000
            price=50000.0,
            current_state=current_state
        )
        assert is_valid

        # Exceeds allocation limit
        is_valid, error = validator.validate_trade(
            symbol="BTC/USDT",
            side="buy",
            size=0.15,  # $7500 + $2000 = $9500 > $8000 limit
            price=50000.0,
            current_state=current_state
        )
        assert not is_valid
        assert "exceeding limit" in error

    def test_validate_liquid_capital(self, risk_limits, current_state):
        """Test liquid capital validation."""
        validator = RiskValidator(risk_limits)

        # Has $8000 liquid
        is_valid, error = validator.validate_trade(
            symbol="BTC/USDT",
            side="buy",
            size=0.15,  # $7500
            price=50000.0,
            current_state=current_state
        )
        assert is_valid

        # Exceeds liquid capital
        is_valid, error = validator.validate_trade(
            symbol="BTC/USDT",
            side="buy",
            size=0.17,  # $8500 > $8000
            price=50000.0,
            current_state=current_state
        )
        assert not is_valid
        assert "insufficient liquid capital" in error.lower()

    def test_get_max_position_size(self, risk_limits, current_state):
        """Test maximum position size calculation."""
        validator = RiskValidator(risk_limits)

        max_size = validator.get_max_position_size(current_state, price=50000.0)

        # Should be minimum of:
        # - max_position_size_usd: $1000
        # - liquid_capital: $8000
        # - remaining_allocation: $6000
        assert max_size == 1000.0


class TestPortfolioRiskAnalyzer:
    """Test portfolio risk analysis."""

    def test_calculate_concentration(self):
        """Test portfolio concentration calculation."""
        analyzer = PortfolioRiskAnalyzer()

        positions = [
            {"symbol": "BTC/USDT", "size": 0.1, "current_price": 50000},  # $5000
            {"symbol": "ETH/USDT", "size": 1.0, "current_price": 3000},   # $3000
            {"symbol": "SOL/USDT", "size": 20, "current_price": 100}      # $2000
        ]

        concentration = analyzer.calculate_portfolio_concentration(positions)

        assert abs(concentration["BTC/USDT"] - 0.5) < 0.01  # 50%
        assert abs(concentration["ETH/USDT"] - 0.3) < 0.01  # 30%
        assert abs(concentration["SOL/USDT"] - 0.2) < 0.01  # 20%

    def test_calculate_max_drawdown(self):
        """Test maximum drawdown calculation."""
        analyzer = PortfolioRiskAnalyzer()

        # Simulate P&L: start at 0, go to +100, drop to -50, recover to +75
        daily_pnl = [10, 20, 30, 20, 20, -30, -40, -30, 25, 50, 50]

        dd_info = analyzer.calculate_max_drawdown(daily_pnl)

        # Cumulative: 10, 30, 60, 80, 100, 70, 30, 0, 25, 75, 125
        # Peak: 100, drawdown to 0 = 100
        assert dd_info['max_drawdown'] >= 80  # Should be around 100

    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        analyzer = PortfolioRiskAnalyzer()

        # Positive returns with low volatility
        returns = [0.01] * 20 + [0.02] * 20  # 1-2% daily returns

        sharpe = analyzer.calculate_sharpe_ratio(returns, risk_free_rate=0.04)

        # Should be positive with low volatility
        assert sharpe > 0

        # Negative returns
        returns = [-0.01] * 20

        sharpe = analyzer.calculate_sharpe_ratio(returns, risk_free_rate=0.04)

        # Should be negative
        assert sharpe < 0

    def test_calculate_var(self):
        """Test VaR calculation."""
        analyzer = PortfolioRiskAnalyzer()

        positions = [
            {"symbol": "BTC/USDT", "size": 0.1, "current_price": 50000}
        ]

        var = analyzer.calculate_var(positions, confidence=0.95, time_horizon_days=1)

        # VaR should be positive and reasonable
        assert var > 0
        assert var < 5000  # Should be less than position value
