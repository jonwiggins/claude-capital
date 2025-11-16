# Claude Capital - Autonomous AI Trading Firm Architecture

## Executive Summary

Claude Capital is an autonomous algorithmic trading firm powered by Claude Code. The system operates on a scheduled loop (e.g., every 30 minutes) where Claude analyzes the current state of the firm, researches opportunities, makes trading decisions, and executes trades autonomously.

## Core Design Philosophy

**Autonomy with Guardrails**: Claude has creative freedom to develop and deploy trading strategies while operating within strict risk management constraints.

**State Continuity**: Each invocation is stateless from Claude's perspective, but the system maintains comprehensive state that allows Claude to pick up exactly where it left off.

**Transparent Decision Making**: Every decision, trade, and research activity is logged for auditability and learning.

## System Architecture

### High-Level Flow

```
┌──────────────────────────────────────────────────────┐
│         Scheduler (cron/systemd timer)               │
│              Triggers every 30 min                   │
└───────────────────────┬──────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│              Main Loop (src/loop.py)                 │
│  1. Load firm state from persistent storage          │
│  2. Prepare context for Claude                       │
│  3. Invoke Claude Code with trading tools            │
│  4. Claude analyzes, researches, decides, executes   │
│  5. Save updated state                               │
│  6. Exit cleanly                                     │
└───────────────────────┬──────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌──────────────┐
│   State     │  │   Trading   │  │   Market     │
│  Manager    │  │   Engine    │  │    Data      │
│             │  │             │  │              │
│ - Firm      │  │ - Wallet    │  │ - Exchanges  │
│   state     │  │ - Orders    │  │ - Prices     │
│ - Positions │  │ - Execution │  │ - Analytics  │
│ - History   │  │ - Risk mgmt │  │              │
└─────────────┘  └─────────────┘  └──────────────┘
```

## Core Components

### 1. State Management System

**Location**: `state/firm_state.json`

The single source of truth for the entire firm. Contains:

```json
{
  "firm": {
    "name": "Claude Capital",
    "inception_date": "ISO-8601",
    "wallet": {
      "address": "0x...",
      "chain": "ethereum",
      "encrypted_key_path": "secrets/wallet.enc"
    }
  },

  "capital": {
    "initial_usd": 10000,
    "current_total_usd": 10500,
    "liquid_usd": 8000,
    "allocated_usd": 2500
  },

  "positions": [
    {
      "id": "unique_id",
      "symbol": "BTC/USDT",
      "exchange": "binance",
      "side": "long",
      "size": 0.05,
      "entry_price": 50000,
      "current_price": 51000,
      "unrealized_pnl_usd": 50,
      "entry_timestamp": "ISO-8601",
      "strategy_name": "momentum_v1",
      "notes": "Entered on breakout signal"
    }
  ],

  "strategies": {
    "active": [
      {
        "name": "momentum_v1",
        "type": "trend_following",
        "status": "live",
        "allocated_capital_usd": 2000,
        "created_at": "ISO-8601",
        "code_path": "strategies/momentum_v1.py",
        "parameters": {},
        "performance": {
          "total_trades": 5,
          "winning_trades": 3,
          "pnl_usd": 150,
          "win_rate": 0.6,
          "sharpe_ratio": 1.5
        }
      }
    ],
    "research": [
      {
        "name": "mean_reversion_v1",
        "status": "backtesting",
        "hypothesis": "ETH shows mean reversion on 4h timeframe",
        "backtest_results": {},
        "next_steps": "Test on live data with paper trading"
      }
    ],
    "retired": []
  },

  "trade_history": [
    {
      "id": "trade_001",
      "timestamp": "ISO-8601",
      "symbol": "BTC/USDT",
      "side": "buy",
      "size": 0.05,
      "price": 50000,
      "fees_usd": 2.5,
      "exchange": "binance",
      "strategy": "momentum_v1",
      "order_id": "exchange_order_id"
    }
  ],

  "performance": {
    "total_pnl_usd": 500,
    "total_trades": 12,
    "winning_trades": 7,
    "win_rate": 0.583,
    "sharpe_ratio": 1.2,
    "max_drawdown_usd": -200,
    "best_trade_usd": 150,
    "worst_trade_usd": -80,
    "daily_pnl": []
  },

  "risk_limits": {
    "max_position_size_usd": 1000,
    "max_total_positions": 5,
    "max_daily_loss_usd": 500,
    "max_total_allocated_pct": 0.8,
    "max_leverage": 1.0,
    "daily_loss_circuit_breaker": true
  },

  "research_log": [
    {
      "id": "research_001",
      "timestamp": "ISO-8601",
      "topic": "BTC correlation with macro indices",
      "findings": "Negative correlation with DXY strengthening",
      "sources": ["urls", "data_analyzed"],
      "action_taken": "Adjusted momentum strategy to consider DXY",
      "outcome": "TBD"
    }
  ],

  "decision_log": [
    {
      "id": "decision_001",
      "timestamp": "ISO-8601",
      "decision": "Enter BTC long position (0.05 BTC)",
      "reasoning": "Strong momentum + volume confirmation + breakout",
      "confidence": 0.7,
      "outcome": "pending",
      "actual_outcome": null,
      "lessons_learned": null
    }
  ],

  "session_log": [
    {
      "timestamp": "ISO-8601",
      "duration_seconds": 45,
      "actions_taken": [
        "analyzed_market_conditions",
        "entered_btc_position",
        "updated_momentum_strategy"
      ],
      "errors": [],
      "next_priorities": [
        "monitor_btc_position_for_exit",
        "research_eth_mean_reversion",
        "analyze_portfolio_correlation"
      ]
    }
  ],

  "system": {
    "version": "0.1.0",
    "last_run": "ISO-8601",
    "emergency_stop": false,
    "alerts": []
  }
}
```

