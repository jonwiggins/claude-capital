# Making Claude Capital Truly Autonomous

This document describes how to make Claude Code run autonomously on a loop, picking up where it left off and making independent trading decisions.

## Core Concept

The current implementation provides the **infrastructure** for autonomous trading. To make it truly autonomous, we need Claude Code to:

1. Read the current state
2. Analyze the situation independently
3. Make trading decisions
4. Execute actions using the trading tools
5. Save state for the next iteration
6. Set priorities for future runs

## Implementation Approaches

### Approach 1: Claude Code Extended Sessions

Use Claude Code's ability to maintain extended working sessions with tool access:

```python
# In src/tools/claude_interface.py

from anthropic import Anthropic

class ClaudeSession:
    def run(self, context: str) -> Dict[str, Any]:
        """Run an autonomous Claude Code session."""

        # Initialize Claude with extended thinking
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8000,
            thinking={
                "type": "enabled",
                "budget_tokens": 5000
            },
            messages=[
                {
                    "role": "user",
                    "content": context
                }
            ],
            tools=TRADING_TOOLS
        )

        # Process Claude's response and tool calls
        actions = []
        conversation = [{"role": "user", "content": context}]

        while True:
            # Add assistant response
            conversation.append({
                "role": "assistant",
                "content": response.content
            })

            # Check if Claude wants to use tools
            tool_use_blocks = [
                block for block in response.content
                if block.type == "tool_use"
            ]

            if not tool_use_blocks:
                # Claude is done
                break

            # Execute tools
            tool_results = []
            for tool_use in tool_use_blocks:
                result = self._execute_tool(
                    tool_use.name,
                    tool_use.input
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(result)
                })
                actions.append(f"{tool_use.name}:{tool_use.input}")

            # Continue conversation with tool results
            conversation.append({
                "role": "user",
                "content": tool_results
            })

            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8000,
                messages=conversation,
                tools=TRADING_TOOLS
            )

        # Extract next priorities from final response
        next_priorities = self._extract_priorities(response.content)

        return {
            "actions": actions,
            "next_priorities": next_priorities,
            "conversation": conversation
        }
```

### Approach 2: Claude Code CLI Integration

Use the Claude Code CLI itself to run autonomous sessions:

```python
# In src/loop.py

import subprocess
import json

class TradingLoop:
    def run_claude_session(self, context: str) -> Dict[str, Any]:
        """Run Claude Code CLI with trading context."""

        # Create a task file for Claude
        task_file = "state/current_task.md"
        with open(task_file, 'w') as f:
            f.write(f"""# Trading Session Task

{context}

## Your Tools

You have access to the following tools via the TradingTools class:

- `get_current_price(symbol, exchange)`: Get current price
- `get_market_data(symbol, timeframe, limit)`: Get OHLCV data
- `execute_trade(symbol, side, size, ...)`: Execute a trade
- `analyze_performance()`: Review performance
- `log_decision(decision, reasoning)`: Log your decision

## Instructions

1. Analyze the current state carefully
2. Research market opportunities
3. Make trading decisions based on your analysis
4. Execute trades if appropriate
5. Log all decisions with clear reasoning
6. Set priorities for the next session

## Next Priorities from Last Session

{self._format_priorities(context)}

Execute your trading strategy autonomously within the risk limits.
""")

        # Run Claude Code with the task
        result = subprocess.run(
            ["claude-code", "run", task_file],
            capture_output=True,
            text=True
        )

        # Parse Claude's actions from output
        actions = self._parse_claude_output(result.stdout)

        return {
            "actions": actions,
            "output": result.stdout
        }
```

### Approach 3: MCP (Model Context Protocol) Integration

Use MCP servers to provide Claude with direct access to trading tools:

```python
# Create an MCP server for trading tools
# mcp_server/trading_server.py

from mcp import Server, Tool

server = Server("claude-capital-trading")

@server.tool("get_current_price")
async def get_current_price(symbol: str, exchange: str = "binance"):
    """Get current price for a symbol."""
    # Implementation using TradingTools
    return tools.get_current_price(symbol, exchange)

@server.tool("execute_trade")
async def execute_trade(
    symbol: str,
    side: str,
    size: float,
    strategy: str = "manual"
):
    """Execute a trade with risk validation."""
    return tools.execute_trade(symbol, side, size, strategy=strategy)

# Run MCP server
server.run()
```

