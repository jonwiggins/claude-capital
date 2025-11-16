# Claude Capital - Project Summary

## What We Built

An **autonomous AI trading firm** powered by Claude Code that can:

- 🤖 **Operate Autonomously**: Claude makes trading decisions independently
- 💰 **Trade Cryptocurrency**: Integrates with major exchanges via ccxt
- 🔒 **Manage Risk**: Multi-layer risk controls and circuit breakers
- 📊 **Learn & Improve**: Maintains state across sessions to learn from past decisions
- 🔄 **Run on Loop**: Designed to run periodically (e.g., every 30 minutes)
- 🧠 **Pick Up Where It Left Off**: Full state continuity between sessions

## Architecture Highlights

### Core Components

1. **State Management** (`src/utils/state.py`)
   - Single source of truth: `state/firm_state.json`
   - Tracks positions, trades, strategies, research, decisions
   - Automatic backups before each update

2. **Trading Engine** (`src/trading/`)
   - **Wallet Manager**: Secure key management, blockchain integration
   - **Exchange Connector**: Unified interface to multiple exchanges
   - **Risk Validator**: Pre-trade validation, position limits, circuit breakers

3. **Main Loop** (`src/loop.py`)
   - Entry point called by scheduler
   - Loads state, updates prices, invokes Claude, saves state
   - Handles errors gracefully

4. **Claude Interface** (`src/tools/claude_interface.py`)
   - Provides trading tools to Claude
   - Executes trades, analyzes markets, logs decisions
   - Framework for full Claude Code integration

5. **Initialization** (`scripts/initialize_firm.py`)
   - Sets up new trading firm
   - Creates/encrypts wallet
   - Initializes state

## Key Features

### Autonomy
- Claude analyzes market conditions independently
- Makes trading decisions within risk limits
- Develops and deploys strategies
- Sets priorities for future sessions

### Safety
- **Position Limits**: Max size, max concurrent positions
- **Loss Limits**: Daily loss circuit breaker
- **Pre-Trade Validation**: All trades validated before execution
- **Emergency Stop**: Manual kill switch
- **Encrypted Keys**: Private keys encrypted at rest
- **Audit Trail**: Complete logging of all decisions and trades

### State Continuity
- Complete state persisted between sessions
- Decision history for learning
- Research notes maintained
- Performance metrics tracked
- Priorities carried forward

### Flexibility
- Support for multiple exchanges
- Multiple blockchain networks
- Configurable risk limits
- Testnet/paper trading mode
- Extensible strategy framework

## Technology Stack

- **Python 3.11+**: Core language
- **Anthropic SDK**: Claude API integration
- **ccxt**: Exchange connectivity (100+ exchanges)
- **web3.py**: Blockchain/wallet operations
- **pandas**: Data analysis
- **cryptography**: Secure key storage

## Project Structure

```
claude-capital/
├── ARCHITECTURE.md          # Detailed system design
├── SETUP_GUIDE.md          # Complete setup instructions
├── AUTONOMOUS_LOOP.md      # Guide to full autonomy
├── README.md               # Project overview
├── requirements.txt        # Dependencies
├── .env.example           # Environment template
│
├── src/
│   ├── loop.py            # Main execution loop ⭐
│   ├── utils/             # State management, logging
│   ├── trading/           # Wallet, exchanges, risk
│   └── tools/             # Claude interface, trading tools
│
├── scripts/
│   └── initialize_firm.py # Firm initialization ⭐
│
├── state/                 # Persistent state (gitignored)
│   ├── firm_state.json   # Single source of truth
│   └── backups/          # Automatic backups
│
├── config/               # Configuration files
├── secrets/              # Encrypted keys (gitignored)
└── logs/                # Session and trade logs
```

## How It Works

### The Loop

```
1. Scheduler triggers (every 30 min)
   ↓
2. Load state from firm_state.json
   ↓
3. Update position prices from exchanges
   ↓
4. Check safety (emergency stop, circuit breakers)
   ↓
5. Prepare context for Claude
   ↓
6. Invoke Claude with trading tools
   ↓
7. Claude analyzes, decides, executes
   ↓
8. Save updated state
   ↓
9. Log session activities
   ↓
10. Exit until next invocation
```

### Claude's Workflow Each Session

```
1. ASSESS
   - Review open positions
   - Check strategy performance
   - Evaluate risk utilization
   - Check last session's priorities

2. ANALYZE
   - Get market data
   - Review trends
   - Check for opportunities
   - Analyze correlations

3. DECIDE
   - Close positions? (TP/SL)
   - Enter new positions?
   - Adjust strategies?
   - Conduct research?

4. EXECUTE
   - Log decision with reasoning
   - Execute trades
   - Update strategies
   - Document actions

5. PLAN
   - Set priorities for next session
   - Note areas for research
   - Plan strategy improvements
```

