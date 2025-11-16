"""
Exchange connectivity for Claude Capital.

Provides a unified interface to multiple cryptocurrency exchanges using ccxt.
Handles order execution, market data fetching, and position management.
"""

import os
import ccxt
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal


class ExchangeConnector:
    """Unified interface to cryptocurrency exchanges."""

    def __init__(self, exchange_name: str = "binance", testnet: bool = False):
        """
        Initialize exchange connector.

        Args:
            exchange_name: Name of the exchange (binance, coinbase, kraken, etc.)
            testnet: Whether to use testnet/sandbox mode
        """
        self.exchange_name = exchange_name.lower()
        self.testnet = testnet

        # Initialize exchange
        exchange_class = getattr(ccxt, self.exchange_name)

        # Get API credentials from environment
        api_key = os.getenv(f"{exchange_name.upper()}_API_KEY")
        secret_key = os.getenv(f"{exchange_name.upper()}_SECRET_KEY")

        config = {
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # spot, margin, future, swap
            }
        }

        # Enable testnet if specified
        if testnet:
            config['sandbox'] = True

        self.exchange = exchange_class(config)

        # Load markets
        self.exchange.load_markets()

    def get_balance(self, currency: Optional[str] = None) -> Dict[str, Any]:
        """
        Get account balance.

        Args:
            currency: Specific currency (e.g., 'BTC', 'USDT'). If None, returns all.

        Returns:
            Balance information
        """
        balance = self.exchange.fetch_balance()

        if currency:
            return {
                "currency": currency,
                "free": balance['free'].get(currency, 0),
                "used": balance['used'].get(currency, 0),
                "total": balance['total'].get(currency, 0)
            }
        else:
            # Return all non-zero balances
            result = {}
            for curr in balance['total']:
                if balance['total'][curr] > 0:
                    result[curr] = {
                        "free": balance['free'].get(curr, 0),
                        "used": balance['used'].get(curr, 0),
                        "total": balance['total'][curr]
                    }
            return result

    def get_current_price(self, symbol: str) -> float:
        """
        Get current price for a trading pair.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')

        Returns:
            Current price
        """
        ticker = self.exchange.fetch_ticker(symbol)
        return ticker['last']

    def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """
        Get orderbook for a symbol.

        Args:
            symbol: Trading pair
            depth: Number of price levels

        Returns:
            Orderbook with bids and asks
        """
        orderbook = self.exchange.fetch_order_book(symbol, limit=depth)

        return {
            "symbol": symbol,
            "timestamp": orderbook.get('timestamp'),
            "bids": orderbook['bids'][:depth],  # [[price, size], ...]
            "asks": orderbook['asks'][:depth],
            "bid": orderbook['bids'][0][0] if orderbook['bids'] else None,
            "ask": orderbook['asks'][0][0] if orderbook['asks'] else None,
            "spread": (orderbook['asks'][0][0] - orderbook['bids'][0][0])
                     if orderbook['bids'] and orderbook['asks'] else None
        }

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100,
        since: Optional[int] = None
    ) -> List[List]:
        """
        Get OHLCV (candlestick) data.

        Args:
            symbol: Trading pair
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of candles
            since: Timestamp in ms (fetch from this time)

        Returns:
            List of OHLCV candles [[timestamp, open, high, low, close, volume], ...]
        """
        return self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)

    def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a market order.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: 'buy' or 'sell'
            amount: Order size
            params: Additional parameters

        Returns:
            Order information
        """
        order = self.exchange.create_market_order(
            symbol,
            side,
            amount,
            params or {}
        )

        return self._format_order(order)

    def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a limit order.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Order size
            price: Limit price
            params: Additional parameters

        Returns:
            Order information
        """
        order = self.exchange.create_limit_order(
            symbol,
            side,
            amount,
            price,
            params or {}
        )

        return self._format_order(order)

    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancel an open order.

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            Cancellation result
        """
        result = self.exchange.cancel_order(order_id, symbol)
        return result

    def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Get order details.

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            Order information
        """
        order = self.exchange.fetch_order(order_id, symbol)
        return self._format_order(order)

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open orders.

        Args:
            symbol: Trading pair (if None, returns all open orders)

        Returns:
            List of open orders
        """
        orders = self.exchange.fetch_open_orders(symbol)
        return [self._format_order(order) for order in orders]

    def get_closed_orders(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get closed orders.

        Args:
            symbol: Trading pair
            limit: Number of orders to fetch

        Returns:
            List of closed orders
        """
        orders = self.exchange.fetch_closed_orders(symbol, limit=limit)
        return [self._format_order(order) for order in orders]

    def get_my_trades(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get trade history.

        Args:
            symbol: Trading pair
            limit: Number of trades to fetch

        Returns:
            List of trades
        """
        trades = self.exchange.fetch_my_trades(symbol, limit=limit)
        return [self._format_trade(trade) for trade in trades]

    def _format_order(self, order: Dict) -> Dict[str, Any]:
        """Format order data to a consistent structure."""
        return {
            "id": order['id'],
            "symbol": order['symbol'],
            "type": order['type'],  # market, limit
            "side": order['side'],  # buy, sell
            "price": order['price'],
            "amount": order['amount'],
            "filled": order['filled'],
            "remaining": order['remaining'],
            "cost": order['cost'],  # filled * price
            "status": order['status'],  # open, closed, canceled
            "timestamp": order['timestamp'],
            "datetime": order['datetime'],
            "fee": order.get('fee'),
            "trades": order.get('trades')
        }

    def _format_trade(self, trade: Dict) -> Dict[str, Any]:
        """Format trade data to a consistent structure."""
        return {
            "id": trade['id'],
            "order_id": trade.get('order'),
            "symbol": trade['symbol'],
            "side": trade['side'],
            "price": trade['price'],
            "amount": trade['amount'],
            "cost": trade['cost'],
            "timestamp": trade['timestamp'],
            "datetime": trade['datetime'],
            "fee": trade.get('fee')
        }

    def get_markets(self) -> List[str]:
        """Get list of available trading pairs."""
        return list(self.exchange.markets.keys())

    def get_market_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed market information.

        Args:
            symbol: Trading pair

        Returns:
            Market information including limits and precision
        """
        market = self.exchange.market(symbol)
        return {
            "symbol": market['symbol'],
            "base": market['base'],
            "quote": market['quote'],
            "active": market['active'],
            "precision": market['precision'],
            "limits": market['limits'],
            "maker_fee": market.get('maker'),
            "taker_fee": market.get('taker')
        }


class ExchangeManager:
    """Manages multiple exchange connections."""

    def __init__(self, testnet: bool = False):
        """
        Initialize exchange manager.

        Args:
            testnet: Whether to use testnet mode
        """
        self.testnet = testnet
        self.exchanges: Dict[str, ExchangeConnector] = {}

    def add_exchange(self, exchange_name: str) -> ExchangeConnector:
        """
        Add an exchange connection.

        Args:
            exchange_name: Name of the exchange

        Returns:
            Exchange connector instance
        """
        if exchange_name not in self.exchanges:
            self.exchanges[exchange_name] = ExchangeConnector(
                exchange_name,
                testnet=self.testnet
            )
        return self.exchanges[exchange_name]

    def get_exchange(self, exchange_name: str) -> Optional[ExchangeConnector]:
        """Get an exchange connector."""
        return self.exchanges.get(exchange_name)

    def get_all_balances(self) -> Dict[str, Dict]:
        """Get balances from all connected exchanges."""
        balances = {}
        for name, exchange in self.exchanges.items():
            try:
                balances[name] = exchange.get_balance()
            except Exception as e:
                balances[name] = {"error": str(e)}
        return balances

    def get_total_value_usd(self) -> float:
        """
        Calculate total portfolio value in USD across all exchanges.

        Returns:
            Total value in USD
        """
        total = 0.0

        for exchange_name, exchange in self.exchanges.items():
            try:
                balances = exchange.get_balance()

                for currency, balance_info in balances.items():
                    amount = balance_info['total']

                    if amount > 0:
                        if currency == 'USDT' or currency == 'USDC' or currency == 'USD':
                            # Stablecoins are 1:1 with USD
                            total += amount
                        else:
                            # Get USD price for other currencies
                            try:
                                # Try common USD pairs
                                for quote in ['USDT', 'USDC', 'USD']:
                                    symbol = f"{currency}/{quote}"
                                    if symbol in exchange.exchange.markets:
                                        price = exchange.get_current_price(symbol)
                                        total += amount * price
                                        break
                            except Exception:
                                # Skip if we can't get price
                                pass

            except Exception as e:
                print(f"Error calculating value for {exchange_name}: {e}")

        return total
