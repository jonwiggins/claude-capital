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
        Research a topic (placeholder for now).

        In production, this could integrate with web search, news APIs, etc.
        """
        self.logger.info(f"Research request: {topic}")
        self.actions_taken.append(f"researched_{topic[:30]}")

        # For now, return a placeholder
        return {
            "topic": topic,
            "findings": "Research functionality to be implemented. "
                       "Consider using web search, news APIs, or on-chain data.",
            "sources": []
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
        Run a Claude trading session.

        Args:
            context: Context/prompt for Claude

        Returns:
            Session result
        """
        self.logger.info("Starting Claude session...")

        # For now, return a simulated response
        # In production, this would invoke Claude API with tool use
        self.logger.info("=" * 80)
        self.logger.info("CLAUDE CONTEXT:")
        self.logger.info(context)
        self.logger.info("=" * 80)

        # Simulate Claude thinking
        self.logger.info("Claude is analyzing the trading situation...")

        # Example: Claude could analyze markets, make trades, etc.
        # For now, just return placeholder actions
        result = {
            "actions": self.tools.actions_taken,
            "next_priorities": [
                "Monitor market conditions for entry opportunities",
                "Research correlation between BTC and major indices",
                "Develop momentum-based trading strategy"
            ]
        }

        return result


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
