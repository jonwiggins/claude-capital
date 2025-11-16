#!/usr/bin/env python3
"""
Main execution loop for Claude Capital.

This script is the entry point for each trading session. It:
1. Loads the current firm state
2. Performs safety checks
3. Invokes Claude Code with trading context and tools
4. Saves updated state
5. Logs session activities

This script is designed to be called periodically (e.g., every 30 minutes)
by a scheduler like cron or systemd timer.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from utils.state import StateManager
from utils.logger import get_logger
from trading.exchanges import ExchangeManager
from trading.risk import CircuitBreaker
from tools.claude_interface import ClaudeSession

# Load environment variables
load_dotenv()


class TradingLoop:
    """Main trading loop executor."""

    def __init__(self):
        """Initialize the trading loop."""
        self.logger = get_logger()
        self.state_manager = StateManager()
        self.circuit_breaker = CircuitBreaker(self.state_manager)
        self.session_start_time = time.time()
        self.actions_taken = []
        self.errors = []

    def run(self) -> int:
        """
        Execute one trading session.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            self.logger.session_start()

            # Step 1: Load state
            self.logger.info("Loading firm state...")
            state = self.state_manager.load()

            # Step 2: Check emergency stop
            if state['system'].get('emergency_stop', False):
                self.logger.warning("EMERGENCY STOP ACTIVE - Trading halted")
                return 0

            # Step 3: Check circuit breaker
            should_trip, reason = self.circuit_breaker.check(state)
            if should_trip:
                self.logger.error(f"Circuit breaker tripped: {reason}")
                self.circuit_breaker.trip(reason)
                return 1

            # Step 4: Update current state
            self.logger.info("Updating current state...")
            updated_state = self._update_state(state)

            # Step 5: Prepare context for Claude
            self.logger.info("Preparing Claude context...")
            context = self._prepare_claude_context(updated_state)

            # Step 6: Invoke Claude Code session
            self.logger.info("Invoking Claude Code session...")
            session = ClaudeSession(
                state_manager=self.state_manager,
                logger=self.logger
            )

            result = session.run(context)

            # Step 7: Save state
            self.logger.info("Saving state...")
            self.state_manager.save(updated_state)

            # Step 8: Log session
            duration = time.time() - self.session_start_time
            next_priorities = result.get('next_priorities', [])

            self.state_manager.log_session(
                actions=result.get('actions', []),
                errors=self.errors,
                next_priorities=next_priorities,
                duration=duration
            )

            # Summary
            summary = {
                "duration": f"{duration:.1f}s",
                "actions": len(result.get('actions', [])),
                "trades": len([a for a in result.get('actions', []) if 'trade' in a.lower()]),
                "capital": f"${updated_state['capital']['current_total_usd']:.2f}",
                "positions": len(updated_state['positions'])
            }

            self.logger.session_end(summary)

            return 0

        except KeyboardInterrupt:
            self.logger.warning("Session interrupted by user")
            return 130

        except Exception as e:
            self.logger.error(f"Fatal error in trading loop: {e}", exc_info=True)
            self.errors.append(str(e))
            return 1

    def _update_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update state with current market data.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        try:
            # Initialize exchange manager
            exchange_manager = ExchangeManager(testnet=os.getenv('ENVIRONMENT') != 'production')

            # Add configured exchanges
            if os.getenv('BINANCE_API_KEY'):
                exchange_manager.add_exchange('binance')

            # Update position prices and unrealized P&L
            for position in state['positions']:
                try:
                    exchange_name = position.get('exchange', 'binance')
                    exchange = exchange_manager.get_exchange(exchange_name)

                    if exchange:
                        current_price = exchange.get_current_price(position['symbol'])
                        position['current_price'] = current_price

                        # Calculate unrealized P&L
                        size = position['size']
                        entry_price = position['entry_price']

                        if position['side'] == 'long':
                            unrealized_pnl = size * (current_price - entry_price)
                        else:
                            unrealized_pnl = size * (entry_price - current_price)

                        position['unrealized_pnl_usd'] = unrealized_pnl

                except Exception as e:
                    self.logger.warning(f"Failed to update position {position['id']}: {e}")

            # Update capital allocation
            total_allocated = sum(
                pos['size'] * pos['current_price']
                for pos in state['positions']
            )
            state['capital']['allocated_usd'] = total_allocated

            # Get total portfolio value (exchange balances)
            try:
                total_exchange_value = exchange_manager.get_total_value_usd()
                state['capital']['current_total_usd'] = total_exchange_value
            except Exception as e:
                self.logger.warning(f"Failed to get total portfolio value: {e}")

            # Calculate liquid capital
            state['capital']['liquid_usd'] = (
                state['capital']['current_total_usd'] -
                state['capital']['allocated_usd']
            )

            # Update total P&L
            initial_capital = state['capital']['initial_usd']
            current_capital = state['capital']['current_total_usd']
            state['performance']['total_pnl_usd'] = current_capital - initial_capital

        except Exception as e:
            self.logger.error(f"Error updating state: {e}", exc_info=True)
            self.errors.append(f"State update error: {e}")

        return state

    def _prepare_claude_context(self, state: Dict[str, Any]) -> str:
        """
        Prepare context/prompt for Claude.

        Args:
            state: Current state

        Returns:
            Context string
        """
        # Get last session priorities
        last_priorities = []
        if state['session_log']:
            last_session = state['session_log'][-1]
            last_priorities = last_session.get('next_priorities', [])

        # Calculate risk utilization
        max_positions = state['risk_limits']['max_total_positions']
        position_utilization = len(state['positions']) / max_positions if max_positions > 0 else 0

        max_allocation_pct = state['risk_limits']['max_total_allocated_pct']
        allocation_pct = state['capital']['allocated_usd'] / state['capital']['current_total_usd']
        allocation_utilization = allocation_pct / max_allocation_pct if max_allocation_pct > 0 else 0

        # Build context
        context = f"""You are Claude Capital, an autonomous AI trading firm.

CURRENT STATE:
- Total Capital: ${state['capital']['current_total_usd']:.2f} (${state['performance']['total_pnl_usd']:+.2f} from initial)
- Liquid Capital: ${state['capital']['liquid_usd']:.2f}
- Allocated Capital: ${state['capital']['allocated_usd']:.2f} ({allocation_pct:.1%} of total)
- Open Positions: {len(state['positions'])} (max: {max_positions})
- Active Strategies: {len(state['strategies']['active'])}
- Total Trades: {state['performance']['total_trades']}
- Win Rate: {state['performance']['win_rate']:.1%}
- Total P&L: ${state['performance']['total_pnl_usd']:+.2f}

OPEN POSITIONS:
"""

        if state['positions']:
            for pos in state['positions']:
                pnl_pct = ((pos['current_price'] / pos['entry_price']) - 1) * 100
                context += f"- {pos['symbol']}: {pos['side']} {pos['size']:.4f} @ ${pos['entry_price']:.2f} "
                context += f"(current: ${pos['current_price']:.2f}, P&L: ${pos['unrealized_pnl_usd']:+.2f} / {pnl_pct:+.2f}%)\n"
        else:
            context += "None\n"

        context += f"""
ACTIVE STRATEGIES:
"""

        if state['strategies']['active']:
            for strategy in state['strategies']['active']:
                context += f"- {strategy['name']}: {strategy['status']}, "
                context += f"P&L: ${strategy['performance'].get('pnl_usd', 0):+.2f}, "
                context += f"Trades: {strategy['performance'].get('total_trades', 0)}\n"
        else:
            context += "None - You should develop and deploy your first strategy!\n"

        context += f"""
RISK UTILIZATION:
- Position Slots: {len(state['positions'])}/{max_positions} ({position_utilization:.0%})
- Capital Allocation: {allocation_utilization:.0%} of maximum
- Daily Loss Limit: ${state['risk_limits']['max_daily_loss_usd']:.2f}
- Max Position Size: ${state['risk_limits']['max_position_size_usd']:.2f}

RECENT RESEARCH:
"""

        if state['research_log']:
            for research in state['research_log'][-3:]:
                context += f"- {research['topic']}: {research['findings'][:100]}...\n"
        else:
            context += "None yet\n"

        context += f"""
LAST SESSION PRIORITIES:
"""

        if last_priorities:
            for i, priority in enumerate(last_priorities, 1):
                context += f"{i}. {priority}\n"
        else:
            context += "This is your first session!\n"

        context += """
YOUR TASK:
As the autonomous trading AI for Claude Capital, you should:

1. ANALYZE: Review current positions and their performance
2. RESEARCH: Investigate trading opportunities and market conditions
3. DECIDE: Make trading decisions based on your analysis
4. EXECUTE: Place trades, update strategies, or close positions as needed
5. PLAN: Set priorities for your next session

You have full autonomy within the defined risk limits. Use your trading tools to:
- Get market data and analyze price action
- Execute trades (buy/sell)
- Research market conditions
- Develop and deploy trading strategies
- Log your decisions with clear reasoning

Remember:
- Every decision should have clear reasoning
- Consider risk-adjusted returns
- Test strategies before deploying significant capital
- Set clear priorities for your next session
- Learn from past trades and decisions

Available tools:
- get_market_data(symbol, timeframe): Get OHLCV data
- get_current_price(symbol): Get latest price
- execute_trade(symbol, side, size): Execute a trade
- analyze_performance(): Review your trading performance
- research_topic(topic): Research trading opportunities
- log_decision(decision, reasoning): Document your decisions

Take your time to think through the current situation and make informed decisions.
"""

        return context


def main():
    """Main entry point."""
    loop = TradingLoop()
    exit_code = loop.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
