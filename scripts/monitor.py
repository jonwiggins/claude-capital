#!/usr/bin/env python3
"""
Monitoring tool for Claude Capital.

Displays current state, performance metrics, and recent activity.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.state import StateManager
from utils.analytics import PerformanceAnalytics


def format_currency(value: float) -> str:
    """Format currency value."""
    return f"${value:,.2f}"


def format_percent(value: float) -> str:
    """Format percentage value."""
    return f"{value:+.2f}%"


def print_header(title: str):
    """Print section header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_overview(state: Dict[str, Any]):
    """Print overview section."""
    print_header("OVERVIEW")

    capital = state['capital']
    performance = state['performance']

    initial = capital['initial_usd']
    current = capital['current_total_usd']
    pnl = performance['total_pnl_usd']
    pnl_pct = (pnl / initial * 100) if initial > 0 else 0

    print(f"Firm: {state['firm']['name']}")
    print(f"Since: {state['firm']['inception_date'][:10]}")
    print()
    print(f"Initial Capital:  {format_currency(initial)}")
    print(f"Current Capital:  {format_currency(current)}")
    print(f"Total P&L:        {format_currency(pnl)} ({format_percent(pnl_pct)})")
    print()
    print(f"Liquid Capital:   {format_currency(capital['liquid_usd'])}")
    print(f"Allocated:        {format_currency(capital['allocated_usd'])} "
          f"({capital['allocated_usd']/current*100:.1f}%)")


def print_positions(state: Dict[str, Any]):
    """Print open positions."""
    print_header("OPEN POSITIONS")

    positions = state.get('positions', [])

    if not positions:
        print("No open positions")
        return

    print(f"{'Symbol':<15} {'Size':<12} {'Entry':<12} {'Current':<12} {'P&L':>15} {'%':>8}")
    print("-" * 80)

    total_pnl = 0

    for pos in positions:
        symbol = pos['symbol']
        size = pos['size']
        entry_price = pos['entry_price']
        current_price = pos.get('current_price', entry_price)
        unrealized_pnl = pos.get('unrealized_pnl_usd', 0)
        pnl_pct = ((current_price / entry_price) - 1) * 100 if pos['side'] == 'long' else 0

        total_pnl += unrealized_pnl

        print(f"{symbol:<15} {size:<12.4f} ${entry_price:<11.2f} ${current_price:<11.2f} "
              f"{format_currency(unrealized_pnl):>15} {format_percent(pnl_pct):>8}")

    print("-" * 80)
    print(f"{'Total Unrealized P&L:':<60} {format_currency(total_pnl):>19}")


def print_performance(state: Dict[str, Any]):
    """Print performance metrics."""
    print_header("PERFORMANCE METRICS")

    analytics = PerformanceAnalytics()
    report = analytics.generate_performance_report(
        state,
        state['capital']['initial_usd']
    )

    overview = report['overview']
    trade_metrics = report['trade_metrics']
    risk_metrics = report['risk_metrics']

    print(f"Trading Period:     {overview['trading_days']} days")
    print(f"Total Return:       {format_percent(overview['total_return_pct'])}")
    print()
    print(f"Total Trades:       {trade_metrics['total_trades']}")
    print(f"Win Rate:           {trade_metrics['win_rate']*100:.1f}%")
    print(f"Winning Trades:     {trade_metrics['winning_trades']}")
    print(f"Losing Trades:      {trade_metrics['losing_trades']}")
    print(f"Average Win:        {format_currency(trade_metrics['avg_win'])}")
    print(f"Average Loss:       {format_currency(trade_metrics['avg_loss'])}")
    print(f"Profit Factor:      {trade_metrics['profit_factor']:.2f}")
    print()
    print(f"Sharpe Ratio:       {risk_metrics['sharpe_ratio']:.2f}")
    print(f"Sortino Ratio:      {risk_metrics['sortino_ratio']:.2f}")
    print(f"Calmar Ratio:       {risk_metrics['calmar_ratio']:.2f}")
    print(f"Max Drawdown:       {format_percent(risk_metrics['max_drawdown_pct'])}")
    print(f"VaR (95%):          {risk_metrics['var_95']:.2f}%")


