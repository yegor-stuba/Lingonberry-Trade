"""
Script to fetch and save market data for the trading bot
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from trading_bot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_bot.data.data_processor import DataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Fetch and save market data')
parser.add_argument('--symbols', type=str, default='BTCUSD,ETHUSD,EURUSD,GBPUSD,USDJPY,XAUUSD', 
                    help='Comma-separated list of symbols to fetch')
parser.add_argument('--timeframes', type=str, default='M15,H1,H4,D1', 
                    help='Comma-separated list of timeframes to fetch')
parser.add_argument('--count', type=int, default=500, 
                    help='Number of candles to fetch for each symbol/timeframe')
parser.add_argument('--source', type=str, default='auto', choices=['auto', 'csv', 'api', 'ctrader'],
                    help='Data source to use')
args = parser.parse_args()

async def fetch_data():
    """Fetch and save data for all specified symbols and timeframes"""
    processor = DataProcessor()
    
    symbols = args.symbols.split(',')
    timeframes = args.timeframes.split(',')
    
    logger.info(f"Fetching data for {len(symbols)} symbols and {len(timeframes)} timeframes")
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Timeframes: {timeframes}")
    
    for symbol in symbols:
        for timeframe in timeframes:
            logger.info(f"Fetching {args.count} candles for {symbol} {timeframe}...")
            
            try:
                df = await processor.load_data(symbol, timeframe, args.count, args.source)
                
                if df is not None and not df.empty:
                    logger.info(f"Successfully fetched {len(df)} candles for {symbol} {timeframe}")
                    
                    # Get market type
                    market_type = processor._get_market_type(symbol)
                    
                    # Save to CSV
                    processor._save_to_csv(df, symbol, timeframe, market_type)
                else:
                    logger.error(f"Failed to fetch data for {symbol} {timeframe}")
            
            except Exception as e:
                logger.error(f"Error fetching data for {symbol} {timeframe}: {e}")
    
    # Close connections
    await processor.close()

if __name__ == "__main__":
    asyncio.run(fetch_data())
