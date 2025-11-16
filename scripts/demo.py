#!/usr/bin/env python3
"""
Demo script for Claude Capital - Autonomous AI Trading Firm

This script demonstrates the complete system working end-to-end with:
- Automatic firm initialization
- Mock exchange (paper trading)
- Multiple trading sessions
- Claude making autonomous decisions
- Performance analytics

Run this to see Claude Capital in action!
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.state import StateManager, initialize_state
from utils.logger import get_logger
from utils.analytics import PerformanceAnalytics
from trading.mock_exchange import MockExchangeConnector
from strategies import MomentumStrategy
from strategies.backtest import Backtester


def print_banner():
    """Print demo banner."""
    print("\n" + "=" * 80)
    print("  CLAUDE CAPITAL - AUTONOMOUS AI TRADING FIRM DEMO")
    print("  Powered by Claude Code")
    print("=" * 80 + "\n")


def cleanup_demo_state():
    """Clean up any previous demo state."""
    demo_state_path = Path("state/demo_firm_state.json")
    if demo_state_path.exists():
        demo_state_path.unlink()
        print("✓ Cleaned up previous demo state\n")


def demo_1_initialize_firm():
    """Demo 1: Initialize the trading firm."""
    print("=" * 80)
    print("DEMO 1: Initializing Claude Capital")
    print("=" * 80 + "\n")

    print("Creating a new autonomous trading firm with:")
    print("  - Name: Claude Capital Demo")
    print("  - Initial Capital: $10,000")
    print("  - Exchange: Mock (Paper Trading)")
    print("  - Risk Limits: Conservative")
    print()

    # Initialize state
    state = initialize_state(
        name="Claude Capital Demo",
        initial_capital_usd=10000.0,
        wallet_address="0x" + "0" * 40,  # Demo wallet
        chain="ethereum",
        state_path="state/demo_firm_state.json"
    )

    print("✓ Firm initialized successfully!")
    print(f"  State file: state/demo_firm_state.json")
    print(f"  Inception: {state['firm']['inception_date'][:19]}")
    print()

    input("Press Enter to continue to Demo 2...")
    return state


def demo_2_backtest_strategy():
    """Demo 2: Backtest a trading strategy."""
    print("\n" + "=" * 80)
    print("DEMO 2: Backtesting Momentum Strategy")
    print("=" * 80 + "\n")

    print("Testing the momentum strategy on historical data...")
    print()

    # Create mock exchange with data
    exchange = MockExchangeConnector(initial_balance=10000)

    # Get historical data (500 hourly candles = ~21 days)
    print("Generating 21 days of historical price data...")
    ohlcv_data = exchange.get_ohlcv('BTC/USDT', '1h', limit=500)
    print(f"✓ Generated {len(ohlcv_data)} candles")
    print()

    # Create and backtest strategy
    print("Creating Momentum Strategy with parameters:")
    strategy = MomentumStrategy(params={
        "fast_ma_period": 10,
        "slow_ma_period": 30,
        "roc_threshold": 2.0,
        "take_profit_pct": 5.0,
        "stop_loss_pct": 2.0
    })
    print(f"  - Fast MA: 10 periods")
    print(f"  - Slow MA: 30 periods")
    print(f"  - ROC Threshold: 2.0%")
    print(f"  - Take Profit: 5.0%")
    print(f"  - Stop Loss: 2.0%")
    print()

    print("Running backtest...")
    backtester = Backtester(initial_capital=10000, commission=0.001)
    results = backtester.run(
        strategy=strategy,
        symbol='BTC/USDT',
        ohlcv_data=ohlcv_data,
        position_size_pct=0.10  # 10% of capital per trade
    )

    # Print results
    backtester.print_results(results)

    print(f"Strategy Performance:")
    print(f"  Win Rate: {results['win_rate']*100:.1f}%")
    print(f"  Total Trades: {results['total_trades']}")
    print(f"  Final Capital: ${results['final_capital']:,.2f}")
    print(f"  Return: {results['total_return_pct']:+.2f}%")
    print()

    input("Press Enter to continue to Demo 3...")
    return results


def demo_3_paper_trading():
    """Demo 3: Demonstrate paper trading."""
    print("\n" + "=" * 80)
    print("DEMO 3: Paper Trading with Mock Exchange")
    print("=" * 80 + "\n")

    print("Now let's see the system make actual trades (paper trading)...")
    print()

    # Load state
    state_manager = StateManager("state/demo_firm_state.json")
    state = state_manager.load()

    # Create mock exchange
    exchange = MockExchangeConnector(initial_balance=10000)

    print("Current State:")
    print(f"  Capital: ${state['capital']['current_total_usd']:,.2f}")
    print(f"  Positions: {len(state['positions'])}")
    print()

    print("Executing a few demo trades...\n")

    # Simulate some trades
    trades = [
        ("BTC/USDT", "buy", 0.05, "Momentum entry signal"),
        ("ETH/USDT", "buy", 0.5, "Breakout detected"),
    ]

    for symbol, side, size, reason in trades:
        price = exchange.get_current_price(symbol)
        print(f"Trade: {side.upper()} {size} {symbol} @ ${price:,.2f}")
        print(f"  Reason: {reason}")

        # Execute trade
        order = exchange.create_market_order(symbol, side, size)

        # Add to state
        if side == "buy":
            position_id = f"demo_pos_{len(state['positions'])}"
            position = {
                "id": position_id,
                "symbol": symbol,
                "exchange": "mock",
                "side": "long",
                "size": size,
                "entry_price": price,
                "current_price": price,
                "unrealized_pnl_usd": 0,
                "entry_timestamp": datetime.utcnow().isoformat(),
                "strategy_name": "demo",
                "notes": reason
            }
            state_manager.add_position(position)

        print(f"  ✓ Executed: Order ID {order['id']}")
        print()
        time.sleep(1)

    state = state_manager.load()
    print(f"After trades:")
    print(f"  Open Positions: {len(state['positions'])}")
    print(f"  Position 1: {state['positions'][0]['symbol']} - {state['positions'][0]['size']} @ ${state['positions'][0]['entry_price']:,.2f}")
    if len(state['positions']) > 1:
        print(f"  Position 2: {state['positions'][1]['symbol']} - {state['positions'][1]['size']} @ ${state['positions'][1]['entry_price']:,.2f}")
    print()

    input("Press Enter to continue to Demo 4...")


def demo_4_analytics():
    """Demo 4: Show performance analytics."""
    print("\n" + "=" * 80)
    print("DEMO 4: Performance Analytics")
    print("=" * 80 + "\n")

    print("Claude Capital includes comprehensive performance analytics:\n")

    # Load state
    state_manager = StateManager("state/demo_firm_state.json")
    state = state_manager.load()

    # Generate analytics
    analytics = PerformanceAnalytics()

    # Add some mock trade history for demo
    mock_trades = [
        {"realized_pnl_usd": 50, "cost": 1000, "timestamp": datetime.utcnow().isoformat()},
        {"realized_pnl_usd": -20, "cost": 1000, "timestamp": datetime.utcnow().isoformat()},
        {"realized_pnl_usd": 75, "cost": 1000, "timestamp": datetime.utcnow().isoformat()},
        {"realized_pnl_usd": 30, "cost": 1000, "timestamp": datetime.utcnow().isoformat()},
        {"realized_pnl_usd": -10, "cost": 1000, "timestamp": datetime.utcnow().isoformat()},
    ]

    state['trade_history'] = mock_trades

    # Calculate metrics
    returns = analytics.calculate_returns(mock_trades)
    sharpe = analytics.calculate_sharpe_ratio(returns) if len(returns) > 1 else 0
    win_metrics = analytics.calculate_win_rate(mock_trades)

    print("Available Metrics:")
    print(f"  ✓ Sharpe Ratio: {sharpe:.2f}")
    print(f"  ✓ Sortino Ratio (downside risk only)")
    print(f"  ✓ Maximum Drawdown")
    print(f"  ✓ Win Rate: {win_metrics['win_rate']*100:.1f}%")
    print(f"  ✓ Profit Factor: {win_metrics['profit_factor']:.2f}")
    print(f"  ✓ VaR (Value at Risk)")
    print(f"  ✓ CVaR (Conditional VaR)")
    print(f"  ✓ Calmar Ratio")
    print()

    print("Trade Metrics:")
    print(f"  Total Trades: {win_metrics['total_trades']}")
    print(f"  Winning Trades: {win_metrics['winning_trades']}")
    print(f"  Losing Trades: {win_metrics['losing_trades']}")
    print(f"  Average Win: ${win_metrics['avg_win']:.2f}")
    print(f"  Average Loss: ${win_metrics['avg_loss']:.2f}")
    print()

    input("Press Enter to continue to Demo 5...")


def demo_5_monitoring():
    """Demo 5: Show monitoring capabilities."""
    print("\n" + "=" * 80)
    print("DEMO 5: Monitoring Dashboard")
    print("=" * 80 + "\n")

    print("Claude Capital includes a real-time monitoring dashboard:")
    print()
    print("  Run: python scripts/monitor.py")
    print()
    print("The dashboard shows:")
    print("  ✓ Overview (capital, P&L, returns)")
    print("  ✓ Open Positions with unrealized P&L")
    print("  ✓ Performance Metrics (Sharpe, win rate, etc.)")
    print("  ✓ Active Strategies")
    print("  ✓ Risk Status (limit utilization)")
    print("  ✓ Recent Activity (trades and decisions)")
    print()

    print("You can also run it in watch mode:")
    print("  watch -n 30 python scripts/monitor.py")
    print()

    input("Press Enter to continue to Demo 6...")


def demo_6_autonomous_loop():
    """Demo 6: Explain the autonomous loop."""
    print("\n" + "=" * 80)
    print("DEMO 6: Autonomous Trading Loop")
    print("=" * 80 + "\n")

    print("How Claude Capital operates autonomously:\n")

    print("1. SCHEDULED EXECUTION")
    print("   Every 30 minutes (configurable), the system:")
    print("   - Loads current state")
    print("   - Updates positions with live prices")
    print("   - Checks safety conditions")
    print()

    print("2. CLAUDE CODE SESSION")
    print("   Claude is invoked with full context:")
    print("   - Current capital and P&L")
    print("   - Open positions")
    print("   - Strategy performance")
    print("   - Priorities from last session")
    print()

    print("3. AUTONOMOUS DECISION MAKING")
    print("   Claude uses available tools to:")
    print("   - Get market data and prices")
    print("   - Analyze technical indicators")
    print("   - Research market conditions")
    print("   - Execute trades (with risk validation)")
    print("   - Update strategies")
    print("   - Log decisions with reasoning")
    print()

    print("4. STATE PERSISTENCE")
    print("   After each session:")
    print("   - All state changes are saved")
    print("   - Priorities set for next session")
    print("   - Complete audit trail maintained")
    print()

    print("5. SAFETY & RISK MANAGEMENT")
    print("   Every trade is validated against:")
    print("   - Position size limits")
    print("   - Capital allocation limits")
    print("   - Daily loss circuit breaker")
    print("   - Emergency stop flag")
    print()

    input("Press Enter to see the summary...")


def demo_summary():
    """Print demo summary."""
    print("\n" + "=" * 80)
    print("DEMO COMPLETE!")
    print("=" * 80 + "\n")

    print("🎉 You've seen Claude Capital in action!\n")

    print("What you learned:")
    print("  ✓ System initialization")
    print("  ✓ Strategy backtesting")
    print("  ✓ Paper trading (mock exchange)")
    print("  ✓ Performance analytics")
    print("  ✓ Monitoring tools")
    print("  ✓ Autonomous loop operation")
    print()

    print("What's included:")
    print("  ✓ Full Claude Code integration")
    print("  ✓ Mock exchange for safe testing")
    print("  ✓ Momentum trading strategy")
    print("  ✓ Comprehensive unit tests")
    print("  ✓ Performance analytics (Sharpe, VaR, etc.)")
    print("  ✓ Monitoring dashboard")
    print("  ✓ Backtesting framework")
    print("  ✓ Research integration")
    print()

    print("Next steps:")
    print("  1. Review the code in src/")
    print("  2. Run tests: pytest")
    print("  3. Try: python src/loop.py (requires ANTHROPIC_API_KEY)")
    print("  4. Monitor: python scripts/monitor.py")
    print("  5. Customize strategies in src/strategies/")
    print()

    print("Documentation:")
    print("  - ARCHITECTURE.md: System design")
    print("  - SETUP_GUIDE.md: Setup instructions")
    print("  - ROADMAP.md: Future development")
    print("  - ENHANCEMENTS.md: Features overview")
    print()

    print("⚠️  Remember:")
    print("  - This demo used mock exchange (paper trading)")
    print("  - Add real API keys only when ready")
    print("  - Start with small capital when going live")
    print("  - Monitor closely initially")
    print()

    print("=" * 80)
    print("Built with Claude Code | Autonomous AI Trading")
    print("=" * 80 + "\n")


def main():
    """Run the complete demo."""
    try:
        print_banner()

        print("This demo will show you:\n")
        print("  1. Firm Initialization")
        print("  2. Strategy Backtesting")
        print("  3. Paper Trading")
        print("  4. Performance Analytics")
        print("  5. Monitoring Dashboard")
        print("  6. Autonomous Loop")
        print()

        response = input("Ready to begin? (y/n): ")
        if response.lower() != 'y':
            print("Demo cancelled.")
            return

        # Clean up previous demo state
        cleanup_demo_state()

        # Run demos
        demo_1_initialize_firm()
        demo_2_backtest_strategy()
        demo_3_paper_trading()
        demo_4_analytics()
        demo_5_monitoring()
        demo_6_autonomous_loop()
        demo_summary()

        # Cleanup
        print("Clean up demo state? (y/n): ", end="")
        if input().lower() == 'y':
            cleanup_demo_state()
            print("✓ Demo state cleaned up")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Exiting...")
    except Exception as e:
        print(f"\nError in demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
