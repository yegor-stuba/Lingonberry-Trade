"""
Test for the WebDataProvider
"""

import logging
import asyncio
import pandas as pd
from trading_bot.data.web_data import WebDataProvider

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_web_data_provider():
    """Test the WebDataProvider"""
    provider = WebDataProvider()
    await provider.initialize()
    
    # Test forex
    forex_symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    
    logger.info("Testing forex data...")
    for symbol in forex_symbols:
        logger.info(f"Getting latest price for {symbol}...")
        price = await provider.get_latest_price(symbol, market_type='forex')
        logger.info(f"{symbol}: {price}")
    
    # Test crypto
    crypto_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    
    logger.info("Testing crypto data...")
    for symbol in crypto_symbols:
        logger.info(f"Getting latest price for {symbol}...")
        price = await provider.get_latest_price(symbol, market_type='crypto')
        logger.info(f"{symbol}: {price}")
    
    # Test OHLCV data
    logger.info("Testing OHLCV data...")
    df = await provider.get_ohlcv('EURUSD', '1h', 10, market_type='forex')
    if df is not None:
        logger.info(f"EURUSD 1h OHLCV data:\n{df.head()}")
    else:
        logger.error("Failed to get EURUSD OHLCV data")
    
    # Close the provider
    await provider.close()

if __name__ == "__main__":
    logger.info("Starting WebDataProvider test...")
    asyncio.run(test_web_data_provider())
    logger.info("WebDataProvider test completed")