def print_strategies(state: Dict[str, Any]):
    """Print strategy information."""
    print_header("STRATEGIES")

    active = state['strategies'].get('active', [])
    research = state['strategies'].get('research', [])

    if not active:
        print("No active strategies")
    else:
        print(f"\nActive Strategies ({len(active)}):")
        print(f"{'Name':<20} {'Status':<12} {'Trades':>8} {'P&L':>15} {'Win Rate':>10}")
        print("-" * 80)

        for strat in active:
            name = strat['name']
            status = strat.get('status', 'unknown')
            perf = strat.get('performance', {})
            trades = perf.get('total_trades', 0)
            pnl = perf.get('pnl_usd', 0)
            win_rate = perf.get('win_rate', 0) * 100

            print(f"{name:<20} {status:<12} {trades:>8} {format_currency(pnl):>15} {win_rate:>9.1f}%")

    if research:
        print(f"\nStrategies in Research ({len(research)}):")
        for strat in research:
            print(f"  - {strat['name']}: {strat.get('status', 'unknown')}")


def print_recent_activity(state: Dict[str, Any], limit: int = 5):
    """Print recent trades and decisions."""
    print_header("RECENT ACTIVITY")

    trades = state.get('trade_history', [])
    decisions = state.get('decision_log', [])

    print(f"\nLast {limit} Trades:")
    if not trades:
        print("  No trades yet")
    else:
        for trade in trades[-limit:]:
            timestamp = trade['timestamp'][:19]
            symbol = trade['symbol']
            side = trade['side'].upper()
            size = trade['size']
            price = trade['price']
            pnl = trade.get('realized_pnl_usd', 0)

            print(f"  {timestamp} | {side:4} {size:.4f} {symbol:<12} @ ${price:,.2f} | "
                  f"P&L: {format_currency(pnl)}")

    print(f"\nLast {limit} Decisions:")
    if not decisions:
        print("  No decisions logged yet")
    else:
        for decision in decisions[-limit:]:
            timestamp = decision['timestamp'][:19]
            text = decision['decision'][:50]
            confidence = decision['confidence'] * 100

            print(f"  {timestamp} | [{confidence:>3.0f}%] {text}")


def print_risk_status(state: Dict[str, Any]):
    """Print risk limit utilization."""
    print_header("RISK STATUS")

    limits = state['risk_limits']
    capital = state['capital']
    positions = state.get('positions', [])

    # Position count utilization
    max_positions = limits['max_total_positions']
    current_positions = len(positions)
    position_util = current_positions / max_positions * 100

    # Capital allocation utilization
    max_alloc_pct = limits['max_total_allocated_pct']
    current_alloc_pct = capital['allocated_usd'] / capital['current_total_usd']
    alloc_util = current_alloc_pct / max_alloc_pct * 100

    # Daily loss
    max_daily_loss = limits['max_daily_loss_usd']

    print(f"Position Slots:     {current_positions}/{max_positions} ({position_util:.0f}%)")
    print(f"Capital Allocation: {current_alloc_pct*100:.1f}% / {max_alloc_pct*100:.0f}% ({alloc_util:.0f}%)")
    print(f"Daily Loss Limit:   {format_currency(max_daily_loss)}")
    print(f"Max Position Size:  {format_currency(limits['max_position_size_usd'])}")
    print(f"Max Leverage:       {limits['max_leverage']:.1f}x")

    # Emergency stop
    emergency_stop = state['system'].get('emergency_stop', False)
    print(f"\nEmergency Stop:     {'ACTIVE' if emergency_stop else 'Inactive'}")

    # Alerts
    alerts = state['system'].get('alerts', [])
    if alerts:
        print(f"\nActive Alerts ({len(alerts)}):")
        for alert in alerts[-5:]:
            print(f"  [{alert.get('severity', 'info').upper()}] {alert.get('message', 'Unknown')}")


def main():
    """Main monitor function."""
    try:
        state_manager = StateManager()
        state = state_manager.load()

        # Print all sections
        print_overview(state)
        print_positions(state)
        print_performance(state)
        print_strategies(state)
        print_risk_status(state)
        print_recent_activity(state)

        print()
        print("=" * 80)
        print()

    except FileNotFoundError:
        print("Error: State file not found. Have you initialized the firm?")
        print("Run: python scripts/initialize_firm.py --initial-capital 10000 --create-wallet")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