### 2. Main Loop Executor

**Location**: `src/loop.py`

The entry point that orchestrates each trading session:

```python
"""
Main execution loop for Claude Capital.

This script is invoked by the scheduler and:
1. Loads current firm state
2. Checks safety conditions
3. Invokes Claude Code with appropriate context and tools
4. Saves updated state
5. Handles errors and logging
"""

def main():
    # Load state
    state = load_firm_state()

    # Safety checks
    if state['system']['emergency_stop']:
        log_and_exit("Emergency stop active")

    if check_risk_limits_breached(state):
        handle_risk_breach(state)
        return

    # Prepare Claude context
    context = prepare_claude_context(state)

    # Invoke Claude Code
    # Claude will have access to trading tools and can make decisions
    session = invoke_claude_session(context)

    # Save updated state
    save_firm_state(state)

    # Cleanup
    log_session_metrics(session)
```

### 3. Trading Engine

**Location**: `src/trading/`

Handles all trading operations:

- **Wallet Manager** (`wallet.py`): Secure key management, balance checking
- **Exchange Connector** (`exchanges.py`): Unified interface to multiple exchanges via ccxt
- **Order Executor** (`executor.py`): Order placement with safety checks
- **Position Tracker** (`positions.py`): Real-time position monitoring
- **Risk Manager** (`risk.py`): Pre-trade risk checks, circuit breakers

### 4. Tools for Claude

**Location**: `src/tools/`

Custom tools that Claude can use during each session:

```python
# Market Data Tools
get_current_price(symbol: str) -> float
get_market_data(symbol: str, timeframe: str, limit: int) -> DataFrame
get_orderbook(symbol: str, depth: int) -> dict
analyze_technicals(symbol: str) -> dict

# Trading Tools
execute_trade(symbol: str, side: str, size: float, order_type: str) -> dict
close_position(position_id: str) -> dict
update_stop_loss(position_id: str, price: float) -> dict

# Analysis Tools
analyze_performance() -> dict
backtest_strategy(code: str, params: dict) -> dict
calculate_portfolio_metrics() -> dict
analyze_correlation(symbols: list) -> dict

# Research Tools
research_topic(topic: str) -> str  # Web search + analysis
fetch_market_news(symbols: list) -> list
analyze_sentiment(symbol: str) -> dict

# State Management Tools
update_strategy(strategy_name: str, updates: dict) -> bool
add_research_note(topic: str, findings: str) -> bool
log_decision(decision: str, reasoning: str) -> bool
```

### 5. Strategy Framework

**Location**: `src/strategies/`

Framework for Claude to develop and deploy strategies:

```python
class BaseStrategy:
    """Base class for all trading strategies."""

    def __init__(self, name: str, params: dict):
        self.name = name
        self.params = params
        self.performance = {}

    def analyze(self, market_data: dict) -> dict:
        """Analyze market and return signals."""
        raise NotImplementedError

    def generate_signals(self) -> list:
        """Generate trading signals."""
        raise NotImplementedError

    def execute(self, signals: list) -> list:
        """Execute trades based on signals."""
        raise NotImplementedError
```

Claude can write strategies that inherit from this base class and deploy them.

## Execution Flow in Detail

### Each 30-Minute Session

1. **Initialization** (5 seconds)
   - Load `firm_state.json`
   - Initialize exchange connections
   - Fetch current wallet balance
   - Update position prices

2. **Context Preparation** (5 seconds)
   - Calculate current portfolio value
   - Update unrealized P&L for open positions
   - Check risk limit utilization
   - Prepare summary of recent activity

3. **Claude Invocation** (60-120 seconds)
   - Claude receives comprehensive context
   - Claude has access to all tools
   - Claude autonomously:
     - Analyzes current positions
     - Reviews strategy performance
     - Researches new opportunities
     - Makes trading decisions
     - Updates strategies
     - Plans next priorities

4. **State Persistence** (5 seconds)
   - Save all updates to `firm_state.json`
   - Backup previous state
   - Log session summary

5. **Cleanup and Exit** (5 seconds)
   - Close connections
   - Log metrics
   - Exit cleanly for next invocation

### Claude's Decision Making Process

Claude follows this general framework each session:

```
1. ASSESS CURRENT STATE
   - Review open positions and P&L
   - Check strategy performance
   - Review risk limit utilization
   - Check alerts and priorities from last session

2. ANALYZE MARKET CONDITIONS
   - Get current prices for tracked assets
   - Review market volatility
   - Check for significant news/events
   - Analyze correlations

3. MAKE DECISIONS
   - Should I close any positions? (take profit/stop loss)
   - Should I adjust existing positions?
   - Should I enter new positions?
   - Should I modify any strategies?
   - Should I research new opportunities?

4. EXECUTE ACTIONS
   - Execute trades (with risk checks)
   - Update strategy parameters
   - Log decisions and reasoning

5. RESEARCH & PLAN
   - Conduct research on identified opportunities
   - Backtest new strategy ideas
   - Plan priorities for next session

6. UPDATE STATE
   - Log all activities
   - Set priorities for next run
   - Update decision log with outcomes
```

## Safety and Risk Management

### Multi-Layer Risk Controls

**Layer 1: Pre-Trade Validation**
- Verify sufficient balance
- Check position size limits
- Verify total exposure limits
- Sanity check prices (vs recent average)
- Check for duplicate orders

**Layer 2: Position-Level Limits**
- Max position size: $1,000 (configurable)
- Max leverage: 1.0x (no leverage initially)
- Max positions: 5 concurrent

**Layer 3: Portfolio-Level Limits**
- Max total allocated capital: 80% of total
- Max daily loss: $500 (circuit breaker)
- Max drawdown from peak: 20%

**Layer 4: Circuit Breakers**
- Daily loss limit hit → Stop all trading for 24h
- Unusual price movements → Require manual confirmation
- API errors → Pause and alert
- Wallet balance mismatch → Stop and investigate

**Layer 5: Manual Overrides**
- `state/emergency_stop.flag` → Immediately stop all trading
- Risk limits can be updated in config
- Individual strategies can be disabled

### Security Considerations

1. **Private Key Management**
   - Encrypted at rest
   - Never logged
   - Separate encryption key stored securely
   - Consider hardware wallet for production

2. **API Key Management**
   - Stored in environment variables
   - Read-only keys where possible
   - IP whitelist on exchanges

3. **Audit Trail**
   - All decisions logged with reasoning
   - All trades logged with full details
   - All API calls logged
   - Immutable append-only trade history

## Technology Stack

### Core Technologies

- **Python 3.11+**: Main language
- **Anthropic SDK**: Claude API integration
- **ccxt**: Exchange connectivity (supports 100+ exchanges)
- **web3.py**: Blockchain/wallet interaction
- **pandas**: Data analysis
- **ta-lib** or **pandas-ta**: Technical indicators
- **SQLite**: Optional structured storage for trade history

