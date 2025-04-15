"""
Test the web scraper data provider
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime

from trading_bot.data.web_data import WebDataProvider

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_web_scraper():
    """Test the web scraper data provider"""
    logger.info("Testing web scraper data provider...")
    
    # Initialize the web scraper
    provider = WebDataProvider()
    
    try:
        # Test forex price
        logger.info("Testing forex price...")
        forex_price = await provider.get_latest_price('EURUSD', 'forex')
        logger.info(f"EURUSD price: {forex_price}")
        
        # Test crypto price
        logger.info("Testing crypto price...")
        crypto_price = await provider.get_latest_price('BTCUSDT', 'crypto')
        logger.info(f"BTCUSDT price: {crypto_price}")
        
        # Test OHLCV data
        logger.info("Testing OHLCV data...")
        
        # Test forex OHLCV
        forex_df = await provider.get_ohlcv('EURUSD', '1h', count=10, market_type='forex')
        if forex_df is not None:
            logger.info(f"EURUSD 1h OHLCV data: {len(forex_df)} candles")
            logger.info(f"Sample:\n{forex_df.head(3)}")
        
        # Test crypto OHLCV
        crypto_df = await provider.get_ohlcv('BTCUSDT', '1h', count=10, market_type='crypto')
        if crypto_df is not None:
            logger.info(f"BTCUSDT 1h OHLCV data: {len(crypto_df)} candles")
            logger.info(f"Sample:\n{crypto_df.head(3)}")
        
        # Test multi-timeframe data
        logger.info("Testing multi-timeframe data...")
        multi_tf_data = await provider.get_multi_timeframe_data('EURUSD', timeframes=['1h', '4h'], count=10)
        for tf, df in multi_tf_data.items():
            logger.info(f"EURUSD {tf} data: {len(df)} candles")
        
        # Test historical data
        logger.info("Testing historical data...")
        hist_data = await provider.get_historical_data('EURUSD', period='1m', timeframe='1d')
        if hist_data is not None:
            logger.info(f"EURUSD historical data: {len(hist_data)} candles")
        
        logger.info("Web scraper test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error testing web scraper: {e}")
    
    finally:
        # Close the provider
        await provider.close()

if __name__ == '__main__':
    asyncio.run(test_web_scraper())
