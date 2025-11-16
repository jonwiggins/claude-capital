"""
Momentum trading strategy.

Enters long positions when price shows strong upward momentum
and exits when momentum weakens or reverses.
"""

import numpy as np
from typing import Dict, List, Any, Optional
from .base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """
    Simple momentum strategy based on rate of change and moving averages.

    Entry signals:
    - Price above fast MA
    - Fast MA above slow MA (trending up)
    - Rate of change above threshold
    - Volume confirmation

    Exit signals:
    - Price below fast MA
    - Fast MA crosses below slow MA
    - Take profit reached
    - Stop loss hit
    """

    def __init__(
        self,
        name: str = "momentum_v1",
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize momentum strategy.

        Default params:
            fast_ma_period: 10 (fast moving average)
            slow_ma_period: 30 (slow moving average)
            roc_period: 14 (rate of change period)
            roc_threshold: 2.0 (% change threshold)
            volume_ma_period: 20 (volume moving average)
            volume_threshold: 1.2 (volume multiplier)
            take_profit_pct: 5.0 (take profit %)
            stop_loss_pct: 2.0 (stop loss %)
        """
        default_params = {
            "fast_ma_period": 10,
            "slow_ma_period": 30,
            "roc_period": 14,
            "roc_threshold": 2.0,
            "volume_ma_period": 20,
            "volume_threshold": 1.2,
            "take_profit_pct": 5.0,
            "stop_loss_pct": 2.0
        }

        # Merge with provided params
        if params:
            default_params.update(params)

        super().__init__(name=name, params=default_params)

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market using momentum indicators.

        Args:
            market_data: Dict with 'ohlcv' key containing OHLCV data

        Returns:
            Analysis results with indicators
        """
        ohlcv = market_data.get('ohlcv', [])

        if len(ohlcv) < self.params['slow_ma_period']:
            return {
                "error": "Insufficient data for analysis",
                "required": self.params['slow_ma_period'],
                "available": len(ohlcv)
            }

        # Extract price and volume
        closes = np.array([candle[4] for candle in ohlcv])
        volumes = np.array([candle[5] for candle in ohlcv])

        # Calculate indicators
        fast_ma = self._moving_average(closes, self.params['fast_ma_period'])
        slow_ma = self._moving_average(closes, self.params['slow_ma_period'])
        roc = self._rate_of_change(closes, self.params['roc_period'])
        volume_ma = self._moving_average(volumes, self.params['volume_ma_period'])

        # Current values
        current_price = closes[-1]
        current_fast_ma = fast_ma[-1]
        current_slow_ma = slow_ma[-1]
        current_roc = roc[-1]
        current_volume = volumes[-1]
        current_volume_ma = volume_ma[-1]

        # Trend analysis
        is_uptrend = current_fast_ma > current_slow_ma
        price_above_fast_ma = current_price > current_fast_ma
        strong_momentum = current_roc > self.params['roc_threshold']
        volume_confirmation = current_volume > (current_volume_ma * self.params['volume_threshold'])

        return {
            "price": current_price,
            "fast_ma": current_fast_ma,
            "slow_ma": current_slow_ma,
            "roc": current_roc,
            "volume": current_volume,
            "volume_ma": current_volume_ma,
            "is_uptrend": is_uptrend,
            "price_above_fast_ma": price_above_fast_ma,
            "strong_momentum": strong_momentum,
            "volume_confirmation": volume_confirmation,
            "all_conditions_met": (
                is_uptrend and
                price_above_fast_ma and
                strong_momentum and
                volume_confirmation
            )
        }

    def generate_signals(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate buy/sell signals based on momentum.

        Args:
            symbol: Trading pair
            market_data: Market data

        Returns:
            List of signals
        """
        analysis = self.analyze(market_data)

        if 'error' in analysis:
            return []

        signals = []

        # Buy signal
        if analysis['all_conditions_met']:
            confidence = self._calculate_confidence(analysis)

            signals.append({
                "action": "buy",
                "symbol": symbol,
                "size": None,  # To be determined by position sizing
                "reason": (
                    f"Momentum entry: Price {analysis['price']:.2f}, "
                    f"Fast MA {analysis['fast_ma']:.2f}, "
                    f"ROC {analysis['roc']:.2f}%, "
                    f"Volume {analysis['volume'] / analysis['volume_ma']:.2f}x avg"
                ),
                "confidence": confidence,
                "indicators": {
                    "roc": analysis['roc'],
                    "ma_spread": ((analysis['fast_ma'] / analysis['slow_ma']) - 1) * 100
                }
            })

        # Sell signal (weak momentum or reversal)
        elif not analysis['is_uptrend'] or not analysis['price_above_fast_ma']:
            signals.append({
                "action": "sell",
                "symbol": symbol,
                "size": None,
                "reason": (
                    f"Momentum exit: "
                    f"{'Downtrend' if not analysis['is_uptrend'] else 'Price below MA'}"
                ),
                "confidence": 0.7,
                "indicators": {
                    "roc": analysis['roc'],
                    "price_ma_ratio": (analysis['price'] / analysis['fast_ma']) - 1
                }
            })

        return signals

    def should_exit(
        self,
        position: Dict[str, Any],
        current_price: float,
        market_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if should exit position (includes stop loss/take profit).

        Args:
            position: Current position
            current_price: Current price
            market_data: Market data

        Returns:
            (should_exit, reason)
        """
        entry_price = position['entry_price']

        # Calculate P&L %
        pnl_pct = ((current_price / entry_price) - 1) * 100

        # Take profit
        if pnl_pct >= self.params['take_profit_pct']:
            return True, f"Take profit hit: +{pnl_pct:.2f}%"

        # Stop loss
        if pnl_pct <= -self.params['stop_loss_pct']:
            return True, f"Stop loss hit: {pnl_pct:.2f}%"

        # Check momentum-based exit
        should_exit_momentum, reason = super().should_exit(position, current_price, market_data)

        return should_exit_momentum, reason

    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence score for entry signal.

        Args:
            analysis: Market analysis results

        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5  # Base confidence

        # Stronger ROC = higher confidence
        if analysis['roc'] > self.params['roc_threshold'] * 2:
            confidence += 0.2
        elif analysis['roc'] > self.params['roc_threshold']:
            confidence += 0.1

        # Stronger volume confirmation = higher confidence
        volume_ratio = analysis['volume'] / analysis['volume_ma']
        if volume_ratio > self.params['volume_threshold'] * 1.5:
            confidence += 0.2
        elif volume_ratio > self.params['volume_threshold']:
            confidence += 0.1

        # MA spread (how far apart the MAs are)
        ma_spread = ((analysis['fast_ma'] / analysis['slow_ma']) - 1) * 100
        if ma_spread > 2:
            confidence += 0.1

        return min(confidence, 0.95)  # Cap at 95%

    @staticmethod
    def _moving_average(data: np.ndarray, period: int) -> np.ndarray:
        """Calculate simple moving average."""
        return np.convolve(data, np.ones(period), 'valid') / period

    @staticmethod
    def _rate_of_change(data: np.ndarray, period: int) -> np.ndarray:
        """
        Calculate rate of change (ROC).

        ROC = ((Current - Previous) / Previous) * 100
        """
        roc = np.zeros(len(data))
        for i in range(period, len(data)):
            roc[i] = ((data[i] - data[i - period]) / data[i - period]) * 100
        return roc


class AdaptiveMomentumStrategy(MomentumStrategy):
    """
    Adaptive momentum strategy that adjusts parameters based on volatility.

    In high volatility, uses wider stops and higher ROC threshold.
    In low volatility, uses tighter stops and lower ROC threshold.
    """

    def __init__(self, name: str = "adaptive_momentum_v1", params: Optional[Dict[str, Any]] = None):
        """Initialize adaptive momentum strategy."""
        default_params = {
            "fast_ma_period": 10,
            "slow_ma_period": 30,
            "roc_period": 14,
            "roc_threshold": 2.0,
            "volume_ma_period": 20,
            "volume_threshold": 1.2,
            "take_profit_pct": 5.0,
            "stop_loss_pct": 2.0,
            "volatility_period": 20,
            "volatility_adjustment": True
        }

        if params:
            default_params.update(params)

        super().__init__(name=name, params=default_params)

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze with adaptive parameters based on volatility.

        Args:
            market_data: Market data

        Returns:
            Analysis with adjusted parameters
        """
        # Get base analysis
        analysis = super().analyze(market_data)

        if 'error' in analysis:
            return analysis

        # Calculate volatility
        ohlcv = market_data.get('ohlcv', [])
        closes = np.array([candle[4] for candle in ohlcv])

        # Calculate returns
        returns = np.diff(closes) / closes[:-1]
        volatility = np.std(returns[-self.params['volatility_period']:]) * np.sqrt(365)

        # Adjust parameters based on volatility
        if self.params['volatility_adjustment']:
            if volatility > 0.5:  # High volatility (>50% annualized)
                # Wider stops, higher thresholds
                self.params['stop_loss_pct'] = 3.0
                self.params['take_profit_pct'] = 7.0
                self.params['roc_threshold'] = 3.0
            elif volatility < 0.2:  # Low volatility (<20% annualized)
                # Tighter stops, lower thresholds
                self.params['stop_loss_pct'] = 1.5
                self.params['take_profit_pct'] = 3.0
                self.params['roc_threshold'] = 1.5
            else:
                # Normal parameters
                self.params['stop_loss_pct'] = 2.0
                self.params['take_profit_pct'] = 5.0
                self.params['roc_threshold'] = 2.0

        analysis['volatility'] = volatility
        analysis['adjusted_params'] = {
            'stop_loss': self.params['stop_loss_pct'],
            'take_profit': self.params['take_profit_pct'],
            'roc_threshold': self.params['roc_threshold']
        }

        return analysis