Then configure Claude Code to use this MCP server for autonomous trading.

## Enhanced State Continuity

To ensure Claude truly "picks up where it left off":

### 1. Context Windows

Maintain a rolling context window:

```python
def _prepare_claude_context(self, state: Dict[str, Any]) -> str:
    """Prepare comprehensive context for Claude."""

    context = f"""# Claude Capital Trading Session

## Your Identity
You are Claude Capital's AI trading system. You have been running autonomously
since {state['firm']['inception_date']}. This is session #{len(state['session_log']) + 1}.

## Session Continuity
Last session: {state['session_log'][-1]['timestamp'] if state['session_log'] else 'First session'}
Last actions: {state['session_log'][-1]['actions_taken'] if state['session_log'] else 'None'}

## Priority Tasks for This Session
"""

    # Include priorities from last session
    if state['session_log']:
        priorities = state['session_log'][-1].get('next_priorities', [])
        for i, priority in enumerate(priorities, 1):
            context += f"{i}. {priority}\n"
    else:
        context += """This is your first session! You should:
1. Familiarize yourself with available markets
2. Research current market conditions
3. Develop your initial trading strategy
4. Consider making your first trade (small size to start)
"""

    # Add comprehensive state information
    context += self._format_current_state(state)
    context += self._format_recent_decisions(state)
    context += self._format_performance_summary(state)

    return context
```

### 2. Decision History

Include recent decisions for learning:

```python
def _format_recent_decisions(self, state: Dict[str, Any]) -> str:
    """Format recent decisions for context."""

    context = "\n## Your Recent Decisions\n"

    for decision in state['decision_log'][-5:]:
        outcome = decision.get('actual_outcome', 'pending')
        context += f"""
- {decision['timestamp'][:10]}: {decision['decision']}
  Reasoning: {decision['reasoning']}
  Confidence: {decision['confidence']:.0%}
  Outcome: {outcome}
"""

    return context
```

### 3. Research Memory

Maintain research notes across sessions:

```python
def _format_research_memory(self, state: Dict[str, Any]) -> str:
    """Format research notes for continuity."""

    context = "\n## Your Research Notes\n"

    for research in state['research_log'][-10:]:
        context += f"""
### {research['topic']} ({research['timestamp'][:10]})
{research['findings']}
Action taken: {research.get('action_taken', 'None yet')}
Outcome: {research.get('outcome', 'TBD')}
"""

    return context
```

## Autonomous Decision Framework

Give Claude a clear decision framework:

```python
DECISION_FRAMEWORK = """
## Your Decision Framework

For each session, follow this process:

1. **ASSESS CURRENT STATE** (5 min thinking time)
   - Review all open positions and their P&L
   - Check strategy performance metrics
   - Evaluate risk limit utilization
   - Review priorities from last session

2. **ANALYZE MARKETS** (10 min)
   - Get current prices for tracked assets
   - Review market volatility and trends
   - Check for significant news or events
   - Identify potential opportunities

3. **MAKE DECISIONS** (10 min)
   - Should I close any positions? (TP/SL)
   - Should I adjust position sizes?
   - Should I enter new positions?
   - Should I modify strategies?
   - Should I conduct research?

4. **EXECUTE ACTIONS** (5 min)
   - Execute trades (always use log_decision first)
   - Update strategy parameters
   - Close positions if needed
   - Log all actions with reasoning

5. **RESEARCH & PLAN** (5 min)
   - Conduct research on new opportunities
   - Backtest strategy ideas
   - Set clear priorities for next session
   - Document lessons learned

## Decision Quality Checklist

Before executing any trade, verify:
- [ ] Clear reasoning documented
- [ ] Risk limits checked
- [ ] Position size appropriate
- [ ] Entry/exit plan defined
- [ ] Fits overall strategy
"""
```

## Monitoring Autonomous Operations

### Session Analytics

Track Claude's decision quality:

```python
def analyze_session_quality(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the quality of autonomous decisions."""

    decisions = state['decision_log']
    trades = state['trade_history']

    return {
        "decision_velocity": len(decisions) / len(state['session_log']),
        "trade_velocity": len(trades) / len(state['session_log']),
        "avg_confidence": np.mean([d['confidence'] for d in decisions]),
        "decision_quality": calculate_decision_quality(decisions),
        "learning_curve": analyze_learning_progression(decisions)
    }
```

