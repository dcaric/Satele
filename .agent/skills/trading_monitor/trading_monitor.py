import urllib.request
import json
from datetime import datetime
import sys

def format_currency(value):
    return f"${value:,.2f}"

def format_percent(value):
    return f"{value:.2f}%"

def get_trading_data():
    url = "https://dariocaric.net/tradingpreview/data.json"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
            else:
                print(f"Error: Received status code {response.status}")
                return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def main():
    data = get_trading_data()
    if not data:
        return

    # Use current_equity as primary, fallback to old keys if any
    current_equity = data.get("current_equity", 0)
    daily_roi = data.get("daily_roi_pct", 0)
    win_rate = data.get("win_rate", 0)
    last_updated = data.get("last_updated", "Unknown")
    
    # Try to parse the date for a nicer display
    try:
        # data.json date: "2026-02-20T22:16:17.034971"
        dt = datetime.fromisoformat(last_updated.split('.')[0])
        last_updated_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        last_updated_str = last_updated

    # Get history for the Alpaca chart summary
    alpaca_history = data.get("alpaca_history", [])
    history_summary = ""
    if alpaca_history:
        recent = alpaca_history[-5:] # Last 5 points
        history_summary = "\nRecent Alpaca Trend:\n"
        for entry in recent:
            history_summary += f"- {entry['date']}: {format_currency(entry['total'])}\n"

    # Print core stats
    print(f"📊 **Trading Performance Summary** 📊")
    print(f"------------------------------------")
    print(f"💰 **Total Equity:** {format_currency(current_equity)}")
    print(f"📈 **Daily ROI:** {format_percent(daily_roi)}")
    print(f"🏆 **Win Rate:** {format_percent(win_rate)}")
    print(f"🕒 **Last Updated:** {last_updated_str}")
    print(f"------------------------------------")
    
    if history_summary:
        print(history_summary)

if __name__ == "__main__":
    main()
