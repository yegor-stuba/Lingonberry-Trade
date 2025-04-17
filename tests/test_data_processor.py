"""
Test script for the data processor
"""

import os
import sys
import asyncio
import logging
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

# Add the parent directory to the path so we can import from trading_bot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_bot.data.data_processor import DataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_data_loading():
    """Test loading data from different sources"""
    processor = DataProcessor()
    
    # Test symbols for different markets
    test_cases = [
        {'symbol': 'BTCUSD', 'timeframe': 'H1', 'market': 'crypto'},
        {'symbol': 'EURUSD', 'timeframe': 'H1', 'market': 'forex'},
        {'symbol': 'XAUUSD', 'timeframe': 'H1', 'market': 'metals'},
    ]
    
    for case in test_cases:
        symbol = case['symbol']
        timeframe = case['timeframe']
        market = case['market']
        
        logger.info(f"Testing data loading for {symbol} {timeframe} ({market})")
        
        # Try loading from CSV first
        logger.info("Trying to load from CSV...")
        df = processor._load_from_csv(symbol, timeframe, market)
        
        if df is not None and not df.empty:
            logger.info(f"Successfully loaded {len(df)} rows from CSV")
            logger.info(f"Sample data:\n{df.head()}")
        else:
            logger.info("CSV data not available, trying to load from API...")
            df = await processor.load_data(symbol, timeframe)
            
            if df is not None and not df.empty:
                logger.info(f"Successfully loaded {len(df)} rows from API")
                logger.info(f"Sample data:\n{df.head()}")
            else:
                logger.error(f"Failed to load data for {symbol} {timeframe}")
        
        # If we have data, test preprocessing
        if df is not None and not df.empty:
            logger.info("Testing data preprocessing...")
            processed_df = processor.preprocess_data(df)
            logger.info(f"Processed data columns: {processed_df.columns.tolist()}")
            
            # Test adding technical indicators
            logger.info("Testing adding technical indicators...")
            indicators_df = processor.add_technical_indicators(processed_df)
            logger.info(f"Indicators added: {[col for col in indicators_df.columns if col not in processed_df.columns]}")
            
            # Plot the data
            logger.info("Generating plot...")
            plt.figure(figsize=(12, 8))
            
            # Plot price and moving averages
            plt.subplot(3, 1, 1)
            plt.plot(indicators_df.index, indicators_df['close'], label='Close')
            plt.plot(indicators_df.index, indicators_df['sma_20'], label='SMA 20')
            plt.plot(indicators_df.index, indicators_df['sma_50'], label='SMA 50')
            plt.legend()
            plt.title(f"{symbol} {timeframe} - Price and Moving Averages")
            
            # Plot RSI
            plt.subplot(3, 1, 2)
            plt.plot(indicators_df.index, indicators_df['rsi_14'], label='RSI 14')
            plt.axhline(y=70, color='r', linestyle='-')
            plt.axhline(y=30, color='g', linestyle='-')
            plt.legend()
            plt.title("RSI")
            
            # Plot MACD
            plt.subplot(3, 1, 3)
            plt.plot(indicators_df.index, indicators_df['macd_12_26'], label='MACD')
            plt.plot(indicators_df.index, indicators_df['macd_signal'], label='Signal')
            plt.bar(indicators_df.index, indicators_df['macd_hist'], label='Histogram')
            plt.legend()
            plt.title("MACD")
            
            plt.tight_layout()
            
            # Save the plot
            output_dir = "test_output"
            os.makedirs(output_dir, exist_ok=True)
            plt.savefig(f"{output_dir}/{symbol}_{timeframe}_analysis.png")
            logger.info(f"Plot saved to {output_dir}/{symbol}_{timeframe}_analysis.png")
    
    # Close connections
    await processor.close()

async def test_multi_timeframe():
    """Test loading data for multiple timeframes"""
    processor = DataProcessor()
    
    symbol = 'BTCUSD'
    timeframes = ['M15', 'H1', 'H4', 'D1']
    
    logger.info(f"Testing multi-timeframe data loading for {symbol}")
    
    # Load data for multiple timeframes
    data_dict = await processor.get_multi_timeframe_data(symbol, timeframes)
    
    # Check results
    for tf, df in data_dict.items():
        if df is not None and not df.empty:
            logger.info(f"Successfully loaded {len(df)} rows for {tf}")
            logger.info(f"Data range: {df.index[0]} to {df.index[-1]}")
        else:
            logger.error(f"Failed to load data for {tf}")
    
    # Close connections
    await processor.close()

async def main():
    """Main test function"""
    logger.info("Starting data processor tests")
    
    await test_data_loading()
    await test_multi_timeframe()
    
    logger.info("All tests completed")

if __name__ == "__main__":
    asyncio.run(main())