## State Schema

The entire firm state is stored in one JSON file:

```json
{
  "firm": { ... },          // Firm metadata
  "capital": { ... },       // Capital allocation
  "positions": [],          // Open positions
  "strategies": { ... },    // Active/research strategies
  "trade_history": [],      // All trades
  "performance": { ... },   // Metrics
  "risk_limits": { ... },   // Risk parameters
  "research_log": [],       // Research notes
  "decision_log": [],       // All decisions
  "session_log": [],        // Session history
  "system": { ... }         // System state
}
```

## Risk Management

Multi-layer protection:

1. **Pre-Trade**: Size limits, balance checks, price validation
2. **Position-Level**: Max size ($1,000), max leverage (1.0x)
3. **Portfolio-Level**: Max allocation (80%), max positions (5)
4. **Daily Limits**: Max daily loss ($500) with circuit breaker
5. **Manual Overrides**: Emergency stop, config updates

## Getting Started

Quick start:

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Initialize
python scripts/initialize_firm.py \
  --initial-capital 10000 \
  --create-wallet

# 4. Test
python src/loop.py

# 5. Schedule
crontab -e
# Add: */30 * * * * cd /path/to/claude-capital && python src/loop.py
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Complete system architecture
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)**: Step-by-step setup
- **[AUTONOMOUS_LOOP.md](AUTONOMOUS_LOOP.md)**: Making it fully autonomous
- **[README.md](README.md)**: Project overview

## Current Status

### ✅ Implemented

- Core architecture design
- State management system
- Wallet integration (Ethereum/EVM)
- Exchange connectivity (ccxt)
- Risk management framework
- Main execution loop
- Trading tools for Claude
- Initialization scripts
- Logging and monitoring
- Safety features

### 🚧 To Be Enhanced

- Full Claude Code integration (tool calling)
- Strategy backtesting framework
- Web research integration
- Multiple chain support
- Performance dashboard
- Advanced analytics
- Machine learning models
- Social trading features

## Next Steps

### For Development

1. **Enhance Claude Integration**
   - Implement full tool calling loop
   - Add extended thinking mode
   - Enable autonomous research

2. **Strategy Framework**
   - Base strategy class implementation
   - Backtesting engine
   - Strategy registry

3. **Advanced Features**
   - Multi-exchange arbitrage
   - DeFi integration
   - On-chain analytics

### For Testing

1. **Paper Trading**
   - Test on exchange testnets
   - Validate risk controls
   - Monitor decision quality

2. **Gradual Deployment**
   - Start with small capital
   - Conservative risk limits
   - Close human monitoring

3. **Performance Validation**
   - Track decision quality
   - Measure strategy effectiveness
   - Optimize parameters

## Design Philosophy

### Autonomy with Guardrails
Claude has creative freedom to develop strategies, but operates within strict risk constraints.

### State Continuity
Each session builds on previous ones. Claude maintains institutional knowledge.

### Transparent Decisions
Every decision logged with reasoning. Complete audit trail.

### Safety First
Multiple layers of protection. Circuit breakers. Emergency stops.

### Fail-Safe Defaults
Conservative limits by default. Gradual expansion of autonomy.

## Use Cases

1. **Research Platform**: Let Claude research trading strategies
2. **Algorithmic Trading**: Deploy systematic strategies
3. **Portfolio Management**: Autonomous rebalancing
4. **Market Making**: Provide liquidity on DEXs
5. **Arbitrage**: Cross-exchange opportunities
6. **Risk Management**: Position monitoring and hedging

## Disclaimer

⚠️ **This is experimental software for educational purposes.**

- Cryptocurrency trading carries significant risk
- Start with capital you can afford to lose
- The autonomous nature means Claude makes real decisions
- Always monitor closely, especially initially
- Past performance does not guarantee future results

By using this software, you acknowledge these risks and agree to use it responsibly.

## Contributing

This is an experimental project. Contributions welcome:

- Strategy implementations
- Exchange integrations
- Risk management improvements
- Analytics and monitoring
- Documentation

## License

MIT License - See LICENSE file

---

## Summary

**Claude Capital** is a complete framework for autonomous AI trading, powered by Claude Code. It provides the infrastructure for Claude to operate as a real trading firm: researching markets, developing strategies, executing trades, and learning from experience - all while operating within robust safety constraints.

The system is designed to run continuously on a loop, with Claude making independent decisions based on comprehensive state information that persists across sessions. This creates true institutional memory and allows Claude to build on previous work.

Start conservative, monitor closely, and watch Claude develop into a sophisticated trading system. 🚀

---

**Built with Claude Code** | [Architecture](ARCHITECTURE.md) | [Setup](SETUP_GUIDE.md) | [Autonomous Loop](AUTONOMOUS_LOOP.md)
