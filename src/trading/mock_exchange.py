"""
Mock exchange for paper trading and testing.

Simulates exchange functionality without real trades, allowing safe testing
of the trading system with realistic market simulation.
"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import uuid


class MockExchange:
    """
    Simulated exchange for paper trading.

    Provides realistic simulation of exchange functionality including:
    - Price generation with volatility
    - Order execution
    - Balance tracking
    - OHLCV data generation
    """

    def __init__(self, initial_balance_usdt: float = 10000.0):
        """
        Initialize mock exchange.

        Args:
            initial_balance_usdt: Starting USDT balance
        """
        self.balances = {
            'USDT': initial_balance_usdt,
            'BTC': 0.0,
            'ETH': 0.0,
            'SOL': 0.0,
            'BNB': 0.0
        }

        # Initial prices
        self.prices = {
            'BTC/USDT': 50000.0,
            'ETH/USDT': 3000.0,
            'SOL/USDT': 100.0,
            'BNB/USDT': 400.0
        }

        # Price volatility (daily % volatility)
        self.volatility = {
            'BTC/USDT': 0.03,  # 3% daily volatility
            'ETH/USDT': 0.04,
            'SOL/USDT': 0.06,
            'BNB/USDT': 0.04
        }

        # Track orders
        self.orders = {}
        self.order_counter = 0

        # Historical prices for OHLCV
        self.price_history = {symbol: [] for symbol in self.prices.keys()}

        # Generate initial historical data
        self._generate_initial_history()

    def _generate_initial_history(self, days: int = 30):
        """Generate initial price history."""
        for symbol in self.prices.keys():
            base_price = self.prices[symbol]
            volatility = self.volatility[symbol]

            # Generate hourly candles for the past N days
            num_candles = days * 24
            timestamp = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

            price = base_price
            for i in range(num_candles):
                # Simulate price movement
                change = random.gauss(0, volatility / 24)  # Hourly volatility
                price = price * (1 + change)

                # Generate OHLCV
                open_price = price
                close_price = price * (1 + random.gauss(0, volatility / 48))
                high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, volatility / 96)))
                low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, volatility / 96)))
                volume = random.uniform(100, 1000)

                candle = [
                    timestamp + (i * 3600000),  # timestamp in ms
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume
                ]

                self.price_history[symbol].append(candle)

            # Update current price to last close
            self.prices[symbol] = self.price_history[symbol][-1][4]

    def _update_price(self, symbol: str) -> float:
        """
        Update price with realistic movement.

        Args:
            symbol: Trading pair

        Returns:
            New price
        """
        current_price = self.prices[symbol]
        volatility = self.volatility[symbol]

        # Random walk with drift
        hourly_volatility = volatility / (24 ** 0.5)
        change = random.gauss(0.0001, hourly_volatility)  # Slight positive drift

        new_price = current_price * (1 + change)
        self.prices[symbol] = new_price

        # Add to history
        timestamp = int(datetime.now().timestamp() * 1000)
        last_candle = self.price_history[symbol][-1]

        # Check if we need a new hourly candle
        if timestamp - last_candle[0] >= 3600000:  # 1 hour
            candle = [
                timestamp,
                current_price,  # open
                new_price,      # high (will be updated)
                new_price,      # low (will be updated)
                new_price,      # close
                random.uniform(100, 1000)  # volume
            ]
            self.price_history[symbol].append(candle)

            # Keep only last 1000 candles
            if len(self.price_history[symbol]) > 1000:
                self.price_history[symbol] = self.price_history[symbol][-1000:]
        else:
            # Update current candle
            last_candle[4] = new_price  # close
            last_candle[2] = max(last_candle[2], new_price)  # high
            last_candle[3] = min(last_candle[3], new_price)  # low

        return new_price

    def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        if symbol not in self.prices:
            raise ValueError(f"Unknown symbol: {symbol}")

        # Update price before returning
        return self._update_price(symbol)

    def get_balance(self, currency: Optional[str] = None) -> Dict[str, Any]:
        """Get account balance."""
        if currency:
            return {
                "currency": currency,
                "free": self.balances.get(currency, 0),
                "used": 0,
                "total": self.balances.get(currency, 0)
            }
        else:
            result = {}
            for curr, balance in self.balances.items():
                if balance > 0.00001:  # Filter dust
                    result[curr] = {
                        "free": balance,
                        "used": 0,
                        "total": balance
                    }
            return result

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100,
        since: Optional[int] = None
    ) -> List[List]:
        """Get OHLCV data."""
        if symbol not in self.price_history:
            raise ValueError(f"Unknown symbol: {symbol}")

        # For simplicity, always return hourly data
        history = self.price_history[symbol]

        # Apply limit
        if since:
            history = [c for c in history if c[0] >= since]

        return history[-limit:]

    def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a market order."""
        if symbol not in self.prices:
            raise ValueError(f"Unknown symbol: {symbol}")

        # Update price
        price = self._update_price(symbol)

        # Extract base and quote currencies
        base, quote = symbol.split('/')

        # Calculate order cost
        if side == 'buy':
            cost = amount * price
            fee_amount = cost * 0.001  # 0.1% fee
            total_cost = cost + fee_amount

            # Check balance
            if self.balances.get(quote, 0) < total_cost:
                raise ValueError(f"Insufficient {quote} balance")

            # Execute trade
            self.balances[quote] -= total_cost
            self.balances[base] = self.balances.get(base, 0) + amount

        elif side == 'sell':
            # Check balance
            if self.balances.get(base, 0) < amount:
                raise ValueError(f"Insufficient {base} balance")

            # Execute trade
            proceeds = amount * price
            fee_amount = proceeds * 0.001
            net_proceeds = proceeds - fee_amount

            self.balances[base] -= amount
            self.balances[quote] = self.balances.get(quote, 0) + net_proceeds

        else:
            raise ValueError(f"Invalid side: {side}")

        # Create order record
        self.order_counter += 1
        order_id = f"mock_{self.order_counter}_{uuid.uuid4().hex[:6]}"

        order = {
            "id": order_id,
            "symbol": symbol,
            "type": "market",
            "side": side,
            "price": price,
            "amount": amount,
            "filled": amount,
            "remaining": 0,
            "cost": amount * price,
            "status": "closed",
            "timestamp": int(datetime.now().timestamp() * 1000),
            "datetime": datetime.now().isoformat(),
            "fee": {
                "cost": fee_amount,
                "currency": quote
            }
        }

        self.orders[order_id] = order
        return order

    def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a limit order (immediately filled in mock)."""
        # In mock mode, limit orders are immediately filled at the limit price
        current_price = self.get_current_price(symbol)

        # Check if order would fill
        if side == 'buy' and current_price <= price:
            fill_price = price
        elif side == 'sell' and current_price >= price:
            fill_price = price
        else:
            # Order wouldn't fill, but fill it anyway for testing
            fill_price = price

        # Execute as market order at limit price
        base, quote = symbol.split('/')

        if side == 'buy':
            cost = amount * fill_price
            fee_amount = cost * 0.001
            total_cost = cost + fee_amount

            if self.balances.get(quote, 0) < total_cost:
                raise ValueError(f"Insufficient {quote} balance")

            self.balances[quote] -= total_cost
            self.balances[base] = self.balances.get(base, 0) + amount

        elif side == 'sell':
            if self.balances.get(base, 0) < amount:
                raise ValueError(f"Insufficient {base} balance")

            proceeds = amount * fill_price
            fee_amount = proceeds * 0.001
            net_proceeds = proceeds - fee_amount

            self.balances[base] -= amount
            self.balances[quote] = self.balances.get(quote, 0) + net_proceeds

        # Create order record
        self.order_counter += 1
        order_id = f"mock_{self.order_counter}_{uuid.uuid4().hex[:6]}"

        order = {
            "id": order_id,
            "symbol": symbol,
            "type": "limit",
            "side": side,
            "price": fill_price,
            "amount": amount,
            "filled": amount,
            "remaining": 0,
            "cost": amount * fill_price,
            "status": "closed",
            "timestamp": int(datetime.now().timestamp() * 1000),
            "datetime": datetime.now().isoformat(),
            "fee": {
                "cost": fee_amount,
                "currency": quote
            }
        }

        self.orders[order_id] = order
        return order

    def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get simulated orderbook."""
        price = self.get_current_price(symbol)

        # Generate realistic orderbook
        bids = []
        asks = []

        for i in range(depth):
            # Bids below current price
            bid_price = price * (1 - (i + 1) * 0.0001)
            bid_size = random.uniform(0.1, 2.0)
            bids.append([bid_price, bid_size])

            # Asks above current price
            ask_price = price * (1 + (i + 1) * 0.0001)
            ask_size = random.uniform(0.1, 2.0)
            asks.append([ask_price, ask_size])

        return {
            "symbol": symbol,
            "timestamp": int(datetime.now().timestamp() * 1000),
            "bids": bids,
            "asks": asks,
            "bid": bids[0][0] if bids else None,
            "ask": asks[0][0] if asks else None,
            "spread": asks[0][0] - bids[0][0] if bids and asks else None
        }

    def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order details."""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        return order

    def get_markets(self) -> List[str]:
        """Get list of available markets."""
        return list(self.prices.keys())


class MockExchangeConnector:
    """
    Wrapper to make MockExchange compatible with ExchangeConnector interface.
    """

    def __init__(self, initial_balance_usdt: float = 10000.0):
        """Initialize mock exchange connector."""
        self.exchange_name = "mock"
        self.testnet = True
        self.exchange = MockExchange(initial_balance_usdt)

    def get_balance(self, currency: Optional[str] = None) -> Dict[str, Any]:
        """Get account balance."""
        return self.exchange.get_balance(currency)

    def get_current_price(self, symbol: str) -> float:
        """Get current price."""
        return self.exchange.get_current_price(symbol)

    def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get orderbook."""
        return self.exchange.get_orderbook(symbol, depth)

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100,
        since: Optional[int] = None
    ) -> List[List]:
        """Get OHLCV data."""
        return self.exchange.get_ohlcv(symbol, timeframe, limit, since)

    def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create market order."""
        return self.exchange.create_market_order(symbol, side, amount, params)

    def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create limit order."""
        return self.exchange.create_limit_order(symbol, side, amount, price, params)

    def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order."""
        return self.exchange.get_order(order_id, symbol)

    def get_markets(self) -> List[str]:
        """Get markets."""
        return self.exchange.get_markets()

    def get_market_info(self, symbol: str) -> Dict[str, Any]:
        """Get market info."""
        base, quote = symbol.split('/')
        return {
            "symbol": symbol,
            "base": base,
            "quote": quote,
            "active": True,
            "precision": {"amount": 8, "price": 2},
            "limits": {
                "amount": {"min": 0.001, "max": 1000},
                "price": {"min": 0.01, "max": 1000000},
                "cost": {"min": 10, "max": 1000000}
            },
            "maker_fee": 0.001,
            "taker_fee": 0.001
        }
