"""
Test the trade suggestion service with web scraper
"""

import asyncio
import logging
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_bot.data.web_data import WebDataProvider
from trading_bot.analysis.smc import SMCAnalyzer
from trading_bot.risk.management import RiskManager

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_trade_suggestion_with_web():
    """Test trade suggestion with web scraper"""
    logger.info("Testing trade suggestion with web scraper...")
    
    # Initialize the web scraper
    provider = WebDataProvider()
    
    try:
        # Initialize SMC Analyzer
        smc_analyzer = SMCAnalyzer()
        
        # Initialize Risk Manager
        risk_manager = RiskManager()
        
        # Test forex analysis
        logger.info("Testing forex analysis...")
        
        # Get forex data
        forex_df = await provider.get_ohlcv('EURUSD', '4h', count=100, market_type='forex')
        if forex_df is not None:
            # Analyze chart
            analysis = smc_analyzer.analyze_chart(forex_df, 'EURUSD')
            
            logger.info(f"EURUSD analysis:")
            logger.info(f"  Market structure: {analysis['market_structure']['trend']}")
            logger.info(f"  Order blocks: {analysis['smc_elements_count']['order_blocks']}")
            logger.info(f"  Fair value gaps: {analysis['smc_elements_count']['fair_value_gaps']}")
            
            # Check for trade setups
            if analysis['trade_setups']:
                for setup in analysis['trade_setups']:
                    logger.info(f"  Trade setup: {setup['type']} at {setup['entry']}")
                    logger.info(f"  Stop loss: {setup['stop_loss']}, Take profit: {setup['take_profit']}")
                    logger.info(f"  Risk-reward: {setup['risk_reward']:.2f}")
                    logger.info(f"  Reason: {setup['reason']}")
                    
                    # Calculate position size
                    position_size = risk_manager.calculate_position_size(
                        account_size=10000,
                        risk_percentage=1.0,
                        entry_price=setup['entry'],
                        stop_loss=setup['stop_loss'],
                        symbol='EURUSD'
                    )
                    
                    logger.info(f"  Position size: {position_size['position_info']['recommended']}")
            else:
                logger.info("  No trade setups found")
        
        # Test crypto analysis
        logger.info("Testing crypto analysis...")
        
        # Get crypto data
        crypto_df = await provider.get_ohlcv('BTCUSDT', '4h', count=100, market_type='crypto')
        if crypto_df is not None:
            # Analyze chart
            analysis = smc_analyzer.analyze_chart(crypto_df, 'BTCUSDT')
            
            logger.info(f"BTCUSDT analysis:")
            logger.info(f"  Market structure: {analysis['market_structure']['trend']}")
            logger.info(f"  Order blocks: {analysis['smc_elements_count']['order_blocks']}")
            logger.info(f"  Fair value gaps: {analysis['smc_elements_count']['fair_value_gaps']}")
            
            # Check for trade setups
            if analysis['trade_setups']:
                for setup in analysis['trade_setups']:
                    logger.info(f"  Trade setup: {setup['type']} at {setup['entry']}")
                    logger.info(f"  Stop loss: {setup['stop_loss']}, Take profit: {setup['take_profit']}")
                    logger.info(f"  Risk-reward: {setup['risk_reward']:.2f}")
                    logger.info(f"  Reason: {setup['reason']}")
                    
                    # Calculate position size
                    position_size = risk_manager.calculate_position_size(
                        account_size=10000,
                        risk_percentage=1.0,
                        entry_price=setup['entry'],
                        stop_loss=setup['stop_loss'],
                        symbol='BTCUSDT'
                    )
                    
                    logger.info(f"  Position size: {position_size['position_info']['recommended']}")
            else:
                logger.info("  No trade setups found")
        
        # Test multi-timeframe analysis
        logger.info("Testing multi-timeframe analysis...")
        
        # Get multi-timeframe data
        multi_tf_data = await provider.get_multi_timeframe_data(
            'EURUSD', 
            timeframes=['1h', '4h', '1d'], 
            count=100
        )
        
        if multi_tf_data and len(multi_tf_data) >= 3:
            # Analyze each timeframe
            for tf, df in multi_tf_data.items():
                analysis = smc_analyzer.analyze_chart(df, f'EURUSD-{tf}')
                
                logger.info(f"EURUSD {tf} analysis:")
                logger.info(f"  Market structure: {analysis['market_structure']['trend']}")
                logger.info(f"  Trade setups: {len(analysis['trade_setups'])}")
        
        logger.info("Trade suggestion with web scraper test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error testing trade suggestion with web scraper: {e}")
    
    finally:
        # Close the provider
        await provider.close()

if __name__ == '__main__':
    asyncio.run(test_trade_suggestion_with_web())
