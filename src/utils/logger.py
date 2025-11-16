"""
Logging utilities for Claude Capital.

Provides structured logging with different levels and formatters.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class TradingLogger:
    """Custom logger for trading activities."""

    def __init__(self, name: str = "claude_capital", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()  # Clear any existing handlers

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler (daily rotation)
        log_file = self.log_dir / f"session_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Trade log file (separate file for trade execution)
        self.trade_log_file = self.log_dir / "trades.log"

    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False) -> None:
        """Log error message."""
        self.logger.error(message, exc_info=exc_info)

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def trade(self, trade_info: dict) -> None:
        """
        Log a trade execution to separate trade log.

        Args:
            trade_info: Dictionary with trade details
        """
        timestamp = datetime.utcnow().isoformat()
        log_entry = (
            f"{timestamp} | TRADE | "
            f"{trade_info.get('side', 'UNKNOWN').upper()} "
            f"{trade_info.get('size', 0)} {trade_info.get('symbol', 'UNKNOWN')} "
            f"@ {trade_info.get('price', 0)} "
            f"| Exchange: {trade_info.get('exchange', 'UNKNOWN')} "
            f"| Strategy: {trade_info.get('strategy', 'manual')} "
            f"| ID: {trade_info.get('id', 'N/A')}\n"
        )

        with open(self.trade_log_file, 'a') as f:
            f.write(log_entry)

        # Also log to main logger
        self.logger.info(f"TRADE EXECUTED: {log_entry.strip()}")

    def decision(self, decision: str, reasoning: str, confidence: float = 0.5) -> None:
        """
        Log a trading decision with reasoning.

        Args:
            decision: The decision made
            reasoning: Explanation of the decision
            confidence: Confidence level (0-1)
        """
        self.logger.info(
            f"DECISION [{confidence:.0%} confidence]: {decision} | "
            f"Reasoning: {reasoning}"
        )

    def session_start(self, session_info: Optional[dict] = None) -> None:
        """Log the start of a trading session."""
        self.logger.info("=" * 80)
        self.logger.info("TRADING SESSION STARTED")
        if session_info:
            for key, value in session_info.items():
                self.logger.info(f"  {key}: {value}")
        self.logger.info("=" * 80)

    def session_end(self, summary: Optional[dict] = None) -> None:
        """Log the end of a trading session."""
        self.logger.info("=" * 80)
        self.logger.info("TRADING SESSION ENDED")
        if summary:
            for key, value in summary.items():
                self.logger.info(f"  {key}: {value}")
        self.logger.info("=" * 80)


# Global logger instance
_logger: Optional[TradingLogger] = None


def get_logger() -> TradingLogger:
    """Get or create the global logger instance."""
    global _logger
    if _logger is None:
        _logger = TradingLogger()
    return _logger
