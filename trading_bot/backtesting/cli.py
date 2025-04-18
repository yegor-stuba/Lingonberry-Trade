"""
Command-line interface for backtesting
"""

import argparse
import asyncio
import logging
import json
import os
from typing import List, Dict
import pandas as pd
import matplotlib.pyplot as plt

from trading_bot.backtesting.engine import BacktestEngine

logger = logging.getLogger(__name__)

async def run_backtest(symbol: str, timeframes: List[str], period: str, market_type: str,
                     initial_capital: float, risk_per_trade: float, output_dir: str):
    """
    Run a backtest and save results
    
    Args:
        symbol (str): Trading symbol
        timeframes (list): List of timeframes
        period (str): Time period
        market_type (str): Market type
        initial_capital (float): Initial capital
        risk_per_trade (float): Risk percentage per trade
        output_dir (str): Output directory
    """
    # Create backtest engine
    engine = BacktestEngine()
    
    # Run multi-timeframe backtest
    results = await engine.run_multi_timeframe_backtest(
        symbol=symbol,
        timeframes=timeframes,
        period=period,
        market_type=market_type,
        initial_capital=initial_capital,
        risk_per_trade=risk_per_trade
    )
    
    if not results.get('success', False):
        logger.error(f"Backtest failed: {results.get('message', 'Unknown error')}")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save results as JSON
    results_copy = results.copy()
    results_copy.pop('df', None)  # Remove DataFrame from results
    
    with open(os.path.join(output_dir, f"{symbol}_{period}_results.json"), 'w') as f:
        # Convert dates to strings
        for trade in results_copy['trades']:
            trade['entry_date'] = str(trade['entry_date'])
            trade['exit_date'] = str(trade['exit_date'])
        
        json.dump(results_copy, f, indent=2)
    
    # Generate and save equity curve
    plt.figure(figsize=(12, 6))
    plt.plot(results['equity'])
    plt.title(f"Equity Curve - {symbol} ({', '.join(timeframes)})")
    plt.xlabel("Trade Number")
    plt.ylabel("Equity")
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, f"{symbol}_{period}_equity.png"))
    
    # Generate and save trade chart
    chart_buf = await engine.generate_chart(with_analysis=True)
    if chart_buf:
        with open(os.path.join(output_dir, f"{symbol}_{period}_chart.png"), 'wb') as f:
            f.write(chart_buf.getvalue())
    
    # Print summary
    print("\n===== BACKTEST RESULTS =====")
    print(f"Symbol: {symbol}")
    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"Period: {period}")
    print(f"Initial Capital: ${initial_capital:.2f}")
    print(f"Final Capital: ${results['final_capital']:.2f}")
    print(f"Profit/Loss: ${results['profit']:.2f} ({results['profit_pct']:.2f}%)")
    print(f"Total Trades: {results['trade_count']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Average RR: {results['avg_rr']:.2f}")
    print("============================\n")

def main():
    """Main function for CLI"""
    parser = argparse.ArgumentParser(description="Run backtests with the trading bot")
    
    parser.add_argument("--symbol", type=str, required=True, help="Trading symbol (e.g., EURUSD)")
    parser.add_argument("--timeframes", type=str, required=True, help="Comma-separated list of timeframes (e.g., 1h,4h,1d)")
    parser.add_argument("--period", type=str, default="1y", help="Time period (e.g., 1m, 3m, 6m, 1y, 2y)")
    parser.add_argument("--market", type=str, default="forex", help="Market type (forex, crypto, indices, metals)")
    parser.add_argument("--capital", type=float, default=10000.0, help="Initial capital")
    parser.add_argument("--risk", type=float, default=1.0, help="Risk percentage per trade")
    parser.add_argument("--output", type=str, default="./backtest_results", help="Output directory")
    
    args = parser.parse_args()
    
    # Parse timeframes
    timeframes = args.timeframes.split(',')
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run backtest
    asyncio.run(run_backtest(
        symbol=args.symbol,
        timeframes=timeframes,
        period=args.period,
        market_type=args.market,
        initial_capital=args.capital,
        risk_per_trade=args.risk,
        output_dir=args.output
    ))

if __name__ == "__main__":
    main()
