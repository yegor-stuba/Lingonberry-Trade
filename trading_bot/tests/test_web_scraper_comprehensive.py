"""
Comprehensive test for the web scraper data provider
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import io

from trading_bot.data.web_data import WebDataProvider
from trading_bot.data.provider_factory import DataProviderFactory
from trading_bot.analysis.smc import SMCAnalyzer
from trading_bot.risk.management import RiskManager

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_web_scraper_comprehensive():
    """Comprehensive test for the web scraper data provider"""
    logger.info("Starting comprehensive web scraper test...")
    
    # Initialize the web scraper
    provider = WebDataProvider()
    
    try:
        # Test 1: Basic price fetching
        logger.info("Test 1: Basic price fetching")
        
        # Test forex prices
        forex_symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        for symbol in forex_symbols:
            price = await provider.get_latest_price(symbol, 'forex')
            logger.info(f"{symbol} price: {price}")
        
        # Test crypto prices
        crypto_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        for symbol in crypto_symbols:
            price = await provider.get_latest_price(symbol, 'crypto')
            logger.info(f"{symbol} price: {price}")
        
        # Test 2: OHLCV data fetching
        logger.info("Test 2: OHLCV data fetching")
        
        # Test forex OHLCV
        for symbol in forex_symbols:
            for timeframe in ['1h', '4h']:
                df = await provider.get_ohlcv(symbol, timeframe, count=10, market_type='forex')
                if df is not None:
                    logger.info(f"{symbol} {timeframe} OHLCV data: {len(df)} candles")
                    logger.info(f"Sample:\n{df.head(3)}")
        
        # Test crypto OHLCV
        for symbol in crypto_symbols:
            for timeframe in ['1h', '4h']:
                df = await provider.get_ohlcv(symbol, timeframe, count=10, market_type='crypto')
                if df is not None:
                    logger.info(f"{symbol} {timeframe} OHLCV data: {len(df)} candles")
                    logger.info(f"Sample:\n{df.head(3)}")
        
        # Test 3: Multi-timeframe data
        logger.info("Test 3: Multi-timeframe data")
        
        # Test forex multi-timeframe
        for symbol in forex_symbols[:1]:  # Just test one symbol
            multi_tf_data = await provider.get_multi_timeframe_data(
                symbol, timeframes=['1h', '4h', '1d'], count=10, market_type='forex'
            )
            for tf, df in multi_tf_data.items():
                logger.info(f"{symbol} {tf} data: {len(df)} candles")
        
        # Test 4: Historical data
        logger.info("Test 4: Historical data")
        
        # Test forex historical data
        for symbol in forex_symbols[:1]:  # Just test one symbol
            hist_data = await provider.get_historical_data(
                symbol, period='1m', timeframe='1d', market_type='forex'
            )
            if hist_data is not None:
                logger.info(f"{symbol} historical data: {len(hist_data)} candles")
        
        # Test 5: Integration with SMC Analyzer
        logger.info("Test 5: Integration with SMC Analyzer")
        
        # Initialize SMC Analyzer
        smc_analyzer = SMCAnalyzer()
        
        # Test forex SMC analysis
        for symbol in forex_symbols[:1]:  # Just test one symbol
            df = await provider.get_ohlcv(symbol, '4h', count=100, market_type='forex')
            if df is not None:
                analysis = smc_analyzer.analyze_chart(df, symbol)
                logger.info(f"{symbol} SMC analysis:")
                logger.info(f"  Market structure: {analysis['market_structure']['trend']}")
                logger.info(f"  Order blocks: {analysis['smc_elements_count']['order_blocks']}")
                logger.info(f"  Fair value gaps: {analysis['smc_elements_count']['fair_value_gaps']}")
                logger.info(f"  Trade setups: {analysis['smc_elements_count']['trade_setups']}")
        
        # Test 6: Integration with Risk Manager
        logger.info("Test 6: Integration with Risk Manager")
        
        # Initialize Risk Manager
        risk_manager = RiskManager()
        
        # Test forex risk management
        for symbol in forex_symbols[:1]:  # Just test one symbol
            price = await provider.get_latest_price(symbol, 'forex')
            if price is not None:
                # Calculate position size
                position_size = risk_manager.calculate_position_size(
                    account_size=10000,
                    risk_percentage=1.0,
                    entry_price=price,
                    stop_loss=price * 0.99,  # 1% below current price
                    symbol=symbol
                )
                logger.info(f"{symbol} position size calculation:")
                logger.info(f"  Direction: {position_size['direction']}")
                logger.info(f"  Risk amount: ${position_size['risk_amount']}")
                logger.info(f"  Position size: {position_size['position_size']}")
                logger.info(f"  Recommended: {position_size['position_info']['recommended']}")
        
        # Test 7: Caching
        logger.info("Test 7: Caching")
        
        # Test price caching
        symbol = forex_symbols[0]
        logger.info(f"Testing price caching for {symbol}...")
        
        # First request should hit the network
        start_time = datetime.now()
        price1 = await provider.get_latest_price(symbol, 'forex')
        first_request_time = (datetime.now() - start_time).total_seconds()
        
        # Second request should use cache
        start_time = datetime.now()
        price2 = await provider.get_latest_price(symbol, 'forex')
        second_request_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"First request time: {first_request_time:.3f}s")
        logger.info(f"Second request time: {second_request_time:.3f}s")
        logger.info(f"Cache speedup: {first_request_time / second_request_time:.1f}x")
        
        # Test 8: Factory integration
        logger.info("Test 8: Factory integration")
        
        # Get provider through factory
        factory_provider = await DataProviderFactory.get_provider('forex', use_web_scraper=True)
        
        # Test that it works
        if factory_provider:
            price = await factory_provider.get_latest_price('EURUSD', 'forex')
            logger.info(f"Factory provider EURUSD price: {price}")
        
        logger.info("Comprehensive test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in comprehensive test: {e}")
    
    finally:
        # Close the provider
        await provider.close()

if __name__ == '__main__':
    asyncio.run(test_web_scraper_comprehensive())
