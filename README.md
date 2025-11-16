# Claude Capital

An autonomous AI trading firm powered by Claude Code.

## Overview

Claude Capital is an algorithmic trading system where Claude Code operates with full autonomy to research, develop, and deploy trading strategies. The system runs on a scheduled loop (every 30 minutes by default), analyzing market conditions, managing positions, and making trading decisions.

## Key Features

- **Autonomous Decision Making**: Claude researches opportunities and makes trading decisions independently
- **State Persistence**: Full state continuity between sessions
- **Multi-Exchange Support**: Trade across multiple cryptocurrency exchanges
- **Robust Risk Management**: Multi-layer risk controls and circuit breakers
- **Complete Audit Trail**: Every decision and trade is logged with reasoning
- **Strategy Framework**: Develop, backtest, and deploy trading strategies

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design.

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key
- Crypto wallet with private key
- Exchange API keys

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize the firm
python scripts/initialize_firm.py \
  --name "Claude Capital" \
  --initial-capital 10000 \
  --wallet-key-path /path/to/key
```

### Running

```bash
# Single execution (for testing)
python src/loop.py

# Schedule with cron (production)
# Add to crontab: */30 * * * * cd /path/to/claude-capital && python src/loop.py
```

## Project Structure

```
claude-capital/
├── src/
│   ├── loop.py              # Main execution loop
│   ├── trading/             # Trading engine components
│   │   ├── wallet.py        # Wallet management
│   │   ├── exchanges.py     # Exchange connectors
│   │   ├── executor.py      # Order execution
│   │   ├── positions.py     # Position tracking
│   │   └── risk.py          # Risk management
│   ├── strategies/          # Trading strategies
│   │   ├── base.py          # Base strategy class
│   │   └── registry.py      # Strategy registry
│   ├── tools/               # Tools for Claude
│   │   ├── market_data.py   # Market data tools
│   │   ├── trading.py       # Trading tools
│   │   ├── analysis.py      # Analysis tools
│   │   └── research.py      # Research tools
│   └── utils/               # Utilities
│       ├── state.py         # State management
│       └── logger.py        # Logging
├── state/
│   └── firm_state.json      # Persistent state
├── config/
│   └── risk_limits.json     # Risk configuration
├── secrets/                 # Encrypted keys (gitignored)
├── logs/                    # Session logs
└── scripts/
    └── initialize_firm.py   # Initialization script
```

## Safety Features

- **Position Limits**: Max position size, max concurrent positions
- **Daily Loss Limits**: Circuit breaker stops trading if daily loss exceeds threshold
- **Pre-Trade Validation**: All trades validated before execution
- **Emergency Stop**: Manual kill switch to halt all trading
- **Encrypted Keys**: Private keys encrypted at rest

## Development Phases

- [x] Phase 1: Core architecture design
- [ ] Phase 2: State management and loop executor
- [ ] Phase 3: Trading engine and wallet integration
- [ ] Phase 4: Claude tools and integration
- [ ] Phase 5: Strategy framework
- [ ] Phase 6: Testing and deployment

## Configuration

### Risk Limits

Edit `config/risk_limits.json`:

```json
{
  "max_position_size_usd": 1000,
  "max_total_positions": 5,
  "max_daily_loss_usd": 500,
  "max_total_allocated_pct": 0.8,
  "max_leverage": 1.0
}
```

### Emergency Stop

```bash
# Stop all trading immediately
touch state/emergency_stop.flag

# Resume trading
rm state/emergency_stop.flag
```

## Monitoring

```bash
# View latest session log
tail -f logs/session_$(date +%Y%m%d).log

# Check current state
cat state/firm_state.json | jq '.performance'

# View recent trades
cat state/firm_state.json | jq '.trade_history | .[-5:]'
```

## Contributing

This is an experimental autonomous trading system. Contributions welcome!

## Disclaimer

**USE AT YOUR OWN RISK**. This is experimental software. Cryptocurrency trading carries significant risk. Never trade with money you cannot afford to lose. The autonomous nature of this system means it will make decisions without human approval. Always start with small amounts and monitor closely.

## License

MIT
