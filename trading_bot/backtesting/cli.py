"""
Command-line interface for backtesting
"""

import argparse
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

from trading_bot.backtesting.backtest import Backtester
from trading_bot.config import settings

logger = logging.getLogger(__name__)

async def main():
    """Main function for the CLI"""
    parser = argparse.ArgumentParser(description='Trading Bot Backtester')
    
    # Required arguments
    parser.add_argument('--market', type=str, required=True, choices=['forex', 'crypto', 'indices', 'metals'],
                        help='Market type')
    parser.add_argument('--symbol', type=str, required=True,
                        help='Trading symbol')
    parser.add_argument('--timeframe', type=str, required=True,
                        help='Timeframe for analysis')
    
    # Optional arguments
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=10000.0, help='Initial capital')
    parser.add_argument('--risk', type=float, default=1.0, help='Risk percentage per trade')
    parser.add_argument('--optimize', action='store_true', help='Run parameter optimization')
    parser.add_argument('--output', type=str, help='Output file for results')
    
    args = parser.parse_args()
    
    # Initialize backtester
    backtester = Backtester()
    
    # Check if symbol is available
    available_symbols = backtester.get_available_symbols(args.market)
    if args.symbol not in available_symbols:
        print(f"Symbol {args.symbol} not available for {args.market}. Available symbols: {available_symbols}")
        return
    
    # Check if timeframe is available
    available_timeframes = backtester.get_available_timeframes(args.market, args.symbol)
    if args.timeframe not in available_timeframes:
        print(f"Timeframe {args.timeframe} not available for {args.symbol}. Available timeframes: {available_timeframes}")
        return
    
    print(f"Running backtest for {args.symbol} on {args.timeframe} timeframe...")
    
    # Run backtest or optimization
    if args.optimize:
        # Define parameter grid for optimization
        param_grid = {
            'min_strength': [60, 70, 80],
            'min_rr': [1.5, 2.0, 2.5],
            'risk_per_trade': [0.5, 1.0, 2.0]
        }
        
        print("Running parameter optimization...")
        results = await backtester.optimize_strategy(
            market_type=args.market,
            symbol=args.symbol,
            timeframe=args.timeframe,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_capital=args.capital,
            param_grid=param_grid
        )
    else:
        results = await backtester.run_backtest(
            market_type=args.market,
            symbol=args.symbol,
            timeframe=args.timeframe,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_capital=args.capital,
            risk_per_trade=args.risk
        )
    
    if not results.get('success', False):
        print(f"Error: {results.get('message', 'Unknown error')}")
        return
    
    # Print summary
    print("\nBacktest Summary:")
    print(f"Symbol: {results['symbol']}")
    print(f"Timeframe: {results['timeframe']}")
    print(f"Period: {results['start_date']} to {results['end_date']}")
    print(f"Initial Capital: ${results['initial_capital']:,.2f}")
    print(f"Final Capital: ${results['final_capital']:,.2f}")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Total Trades: {results['trade_count']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")
    
    # Save results to file if specified
    if args.output:
        output_path = Path(args.output)
        
        # Create directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove binary data (charts) before saving to JSON
        results_copy = results.copy()
        if 'charts' in results_copy:
            del results_copy['charts']
        
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(results_copy, f, indent=4, default=str)
        
        print(f"\nResults saved to {output_path}")
    
    # Generate report with charts
    report = backtester.generate_report(results)
    
    # Save charts if output is specified
    if args.output and report.get('success', False):
        output_dir = Path(args.output).parent
        
        # Save charts
        for chart_name, chart_data in report.get('charts', {}).items():
            if chart_data:
                chart_path = output_dir / f"{chart_name}.png"
                with open(chart_path, 'wb') as f:
                    f.write(chart_data.getvalue())
                print(f"Chart saved to {chart_path}")

if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the main function
    asyncio.run(main())
