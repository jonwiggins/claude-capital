# Claude Capital - Setup Guide

This guide will walk you through setting up your autonomous AI trading firm powered by Claude Code.

## Prerequisites

Before you begin, ensure you have:

- Python 3.11 or higher
- An Anthropic API key (sign up at https://console.anthropic.com)
- A cryptocurrency exchange account (e.g., Binance) with API keys
- Basic understanding of cryptocurrency trading
- A crypto wallet (or create a new one during setup)

## Installation Steps

### 1. Clone and Install Dependencies

```bash
# Navigate to the project directory
cd claude-capital

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Anthropic API
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Exchange API Keys (Binance example)
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key

# Environment
ENVIRONMENT=development  # Use 'production' when ready for live trading
LOG_LEVEL=INFO
```

**Important:** In development mode, the system will use exchange testnets (paper trading) if available.

### 3. Initialize Your Trading Firm

You have two options:

#### Option A: Create a New Wallet

```bash
python scripts/initialize_firm.py \
  --name "Claude Capital" \
  --initial-capital 10000 \
  --create-wallet \
  --chain ethereum
```

This will:
- Create a new Ethereum wallet
- Display the wallet address and private key
- Encrypt and save the private key
- Initialize the firm state

**⚠️ CRITICAL:** Save the encryption key shown! Add it to your `.env` file:

```bash
WALLET_ENCRYPTION_KEY=your_encryption_key_here
```

#### Option B: Use Existing Wallet

```bash
python scripts/initialize_firm.py \
  --name "Claude Capital" \
  --initial-capital 10000 \
  --wallet-address 0xYourWalletAddress \
  --wallet-key your_private_key_here \
  --chain ethereum
```

### 4. Verify Setup

Test that everything is working:

```bash
# Run a single trading session
python src/loop.py
```

You should see:
- State loaded successfully
- Claude analyzing the situation
- Session completed without errors

Check the logs:
```bash
cat logs/session_$(date +%Y%m%d).log
```

### 5. Set Up Scheduler (Optional)

For autonomous operation, set up a cron job to run every 30 minutes:

```bash
crontab -e
```

Add this line (replace `/path/to/claude-capital` with actual path):

```bash
*/30 * * * * cd /path/to/claude-capital && /path/to/claude-capital/venv/bin/python src/loop.py >> logs/cron.log 2>&1
```

Or use systemd timer (see `docs/systemd-setup.md` for details).

## Configuration

### Risk Limits

The default risk limits are defined in `state/firm_state.json` under `risk_limits`:

```json
{
  "max_position_size_usd": 1000,
  "max_total_positions": 5,
  "max_daily_loss_usd": 500,
  "max_total_allocated_pct": 0.8,
  "max_leverage": 1.0
}
```

**Recommended for beginners:**
- Start with small position sizes ($100-$500)
- Limit total positions to 2-3
- Set conservative daily loss limits ($50-$100)
- Use no leverage (1.0x)

### Exchange Configuration

To add multiple exchanges, add their API keys to `.env`:

```bash
# Coinbase
COINBASE_API_KEY=your_key
COINBASE_SECRET_KEY=your_secret

# Kraken
KRAKEN_API_KEY=your_key
KRAKEN_SECRET_KEY=your_secret
```

The system will automatically detect and connect to configured exchanges.

## Safety Features

### Emergency Stop

To immediately halt all trading:

```bash
touch state/emergency_stop.flag
```

To resume:

```bash
rm state/emergency_stop.flag
```

Or edit `state/firm_state.json` and set `system.emergency_stop` to `false`.

### Circuit Breakers

The system has automatic circuit breakers that will stop trading if:
- Daily loss limit is exceeded
- Maximum drawdown threshold is reached
- Unusual market conditions are detected

When a circuit breaker trips, check the logs and `state/firm_state.json` for details.

## Monitoring

### View Current State

```bash
# Overall performance
cat state/firm_state.json | jq '.performance'

# Current positions
cat state/firm_state.json | jq '.positions'

# Recent trades
cat state/firm_state.json | jq '.trade_history | .[-5:]'

# Risk utilization
cat state/firm_state.json | jq '.capital'
```

### Logs

- Session logs: `logs/session_YYYYMMDD.log`
- Trade log: `logs/trades.log`
- Cron log (if using cron): `logs/cron.log`

### Real-time Monitoring

```bash
# Watch session logs
tail -f logs/session_$(date +%Y%m%d).log

# Watch trades
tail -f logs/trades.log
```

## Usage

### How It Works

1. **Every 30 minutes** (or your configured interval), the main loop executes
2. **Load State**: Current firm state is loaded from disk
3. **Update Prices**: All position prices are updated from exchanges
4. **Safety Checks**: Circuit breakers and risk limits are checked
5. **Claude Session**: Claude analyzes the situation with full context
6. **Decision Making**: Claude can:
   - Analyze market conditions
   - Research trading opportunities
   - Execute trades (buy/sell)
   - Update strategies
   - Close positions
7. **State Saved**: All updates are persisted to disk
8. **Logging**: Actions and decisions are logged

### What Claude Can Do

Claude has full autonomy to:
- ✅ Research market opportunities
- ✅ Develop trading strategies
- ✅ Execute trades within risk limits
- ✅ Close positions (take profit/stop loss)
- ✅ Adjust position sizes
- ✅ Log decisions with reasoning
- ✅ Set priorities for next session

Claude **cannot**:
- ❌ Exceed position size limits
- ❌ Trade when circuit breaker is active
- ❌ Use leverage (unless configured)
- ❌ Trade without risk validation

### Example Session Flow

```
1. Claude analyzes current state:
   - $10,000 capital, no positions
   - No active strategies yet

2. Claude decides to research:
   - Checks BTC price and trend
   - Reviews market volatility
   - Identifies momentum opportunity

3. Claude develops a strategy:
   - Creates "momentum_v1" strategy
   - Sets parameters and rules

4. Claude executes:
   - Buys 0.1 BTC at $50,000
   - Logs decision with reasoning
   - Sets stop loss and take profit targets

5. Claude plans next session:
   - Monitor BTC position
   - Research ETH opportunity
   - Analyze correlation with indices
```

## Testing

### Paper Trading

Always start in `development` mode:

```bash
# In .env
ENVIRONMENT=development
```

This enables testnet mode on supported exchanges (paper trading with fake money).

### Recommended Testing Sequence

1. **Day 1**: Run manually, observe Claude's decisions
2. **Day 2-3**: Run every 4 hours, monitor closely
3. **Day 4-7**: Run every 2 hours, verify risk controls
4. **Week 2**: Enable 30-minute interval
5. **Week 3**: Consider production with small capital

### What to Monitor

- Are Claude's decisions logical?
- Are risk limits being respected?
- Is the state being saved correctly?
- Are trades executing as expected?
- Are logs detailed enough?

## Troubleshooting

### "State file not found"

Run the initialization script:
```bash
python scripts/initialize_firm.py --initial-capital 10000 --create-wallet
```

### "ANTHROPIC_API_KEY not set"

Add your API key to `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### "Failed to connect to exchange"

Check:
1. API keys are correct in `.env`
2. API keys have trading permissions
3. IP whitelist (if configured on exchange)
4. Exchange is not under maintenance

### "Circuit breaker tripped"

This is a safety feature. Check:
1. Why it tripped: `cat state/firm_state.json | jq '.system.alerts'`
2. Current losses: `cat state/firm_state.json | jq '.performance'`
3. Reset if safe: `rm state/emergency_stop.flag`

### Positions not updating

1. Check exchange connectivity
2. Verify API keys have read permissions
3. Check logs for errors

## Advanced Configuration

### Custom Trading Hours

Edit your cron job to only run during specific hours:

```bash
# Only run 9 AM - 5 PM EST on weekdays
*/30 9-17 * * 1-5 cd /path/to/claude-capital && python src/loop.py
```

### Multiple Instances

To run multiple independent trading firms:

```bash
# Firm 1 (conservative)
FIRM_NAME=conservative STATE_DIR=state/conservative python src/loop.py

# Firm 2 (aggressive)
FIRM_NAME=aggressive STATE_DIR=state/aggressive python src/loop.py
```

### Custom Risk Limits

Edit `state/firm_state.json` and modify `risk_limits`:

```json
{
  "risk_limits": {
    "max_position_size_usd": 500,
    "max_total_positions": 3,
    "max_daily_loss_usd": 100,
    "max_total_allocated_pct": 0.5
  }
}
```

## Best Practices

### 🔒 Security

- Never commit `.env` or `secrets/` to version control
- Regularly backup `state/` directory
- Use API keys with minimum required permissions
- Enable IP whitelist on exchanges
- Use hardware wallet for large amounts

### 💰 Risk Management

- Start with capital you can afford to lose
- Begin with very conservative limits
- Gradually increase limits as you gain confidence
- Always monitor performance regularly
- Set up alerts for large losses

### 📊 Monitoring

- Review logs daily
- Check decision quality weekly
- Analyze strategy performance monthly
- Backup state before making changes

### 🧪 Development

- Always test on testnet first
- Make one change at a time
- Document strategy modifications
- Keep old versions for rollback

## Getting Help

- Check logs first: `logs/session_*.log`
- Review state: `cat state/firm_state.json | jq`
- Check architecture: `ARCHITECTURE.md`
- Open an issue if you find bugs

## What's Next?

Once you're comfortable with the basics:

1. **Develop Strategies**: Let Claude research and create trading strategies
2. **Backtest**: Test strategies on historical data before deploying
3. **Multi-Exchange**: Add more exchanges for better opportunities
4. **Advanced Analytics**: Implement custom performance metrics
5. **Machine Learning**: Integrate prediction models
6. **Dashboard**: Build a monitoring UI

## ⚠️ Disclaimer

**This is experimental software. Cryptocurrency trading is risky.**

- Never trade with money you can't afford to lose
- The autonomous nature means Claude makes decisions without approval
- Start small and monitor closely
- Past performance doesn't guarantee future results
- You are responsible for all trades executed by the system

By using this software, you acknowledge these risks and agree to use it responsibly.

---

**Happy Trading! 🚀**

For more details, see:
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [README.md](README.md) - Project overview