### Alert System

Alert on unusual autonomous behavior:

```python
def check_autonomous_health(state: Dict[str, Any]) -> List[str]:
    """Check for concerning autonomous behavior."""

    alerts = []

    # Check decision rate
    recent_sessions = state['session_log'][-10:]
    avg_decisions = np.mean([
        len(s.get('actions_taken', []))
        for s in recent_sessions
    ])

    if avg_decisions > 10:
        alerts.append("High decision velocity - review for overtrading")

    # Check reasoning quality
    recent_decisions = state['decision_log'][-20:]
    low_confidence = [d for d in recent_decisions if d['confidence'] < 0.3]

    if len(low_confidence) > 5:
        alerts.append("Many low-confidence decisions - may need guidance")

    return alerts
```

## Production Deployment

### Systemd Service

Create a systemd service for continuous operation:

```ini
# /etc/systemd/system/claude-capital.service

[Unit]
Description=Claude Capital Autonomous Trading
After=network.target

[Service]
Type=simple
User=trading
WorkingDirectory=/opt/claude-capital
ExecStart=/opt/claude-capital/venv/bin/python src/loop.py
Restart=always
RestartSec=1800
StandardOutput=append:/var/log/claude-capital/output.log
StandardError=append:/var/log/claude-capital/error.log

[Install]
WantedBy=multi-user.target
```

### Systemd Timer

Run every 30 minutes:

```ini
# /etc/systemd/system/claude-capital.timer

[Unit]
Description=Claude Capital Trading Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable claude-capital.timer
sudo systemctl start claude-capital.timer
```

## Advanced Autonomous Features

### 1. Self-Improvement Loop

Let Claude improve its own strategies:

```python
def enable_self_improvement(state: Dict[str, Any]) -> None:
    """Allow Claude to modify strategies based on performance."""

    # Add self-improvement task to context
    if len(state['trade_history']) >= 100:
        state['session_log'][-1]['next_priorities'].insert(0,
            "Review strategy performance and optimize underperforming strategies"
        )
```

### 2. Research Automation

Integrate web research for autonomous learning:

```python
def autonomous_research(topic: str) -> Dict[str, Any]:
    """Conduct autonomous research on a topic."""

    # Use web search to gather information
    search_results = search_web(topic)

    # Use Claude to analyze and synthesize
    analysis = claude_analyze_research(search_results)

    return {
        "topic": topic,
        "sources": search_results,
        "findings": analysis,
        "trading_implications": extract_implications(analysis)
    }
```

### 3. Portfolio Rebalancing

Let Claude autonomously rebalance:

```python
def autonomous_rebalancing(state: Dict[str, Any]) -> List[Dict]:
    """Generate rebalancing actions based on portfolio analysis."""

    # Claude analyzes portfolio composition
    current_allocation = analyze_portfolio(state['positions'])
    optimal_allocation = claude_optimize_portfolio(current_allocation)

    # Generate rebalancing trades
    rebalancing_trades = generate_rebalancing_trades(
        current_allocation,
        optimal_allocation
    )

    return rebalancing_trades
```

## Best Practices for Autonomous Operation

1. **Start Conservative**: Begin with very tight risk limits
2. **Monitor Closely**: Review every decision for the first week
3. **Gradual Autonomy**: Slowly relax constraints as confidence grows
4. **Decision Audits**: Regularly review decision quality
5. **Kill Switches**: Always have multiple ways to stop trading
6. **Backup State**: Automated backups before each session
7. **Performance Bounds**: Auto-pause if performance degrades
8. **Regular Reviews**: Weekly human review of autonomous decisions

## Conclusion

The infrastructure is in place for fully autonomous trading. The key to success is:

1. **Clear Context**: Give Claude comprehensive state information
2. **Good Tools**: Provide reliable, well-validated trading tools
3. **Safety Rails**: Maintain strict risk management
4. **Monitoring**: Watch autonomous behavior closely
5. **Iteration**: Continuously improve based on performance

Start conservative, monitor closely, and gradually increase autonomy as you gain confidence in Claude's decision-making abilities.

---

**Remember**: Full autonomy means Claude makes real trading decisions with real money. Start small, test thoroughly, and always maintain proper risk controls.
