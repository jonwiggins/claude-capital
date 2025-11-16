"""
Backtesting framework for trading strategies.

Allows testing strategies on historical data before live deployment.
"""

import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
from copy import deepcopy


class Backtester:
    """Backtest trading strategies on historical data."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001
    ):
        """
        Initialize backtester.

        Args:
            initial_capital: Starting capital
            commission: Trading commission (0.001 = 0.1%)
        """
        self.initial_capital = initial_capital
        self.commission = commission

    def run(
        self,
        strategy,
        symbol: str,
        ohlcv_data: List[List],
        position_size_pct: float = 0.1
    ) -> Dict[str, Any]:
        """
        Run backtest on historical data.

        Args:
            strategy: Strategy instance
            symbol: Trading symbol
            ohlcv_data: Historical OHLCV data
            position_size_pct: Position size as % of capital

        Returns:
            Backtest results
        """
        capital = self.initial_capital
        position = None
        trades = []
        equity_curve = [capital]

        for i in range(len(ohlcv_data)):
            # Get current candle
            candle = ohlcv_data[i]
            timestamp = candle[0]
            close_price = candle[4]

            # Prepare market data (rolling window)
            window_start = max(0, i - 100)
            market_data = {
                'ohlcv': ohlcv_data[window_start:i+1],
                'current_price': close_price
            }

            # Check if we have a position
            if position is not None:
                # Update position value
                position_value = position['size'] * close_price

                # Check for exit
                should_exit, reason = strategy.should_exit(
                    position,
                    close_price,
                    market_data
                )

                if should_exit:
                    # Close position
                    proceeds = position_value * (1 - self.commission)
                    capital += proceeds

                    pnl = proceeds - position['cost']

                    trade = {
                        'entry_time': position['entry_time'],
                        'exit_time': timestamp,
                        'symbol': symbol,
                        'side': 'long',
                        'size': position['size'],
                        'entry_price': position['entry_price'],
                        'exit_price': close_price,
                        'pnl_usd': pnl,
                        'pnl_pct': (close_price / position['entry_price'] - 1) * 100,
                        'reason': reason
                    }

                    trades.append(trade)
                    strategy.update_performance(trade)

                    position = None

            else:
                # No position, check for entry
                should_enter, reason = strategy.should_enter(
                    symbol,
                    close_price,
                    market_data
                )

                if should_enter:
                    # Enter position
                    position_value = capital * position_size_pct
                    commission_cost = position_value * self.commission
                    cost = position_value + commission_cost

                    if cost <= capital:
                        capital -= cost

                        position = {
                            'entry_time': timestamp,
                            'symbol': symbol,
                            'size': position_value / close_price,
                            'entry_price': close_price,
                            'cost': cost,
                            'strategy_name': strategy.name
                        }

            # Update equity curve
            total_equity = capital
            if position:
                total_equity += position['size'] * close_price

            equity_curve.append(total_equity)

        # Close any remaining position
        if position:
            close_price = ohlcv_data[-1][4]
            proceeds = position['size'] * close_price * (1 - self.commission)
            capital += proceeds

            pnl = proceeds - position['cost']

            trade = {
                'entry_time': position['entry_time'],
                'exit_time': ohlcv_data[-1][0],
                'symbol': symbol,
                'side': 'long',
                'size': position['size'],
                'entry_price': position['entry_price'],
                'exit_price': close_price,
                'pnl_usd': pnl,
                'pnl_pct': (close_price / position['entry_price'] - 1) * 100,
                'reason': 'End of backtest'
            }

            trades.append(trade)

        # Calculate metrics
        final_capital = equity_curve[-1]
        total_return = (final_capital - self.initial_capital) / self.initial_capital

        winning_trades = [t for t in trades if t['pnl_usd'] > 0]
        losing_trades = [t for t in trades if t['pnl_usd'] < 0]

        win_rate = len(winning_trades) / len(trades) if trades else 0

        # Max drawdown
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (running_max - equity_array) / running_max
        max_drawdown = np.max(drawdown)

        return {
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown * 100,
            'trades': trades,
            'equity_curve': equity_curve,
            'strategy_performance': strategy.performance
        }

    def print_results(self, results: Dict[str, Any]) -> None:
        """
        Print backtest results.

        Args:
            results: Backtest results
        """
        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        print(f"Initial Capital:    ${results['initial_capital']:,.2f}")
        print(f"Final Capital:      ${results['final_capital']:,.2f}")
        print(f"Total Return:       {results['total_return_pct']:+.2f}%")
        print(f"\nTotal Trades:       {results['total_trades']}")
        print(f"Win Rate:           {results['win_rate']*100:.1f}%")
        print(f"Winning Trades:     {results['winning_trades']}")
        print(f"Losing Trades:      {results['losing_trades']}")
        print(f"\nMax Drawdown:       {results['max_drawdown_pct']:.2f}%")
        print("=" * 60 + "\n")
