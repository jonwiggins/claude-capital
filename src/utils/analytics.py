"""
Performance analytics for Claude Capital.

Provides comprehensive performance metrics and analysis tools.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class PerformanceAnalytics:
    """Calculates and tracks performance metrics."""

    @staticmethod
    def calculate_returns(trades: List[Dict[str, Any]]) -> np.ndarray:
        """
        Calculate returns from trade history.

        Args:
            trades: List of trades

        Returns:
            Array of returns
        """
        if not trades:
            return np.array([])

        returns = []
        for trade in trades:
            pnl = trade.get('realized_pnl_usd', trade.get('pnl_usd', 0))
            cost = trade.get('cost', trade['size'] * trade['price'])

            if cost > 0:
                ret = pnl / cost
                returns.append(ret)

        return np.array(returns)

    @staticmethod
    def calculate_sharpe_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.04,
        periods_per_year: int = 365
    ) -> float:
        """
        Calculate Sharpe ratio.

        Args:
            returns: Array of period returns
            risk_free_rate: Annual risk-free rate
            periods_per_year: Number of periods in a year

        Returns:
            Sharpe ratio
        """
        if len(returns) < 2:
            return 0.0

        # Calculate mean and std of returns
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)

        if std_return == 0:
            return 0.0

        # Annualize
        annual_return = mean_return * periods_per_year
        annual_std = std_return * np.sqrt(periods_per_year)

        # Sharpe ratio
        sharpe = (annual_return - risk_free_rate) / annual_std

        return sharpe

    @staticmethod
    def calculate_sortino_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.04,
        periods_per_year: int = 365
    ) -> float:
        """
        Calculate Sortino ratio (like Sharpe but only considers downside volatility).

        Args:
            returns: Array of period returns
            risk_free_rate: Annual risk-free rate
            periods_per_year: Number of periods in a year

        Returns:
            Sortino ratio
        """
        if len(returns) < 2:
            return 0.0

        mean_return = np.mean(returns)

        # Downside deviation (only negative returns)
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return float('inf')  # All positive returns

        downside_std = np.std(downside_returns, ddof=1)

        if downside_std == 0:
            return 0.0

        # Annualize
        annual_return = mean_return * periods_per_year
        annual_downside_std = downside_std * np.sqrt(periods_per_year)

        sortino = (annual_return - risk_free_rate) / annual_downside_std

        return sortino

    @staticmethod
    def calculate_max_drawdown(equity_curve: np.ndarray) -> Dict[str, Any]:
        """
        Calculate maximum drawdown from equity curve.

        Args:
            equity_curve: Array of portfolio values over time

        Returns:
            Dict with max drawdown info
        """
        if len(equity_curve) == 0:
            return {"max_drawdown": 0, "max_drawdown_pct": 0, "peak_value": 0}

        # Calculate running maximum
        running_max = np.maximum.accumulate(equity_curve)

        # Calculate drawdown at each point
        drawdown = running_max - equity_curve
        drawdown_pct = drawdown / running_max

        max_dd = np.max(drawdown)
        max_dd_pct = np.max(drawdown_pct)
        max_dd_idx = np.argmax(drawdown)

        peak_value = running_max[max_dd_idx]

        return {
            "max_drawdown": float(max_dd),
            "max_drawdown_pct": float(max_dd_pct),
            "peak_value": float(peak_value),
            "max_dd_date_idx": int(max_dd_idx)
        }

    @staticmethod
    def calculate_win_rate(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate win rate and related metrics.

        Args:
            trades: List of trades

        Returns:
            Dict with win rate metrics
        """
        if not trades:
            return {
                "win_rate": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0
            }

        winning = []
        losing = []

        for trade in trades:
            pnl = trade.get('realized_pnl_usd', trade.get('pnl_usd', 0))

            if pnl > 0:
                winning.append(pnl)
            elif pnl < 0:
                losing.append(abs(pnl))

        total_trades = len(trades)
        winning_trades = len(winning)
        losing_trades = len(losing)

        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        avg_win = np.mean(winning) if winning else 0
        avg_loss = np.mean(losing) if losing else 0

        total_wins = sum(winning)
        total_losses = sum(losing)

        profit_factor = total_wins / total_losses if total_losses > 0 else (total_wins if total_wins > 0 else 0)

        return {
            "win_rate": win_rate,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor
        }

    @staticmethod
    def calculate_var(
        returns: np.ndarray,
        confidence: float = 0.95,
        method: str = 'historical'
    ) -> float:
        """
        Calculate Value at Risk.

        Args:
            returns: Array of returns
            confidence: Confidence level (0.95 = 95%)
            method: 'historical' or 'parametric'

        Returns:
            VaR (as a positive number representing potential loss)
        """
        if len(returns) == 0:
            return 0.0

        if method == 'historical':
            # Historical VaR
            var = -np.percentile(returns, (1 - confidence) * 100)
        else:
            # Parametric VaR (assumes normal distribution)
            mean = np.mean(returns)
            std = np.std(returns, ddof=1)
            from scipy import stats
            z_score = stats.norm.ppf(1 - confidence)
            var = -(mean + z_score * std)

        return float(var)

    @staticmethod
    def calculate_cvar(
        returns: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall).

        Args:
            returns: Array of returns
            confidence: Confidence level

        Returns:
            CVaR (average of losses beyond VaR)
        """
        if len(returns) == 0:
            return 0.0

        var_threshold = np.percentile(returns, (1 - confidence) * 100)

        # Get all returns worse than VaR
        tail_returns = returns[returns <= var_threshold]

        if len(tail_returns) == 0:
            return 0.0

        cvar = -np.mean(tail_returns)

        return float(cvar)

    @staticmethod
    def create_equity_curve(
        trades: List[Dict[str, Any]],
        initial_capital: float
    ) -> np.ndarray:
        """
        Create equity curve from trade history.

        Args:
            trades: List of trades (sorted by timestamp)
            initial_capital: Starting capital

        Returns:
            Array of equity values
        """
        if not trades:
            return np.array([initial_capital])

        equity = [initial_capital]

        for trade in trades:
            pnl = trade.get('realized_pnl_usd', trade.get('pnl_usd', 0))
            equity.append(equity[-1] + pnl)

        return np.array(equity)

    @staticmethod
    def calculate_calmar_ratio(
        total_return: float,
        max_drawdown: float,
        years: float = 1.0
    ) -> float:
        """
        Calculate Calmar ratio (return / max drawdown).

        Args:
            total_return: Total return (as decimal)
            max_drawdown: Maximum drawdown (as decimal)
            years: Time period in years

        Returns:
            Calmar ratio
        """
        if max_drawdown == 0:
            return 0.0

        annualized_return = (1 + total_return) ** (1 / years) - 1

        calmar = annualized_return / max_drawdown

        return calmar

    @staticmethod
    def analyze_trades_by_time(
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze trades by time periods.

        Args:
            trades: List of trades

        Returns:
            Dict with analysis by hour, day of week, month
        """
        if not trades:
            return {}

        by_hour = defaultdict(list)
        by_day = defaultdict(list)
        by_month = defaultdict(list)

        for trade in trades:
            timestamp = trade.get('timestamp')
            if not timestamp:
                continue

            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            pnl = trade.get('realized_pnl_usd', trade.get('pnl_usd', 0))

            by_hour[dt.hour].append(pnl)
            by_day[dt.weekday()].append(pnl)  # 0 = Monday
            by_month[dt.month].append(pnl)

        # Calculate stats for each period
        def calc_stats(data_dict):
            stats = {}
            for key, pnls in data_dict.items():
                if pnls:
                    stats[key] = {
                        "count": len(pnls),
                        "total_pnl": sum(pnls),
                        "avg_pnl": np.mean(pnls),
                        "win_rate": len([p for p in pnls if p > 0]) / len(pnls)
                    }
            return stats

        return {
            "by_hour": calc_stats(by_hour),
            "by_day": calc_stats(by_day),
            "by_month": calc_stats(by_month)
        }

    @staticmethod
    def generate_performance_report(
        state: Dict[str, Any],
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.

        Args:
            state: Current firm state
            initial_capital: Initial capital

        Returns:
            Complete performance report
        """
        trades = state.get('trade_history', [])
        positions = state.get('positions', [])
        current_capital = state['capital']['current_total_usd']

        analytics = PerformanceAnalytics()

        # Basic metrics
        total_return = (current_capital - initial_capital) / initial_capital
        total_pnl = current_capital - initial_capital

        # Trade analysis
        win_rate_metrics = analytics.calculate_win_rate(trades)

        # Returns and risk
        returns = analytics.calculate_returns(trades)

        sharpe = analytics.calculate_sharpe_ratio(returns) if len(returns) > 0 else 0
        sortino = analytics.calculate_sortino_ratio(returns) if len(returns) > 0 else 0

        # Equity curve and drawdown
        equity_curve = analytics.create_equity_curve(trades, initial_capital)
        dd_metrics = analytics.calculate_max_drawdown(equity_curve)

        # VaR
        var_95 = analytics.calculate_var(returns, confidence=0.95) if len(returns) > 0 else 0
        cvar_95 = analytics.calculate_cvar(returns, confidence=0.95) if len(returns) > 0 else 0

        # Time analysis
        time_analysis = analytics.analyze_trades_by_time(trades)

        # Calculate trading days
        if trades:
            first_trade = datetime.fromisoformat(trades[0]['timestamp'].replace('Z', '+00:00'))
            last_trade = datetime.fromisoformat(trades[-1]['timestamp'].replace('Z', '+00:00'))
            days = (last_trade - first_trade).days + 1
        else:
            days = 1

        years = days / 365.0

        # Calmar ratio
        calmar = analytics.calculate_calmar_ratio(
            total_return,
            dd_metrics['max_drawdown_pct'],
            years
        ) if dd_metrics['max_drawdown_pct'] > 0 else 0

        return {
            "overview": {
                "initial_capital": initial_capital,
                "current_capital": current_capital,
                "total_return": total_return,
                "total_return_pct": total_return * 100,
                "total_pnl": total_pnl,
                "trading_days": days,
                "active_positions": len(positions)
            },
            "trade_metrics": win_rate_metrics,
            "risk_metrics": {
                "sharpe_ratio": sharpe,
                "sortino_ratio": sortino,
                "max_drawdown": dd_metrics['max_drawdown'],
                "max_drawdown_pct": dd_metrics['max_drawdown_pct'] * 100,
                "calmar_ratio": calmar,
                "var_95": var_95 * 100,  # As percentage
                "cvar_95": cvar_95 * 100
            },
            "time_analysis": time_analysis,
            "equity_curve": equity_curve.tolist()
        }