### Infrastructure

- **Scheduler**: systemd timer or cron
- **Environment**: Linux server or container
- **Monitoring**: Custom logging + optional integration with monitoring tools
- **Backups**: Automated state backups before each run

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] State management system
- [ ] Main loop executor
- [ ] Basic wallet integration
- [ ] Simple exchange connector (single exchange)
- [ ] Risk management framework
- [ ] Logging and audit trail

### Phase 2: Trading Capabilities (Week 2)
- [ ] Order execution with safety checks
- [ ] Position tracking
- [ ] Performance analytics
- [ ] Market data tools
- [ ] Basic technical analysis

### Phase 3: Claude Integration (Week 3)
- [ ] Tool interface for Claude
- [ ] Context preparation system
- [ ] Claude invocation loop
- [ ] State updates and persistence
- [ ] Testing with paper trading

### Phase 4: Strategy Framework (Week 4)
- [ ] Base strategy class
- [ ] Strategy registry
- [ ] Backtesting framework
- [ ] Strategy deployment system

### Phase 5: Advanced Features (Week 5+)
- [ ] Multiple exchange support
- [ ] Advanced risk management
- [ ] Research tools (web search, news, sentiment)
- [ ] Performance optimization
- [ ] Dashboard/monitoring UI

## Initial Deployment

### Startup Sequence

1. **Initialize Firm**
   ```bash
   python scripts/initialize_firm.py \
     --name "Claude Capital" \
     --initial-capital 10000 \
     --wallet-key-path /path/to/encrypted/key
   ```

2. **Configure Risk Limits**
   - Edit `config/risk_limits.json`
   - Set conservative limits initially

3. **Start Scheduler**
   ```bash
   # Install systemd timer
   sudo systemctl enable claude-capital.timer
   sudo systemctl start claude-capital.timer
   ```

4. **Monitor First Runs**
   - Watch logs for first few sessions
   - Verify state updates correctly
   - Test emergency stop mechanism

### Claude's Initial Prompt

Each session, Claude receives:

```
You are Claude Capital, an autonomous AI trading firm.

CURRENT STATE:
- Total Capital: $10,500 (+5.0%)
- Open Positions: 1 (BTC long, +$50 unrealized)
- Active Strategies: 1 (momentum_v1, +$150 realized)
- Risk Utilization: 25% of max

LAST SESSION PRIORITIES:
1. Monitor BTC position for exit signal
2. Research ETH mean reversion opportunity
3. Analyze portfolio correlation

YOUR TOOLS:
[List of available trading, analysis, and research tools]

YOUR TASK:
Analyze the current state, make trading decisions, research opportunities,
and update strategies as you see fit. You have full autonomy within the
defined risk limits.

Remember:
- Log all decisions with clear reasoning
- Consider risk-adjusted returns
- Research before deploying new strategies
- Set priorities for the next session
```

## Monitoring and Maintenance

### Key Metrics to Track

- Total capital and P&L
- Win rate and Sharpe ratio
- Number of active strategies
- Risk limit utilization
- Session execution time
- API call success rates

### Regular Maintenance

- **Daily**: Review decision log and trades
- **Weekly**: Analyze strategy performance, adjust risk limits if needed
- **Monthly**: Review overall performance, consider capital adjustments
- **Quarterly**: Architecture review and improvements

## Future Enhancements

1. **Multi-chain support**: Expand beyond Ethereum
2. **DeFi integration**: Access DEXs, yield farming, etc.
3. **Machine learning**: Train custom models for predictions
4. **Social trading**: Analyze and mirror successful traders
5. **Advanced research**: Integration with research databases, academic papers
6. **Risk modeling**: VaR, stress testing, scenario analysis
7. **Optimization**: Genetic algorithms for strategy optimization
8. **Dashboard**: Real-time monitoring web interface

## Conclusion

This architecture enables Claude Code to operate as a truly autonomous trading firm, with the freedom to research, develop, and deploy strategies while operating within robust safety constraints. The state-based design allows Claude to build institutional knowledge over time, learning from past decisions and continuously improving its approach to trading.
