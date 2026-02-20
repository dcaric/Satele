---
name: Trading Monitor
description: Fetch trading performance statistics (Total Equity, ROI, Win Rate) from the dariocaric.net dashboard data.
---

# Trading Monitor Skill

This skill allows Satele to monitor the trading bot's performance by parsing the live JSON data from `https://dariocaric.net/tradingpreview/data.json`.

## Capabilities

1. **Check Equity**: Get the current "Total Equity" of the trading account.
2. **Performance Summary**: Get a snapshot of ROI, Win Rate, and the latest update time.
3. **Historical Trend**: View the recent history from the Alpaca Brokerage account.

## Tools
The agent can use the following script:
`python3 .agent/skills/trading_monitor/trading_monitor.py`

## Usage Examples

- "What is my current total equity?"
- "How is my trading bot performing today?"
- "Show me the trading performance stats."
- "When was the trading dashboard last updated?"

## Example
If a user says "show trading stats", the agent should:
1. Run `python3 .agent/skills/trading_monitor/trading_monitor.py`
2. Reply with the output.
