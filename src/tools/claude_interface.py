"""
Claude Code integration for trading decisions.

This module handles the interface between the trading loop and Claude,
providing tools for market analysis, trade execution, and research.
"""

import os
from typing import Dict, List, Any, Optional
from anthropic import Anthropic
from datetime import datetime
import uuid


class TradingTools:
    """Trading tools available to Claude."""

    def __init__(self, state_manager, exchange_manager, risk_validator, logger):
        """
        Initialize trading tools.

        Args:
            state_manager: StateManager instance
            exchange_manager: ExchangeManager instance
            risk_validator: RiskValidator instance
            logger: Logger instance
        """
        self.state_manager = state_manager
        self.exchange_manager = exchange_manager
        self.risk_validator = risk_validator
        self.logger = logger
        self.actions_taken = []

    def get_current_price(self, symbol: str, exchange: str = "binance") -> Dict[str, Any]:
        """Get current price for a trading pair."""
        try:
            exchange_conn = self.exchange_manager.get_exchange(exchange)
            if not exchange_conn:
                return {"error": f"Exchange {exchange} not connected"}

            price = exchange_conn.get_current_price(symbol)
            return {
                "symbol": symbol,
                "price": price,
                "exchange": exchange,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return {"error": str(e)}

    def get_market_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
        exchange: str = "binance"
    ) -> Dict[str, Any]:
        """Get OHLCV market data."""
        try:
            exchange_conn = self.exchange_manager.get_exchange(exchange)
            if not exchange_conn:
                return {"error": f"Exchange {exchange} not connected"}

            ohlcv = exchange_conn.get_ohlcv(symbol, timeframe, limit)

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "data_points": len(ohlcv),
                "data": ohlcv,  # [[timestamp, open, high, low, close, volume], ...]
                "latest_close": ohlcv[-1][4] if ohlcv else None
            }
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return {"error": str(e)}

    def execute_trade(
        self,
        symbol: str,
        side: str,
        size: float,
        order_type: str = "market",
        price: Optional[float] = None,
        exchange: str = "binance",
        strategy: str = "manual"
    ) -> Dict[str, Any]:
        """
        Execute a trade with full risk validation.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: 'buy' or 'sell'
            size: Order size
            order_type: 'market' or 'limit'
            price: Limit price (required for limit orders)
            exchange: Exchange to use
            strategy: Strategy name for tracking

        Returns:
            Trade result
        """
        try:
            # Get current state
            state = self.state_manager.load()

            # Get current price if not provided
            if price is None:
                price_data = self.get_current_price(symbol, exchange)
                if "error" in price_data:
                    return price_data
                price = price_data['price']

            # Validate trade
            is_valid, error_msg = self.risk_validator.validate_trade(
                symbol, side, size, price, state
            )

            if not is_valid:
                self.logger.warning(f"Trade rejected: {error_msg}")
                return {
                    "status": "rejected",
                    "reason": error_msg
                }

            # Execute trade on exchange
            exchange_conn = self.exchange_manager.get_exchange(exchange)
            if not exchange_conn:
                return {"error": f"Exchange {exchange} not connected"}

            if order_type == "market":
                order = exchange_conn.create_market_order(symbol, side, size)
            elif order_type == "limit":
                if price is None:
                    return {"error": "Price required for limit orders"}
                order = exchange_conn.create_limit_order(symbol, side, size, price)
            else:
                return {"error": f"Unknown order type: {order_type}"}

            # Create trade record
            trade_id = f"trade_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            trade_record = {
                "id": trade_id,
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": order['price'],
                "fees_usd": order.get('fee', {}).get('cost', 0),
                "exchange": exchange,
                "strategy": strategy,
                "order_id": order['id']
            }

            # Add to trade history
            self.state_manager.add_trade(trade_record)

            # Update positions
            if side == "buy":
                # Open new position
                position_id = f"pos_{uuid.uuid4().hex[:8]}"
                position = {
                    "id": position_id,
                    "symbol": symbol,
                    "exchange": exchange,
                    "side": "long",
                    "size": size,
                    "entry_price": order['price'],
                    "current_price": order['price'],
                    "unrealized_pnl_usd": 0,
                    "entry_timestamp": datetime.utcnow().isoformat(),
                    "strategy_name": strategy,
                    "notes": f"Opened via {order_type} order"
                }
                self.state_manager.add_position(position)

            elif side == "sell":
                # Close position (simplified - matches by symbol)
                state = self.state_manager.load()
                for pos in state['positions']:
                    if pos['symbol'] == symbol and pos['side'] == 'long':
                        # Calculate realized P&L
                        realized_pnl = size * (order['price'] - pos['entry_price'])

                        # Remove position
                        self.state_manager.remove_position(pos['id'])

                        # Update trade record with P&L
                        trade_record['realized_pnl_usd'] = realized_pnl

                        break

            # Log trade
            self.logger.trade(trade_record)
            self.actions_taken.append(f"executed_trade_{side}_{symbol}")

            return {
                "status": "success",
                "trade_id": trade_id,
                "order": order,
                "trade": trade_record
            }

        except Exception as e:
            self.logger.error(f"Error executing trade: {e}", exc_info=True)
            return {"error": str(e)}

    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze current trading performance."""
        try:
            state = self.state_manager.load()
            return {
                "summary": self.state_manager.get_performance_summary(),
                "recent_trades": state['trade_history'][-10:],
                "active_strategies": state['strategies']['active'],
                "risk_metrics": {
                    "max_drawdown": state['performance'].get('max_drawdown_usd', 0),
                    "sharpe_ratio": state['performance'].get('sharpe_ratio', 0),
                    "win_rate": state['performance'].get('win_rate', 0)
                }
            }
        except Exception as e:
            self.logger.error(f"Error analyzing performance: {e}")
            return {"error": str(e)}

    def log_decision(self, decision: str, reasoning: str, confidence: float = 0.5) -> Dict[str, str]:
        """Log a trading decision."""
        try:
            self.state_manager.add_decision(decision, reasoning, confidence)
            self.logger.decision(decision, reasoning, confidence)
            self.actions_taken.append(f"logged_decision")
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"Error logging decision: {e}")
            return {"error": str(e)}

    def research_topic(self, topic: str) -> Dict[str, Any]:
        """
        Research a topic using web search and analysis.

        Args:
            topic: Research topic

        Returns:
            Research findings
        """
        self.logger.info(f"Research request: {topic}")
        self.actions_taken.append(f"researched_{topic[:30]}")

        try:
            from tools.research import ResearchTools
            research_tools = ResearchTools()
            findings = research_tools.research_topic(topic)

            # Log research note
            self.state_manager.add_research_note(
                topic=topic,
                findings=str(findings.get('sentiment', {}) if 'sentiment' in findings else findings)[:500],
                action_taken="Conducted web research"
            )

            return findings

        except Exception as e:
            self.logger.error(f"Error conducting research: {e}")
            return {
                "topic": topic,
                "error": str(e),
                "suggestion": "Check TAVILY_API_KEY in .env for web search capabilities"
            }


class ClaudeSession:
    """Manages a Claude Code trading session."""

    def __init__(self, state_manager, logger):
        """
        Initialize Claude session.

        Args:
            state_manager: StateManager instance
            logger: Logger instance
        """
        self.state_manager = state_manager
        self.logger = logger

        # Initialize Anthropic client
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=api_key)

        # Initialize exchange manager
        from trading.exchanges import ExchangeManager
        self.exchange_manager = ExchangeManager(
            testnet=os.getenv('ENVIRONMENT') != 'production'
        )

        # Add configured exchanges
        if os.getenv('BINANCE_API_KEY'):
            self.exchange_manager.add_exchange('binance')

        # Initialize risk validator
        state = self.state_manager.load()
        from trading.risk import RiskValidator
        self.risk_validator = RiskValidator(state['risk_limits'])

        # Initialize trading tools
        self.tools = TradingTools(
            state_manager=self.state_manager,
            exchange_manager=self.exchange_manager,
            risk_validator=self.risk_validator,
            logger=self.logger
        )

    def run(self, context: str) -> Dict[str, Any]:
        """
        Run a Claude trading session with full tool calling.

        Args:
            context: Context/prompt for Claude

        Returns:
            Session result with actions and next priorities
        """
        self.logger.info("Starting Claude session...")
        self.logger.info("=" * 80)

        # Initialize conversation
        messages = [{"role": "user", "content": context}]

        max_turns = 15  # Prevent infinite loops
        turn_count = 0

        try:
            while turn_count < max_turns:
                turn_count += 1
                self.logger.info(f"Turn {turn_count}/{max_turns}")

                # Call Claude with tools
                response = self.client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=8000,
                    messages=messages,
                    tools=TRADING_TOOLS,
                    temperature=1.0
                )

                # Add assistant response to conversation
                assistant_content = response.content
                messages.append({
                    "role": "assistant",
                    "content": assistant_content
                })

                # Check if Claude wants to use tools
                tool_use_blocks = [
                    block for block in response.content
                    if hasattr(block, 'type') and block.type == "tool_use"
                ]

                if not tool_use_blocks:
                    # Claude is done, extract final response
                    self.logger.info("Claude session complete")

                    # Extract text content
                    text_blocks = [
                        block.text for block in response.content
                        if hasattr(block, 'type') and block.type == "text"
                    ]
                    final_text = "\n".join(text_blocks)

                    # Log Claude's final thoughts
                    self.logger.info("=" * 80)
                    self.logger.info("CLAUDE'S FINAL RESPONSE:")
                    self.logger.info(final_text)
                    self.logger.info("=" * 80)

                    # Extract next priorities
                    next_priorities = self._extract_priorities(final_text)

                    return {
                        "actions": self.tools.actions_taken,
                        "next_priorities": next_priorities,
                        "final_response": final_text,
                        "turns": turn_count
                    }

                # Execute tools
                self.logger.info(f"Claude requested {len(tool_use_blocks)} tool(s)")
                tool_results = []

                for tool_use in tool_use_blocks:
                    tool_name = tool_use.name
                    tool_input = tool_use.input
                    tool_use_id = tool_use.id

                    self.logger.info(f"Executing tool: {tool_name}")
                    self.logger.debug(f"  Input: {tool_input}")

                    # Execute the tool
                    result = self._execute_tool(tool_name, tool_input)

                    self.logger.info(f"  Result: {str(result)[:200]}...")

                    # Add tool result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": str(result)
                    })

                # Add tool results to conversation
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

            # Max turns reached
            self.logger.warning(f"Max turns ({max_turns}) reached, ending session")
            return {
                "actions": self.tools.actions_taken,
                "next_priorities": ["Continue analysis from previous session"],
                "final_response": "Session ended (max turns reached)",
                "turns": turn_count
            }

        except Exception as e:
            self.logger.error(f"Error in Claude session: {e}", exc_info=True)
            return {
                "actions": self.tools.actions_taken,
                "next_priorities": ["Investigate session error and retry"],
                "error": str(e),
                "turns": turn_count
            }

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """
        Execute a trading tool.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters

        Returns:
            Tool execution result
        """
        tool_map = {
            "get_current_price": self.tools.get_current_price,
            "get_market_data": self.tools.get_market_data,
            "execute_trade": self.tools.execute_trade,
            "analyze_performance": self.tools.analyze_performance,
            "log_decision": self.tools.log_decision,
            "research_topic": self.tools.research_topic
        }

        tool_func = tool_map.get(tool_name)
        if not tool_func:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return tool_func(**tool_input)
        except Exception as e:
            self.logger.error(f"Error executing {tool_name}: {e}")
            return {"error": str(e)}

    def _extract_priorities(self, text: str) -> List[str]:
        """
        Extract next priorities from Claude's response.

        Args:
            text: Claude's final response text

        Returns:
            List of priorities
        """
        priorities = []

        # Look for common patterns
        lines = text.split('\n')
        in_priorities_section = False

        for line in lines:
            line = line.strip()

            # Check for priority section headers
            if any(keyword in line.lower() for keyword in [
                'next priority', 'next session', 'priorities for next',
                'next steps', 'for next time', 'next iteration'
            ]):
                in_priorities_section = True
                continue

            # Extract numbered or bulleted items
            if in_priorities_section and line:
                # Remove common prefixes
                for prefix in ['- ', '* ', '• ']:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                        break

                # Remove numbering (1. 2. etc)
                if line and line[0].isdigit() and len(line) > 2 and line[1] in '.):':
                    line = line[2:].strip()

                if line and len(line) > 10:  # Reasonable priority length
                    priorities.append(line)

                    if len(priorities) >= 5:  # Max 5 priorities
                        break

            # Stop if we hit another section
            if in_priorities_section and line.startswith('#'):
                break

        # Default priorities if none found
        if not priorities:
            priorities = [
                "Monitor current market conditions",
                "Analyze portfolio performance",
                "Research new trading opportunities"
            ]

        return priorities[:5]  # Max 5 priorities


# Tool definitions for Claude API (when using actual Claude Code integration)
TRADING_TOOLS = [
    {
        "name": "get_current_price",
        "description": "Get the current price for a trading pair",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Trading pair (e.g., 'BTC/USDT')"
                },
                "exchange": {
                    "type": "string",
                    "description": "Exchange name (default: 'binance')"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_market_data",
        "description": "Get OHLCV market data for analysis",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Trading pair"
                },
                "timeframe": {
                    "type": "string",
                    "description": "Timeframe (1m, 5m, 1h, 4h, 1d, etc.)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of candles to fetch"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "execute_trade",
        "description": "Execute a trade (buy or sell). This will be validated against risk limits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Trading pair"
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Buy or sell"
                },
                "size": {
                    "type": "number",
                    "description": "Order size"
                },
                "order_type": {
                    "type": "string",
                    "enum": ["market", "limit"],
                    "description": "Order type"
                },
                "strategy": {
                    "type": "string",
                    "description": "Strategy name for tracking"
                }
            },
            "required": ["symbol", "side", "size"]
        }
    },
    {
        "name": "analyze_performance",
        "description": "Get current trading performance metrics",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "log_decision",
        "description": "Log a trading decision with reasoning",
        "input_schema": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "description": "The decision made"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of the decision"
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence level (0-1)"
                }
            },
            "required": ["decision", "reasoning"]
        }
    }
]
