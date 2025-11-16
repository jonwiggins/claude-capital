"""
Tests for mock exchange.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading.mock_exchange import MockExchange, MockExchangeConnector


class TestMockExchange:
    """Test mock exchange functionality."""

    @pytest.fixture
    def exchange(self):
        """Create a mock exchange instance."""
        return MockExchange(initial_balance_usdt=10000.0)

    def test_initial_balance(self, exchange):
        """Test initial balance setup."""
        balance = exchange.get_balance('USDT')

        assert balance['currency'] == 'USDT'
        assert balance['total'] == 10000.0
        assert balance['free'] == 10000.0

    def test_price_updates(self, exchange):
        """Test price updates."""
        initial_price = exchange.get_current_price('BTC/USDT')
        assert initial_price > 0

        # Get price again, should change slightly
        new_price = exchange.get_current_price('BTC/USDT')
        assert new_price > 0

        # Prices should be similar but not identical
        # (unless by chance the random walk returned same price)
        assert abs(new_price - initial_price) / initial_price < 0.1  # Less than 10% change

    def test_market_buy_order(self, exchange):
        """Test market buy order execution."""
        initial_usdt = exchange.balances['USDT']
        initial_btc = exchange.balances.get('BTC', 0)

        # Buy 0.1 BTC
        order = exchange.create_market_order('BTC/USDT', 'buy', 0.1)

        assert order['status'] == 'closed'
        assert order['side'] == 'buy'
        assert order['filled'] == 0.1

        # Check balances changed
        final_usdt = exchange.balances['USDT']
        final_btc = exchange.balances.get('BTC', 0)

        assert final_usdt < initial_usdt  # USDT decreased
        assert final_btc > initial_btc     # BTC increased
        assert final_btc == initial_btc + 0.1

    def test_market_sell_order(self, exchange):
        """Test market sell order execution."""
        # First buy some BTC
        exchange.create_market_order('BTC/USDT', 'buy', 0.1)

        initial_usdt = exchange.balances['USDT']
        initial_btc = exchange.balances.get('BTC', 0)

        # Sell the BTC
        order = exchange.create_market_order('BTC/USDT', 'sell', 0.1)

        assert order['status'] == 'closed'
        assert order['side'] == 'sell'

        # Check balances
        final_usdt = exchange.balances['USDT']
        final_btc = exchange.balances.get('BTC', 0)

        assert final_usdt > initial_usdt  # USDT increased
        assert final_btc < initial_btc     # BTC decreased

    def test_insufficient_balance(self, exchange):
        """Test trading with insufficient balance."""
        # Try to buy more BTC than we have USDT for
        with pytest.raises(ValueError, match="Insufficient"):
            exchange.create_market_order('BTC/USDT', 'buy', 1.0)  # Way too much

    def test_limit_order(self, exchange):
        """Test limit order execution."""
        order = exchange.create_limit_order('BTC/USDT', 'buy', 0.1, 45000.0)

        assert order['status'] == 'closed'
        assert order['type'] == 'limit'
        assert order['price'] == 45000.0

    def test_get_ohlcv(self, exchange):
        """Test OHLCV data retrieval."""
        ohlcv = exchange.get_ohlcv('BTC/USDT', '1h', limit=50)

        assert len(ohlcv) > 0
        assert len(ohlcv) <= 50

        # Check candle structure
        candle = ohlcv[0]
        assert len(candle) == 6  # [timestamp, open, high, low, close, volume]
        assert candle[2] >= candle[1]  # high >= open
        assert candle[2] >= candle[4]  # high >= close
        assert candle[3] <= candle[1]  # low <= open
        assert candle[3] <= candle[4]  # low <= close

    def test_get_orderbook(self, exchange):
        """Test orderbook generation."""
        orderbook = exchange.get_orderbook('BTC/USDT', depth=10)

        assert 'bids' in orderbook
        assert 'asks' in orderbook
        assert len(orderbook['bids']) == 10
        assert len(orderbook['asks']) == 10

        # Bids should be descending
        assert orderbook['bids'][0][0] > orderbook['bids'][-1][0]

        # Asks should be ascending
        assert orderbook['asks'][0][0] < orderbook['asks'][-1][0]

        # Best bid < best ask (spread)
        assert orderbook['bid'] < orderbook['ask']

    def test_get_order(self, exchange):
        """Test order retrieval."""
        # Create an order
        order = exchange.create_market_order('BTC/USDT', 'buy', 0.05)
        order_id = order['id']

        # Retrieve it
        retrieved = exchange.get_order(order_id, 'BTC/USDT')

        assert retrieved['id'] == order_id
        assert retrieved['symbol'] == 'BTC/USDT'
        assert retrieved['side'] == 'buy'

    def test_fees(self, exchange):
        """Test trading fees."""
        initial_balance = exchange.balances['USDT']

        # Buy BTC
        price = exchange.get_current_price('BTC/USDT')
        order = exchange.create_market_order('BTC/USDT', 'buy', 0.1)

        cost = order['cost']
        fee = order['fee']['cost']

        # Fee should be ~0.1% of cost
        expected_fee = cost * 0.001
        assert abs(fee - expected_fee) < 0.01

        # Total deducted should be cost + fee
        final_balance = exchange.balances['USDT']
        assert abs((initial_balance - final_balance) - (cost + fee)) < 0.01


class TestMockExchangeConnector:
    """Test mock exchange connector."""

    def test_connector_interface(self):
        """Test that connector implements expected interface."""
        connector = MockExchangeConnector(initial_balance_usdt=5000.0)

        # Test all expected methods exist
        assert hasattr(connector, 'get_balance')
        assert hasattr(connector, 'get_current_price')
        assert hasattr(connector, 'create_market_order')
        assert hasattr(connector, 'create_limit_order')
        assert hasattr(connector, 'get_ohlcv')
        assert hasattr(connector, 'get_orderbook')

    def test_connector_balance(self):
        """Test balance retrieval through connector."""
        connector = MockExchangeConnector(initial_balance_usdt=5000.0)

        balance = connector.get_balance('USDT')
        assert balance['total'] == 5000.0

    def test_connector_trading(self):
        """Test trading through connector."""
        connector = MockExchangeConnector(initial_balance_usdt=10000.0)

        # Get price
        price = connector.get_current_price('BTC/USDT')
        assert price > 0

        # Place order
        order = connector.create_market_order('BTC/USDT', 'buy', 0.1)
        assert order['status'] == 'closed'

        # Check balance changed
        balance = connector.get_balance('BTC')
        assert balance['total'] > 0
