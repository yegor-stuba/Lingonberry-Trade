"""
Main entry point for the trading bot
"""

import sys
import os
import logging
from pathlib import Path
import argparse
import asyncio

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_bot.config import settings
from trading_bot.services.trade_suggestion import TradeSuggestionService
from trading_bot.bridges.mt5.server import run_server as run_mt5_server
import threading

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def async_main(args):
    """Async main function"""
    logger.info("Starting Trading Bot...")
    
    # Start MT5 bridge server if requested
    mt5_server_thread = None
    if args.start_mt5_bridge:
        logger.info("Starting MT5 bridge server...")
        mt5_server_thread = threading.Thread(target=run_mt5_server)
        mt5_server_thread.daemon = True
        mt5_server_thread.start()
        logger.info("MT5 bridge server started in background")
        
        # Give the server time to start
        await asyncio.sleep(2)
    
    # Initialize the trade suggestion service
    service = TradeSuggestionService(
        use_web_scraper=args.use_web_scraper,
        use_mt5=args.use_mt5,
        browser_type=args.browser
    )
    
    try:
        # Initialize the service
        logger.info("Initializing trade suggestion service...")
        init_success = await service.initialize()
        
        if not init_success:
            logger.error("Failed to initialize trade suggestion service")
            return
        
        logger.info("Trade suggestion service initialized successfully")
        
        if args.symbol:
            # Get trade suggestion for a specific symbol
            logger.info(f"Getting trade suggestion for {args.symbol} in {args.market} market...")
            result = await service.get_trade_suggestions(args.market, args.symbol)
            
            if result['success']:
                suggestions = result.get('suggestions', [])
                if suggestions:
                    logger.info(f"Found {len(suggestions)} trade suggestions for {args.symbol}")
                    
                    # Print details of each suggestion
                    for i, suggestion in enumerate(suggestions):
                        logger.info(f"Suggestion {i+1}:")
                        logger.info(f"  Direction: {suggestion['direction']}")
                        logger.info(f"  Entry: {suggestion['entry']}")
                        logger.info(f"  Stop Loss: {suggestion['stop_loss']}")
                        logger.info(f"  Take Profit: {suggestion['take_profit']}")
                        logger.info(f"  Risk-Reward: {suggestion['risk_reward']:.2f}")
                        logger.info(f"  Reason: {suggestion['reason']}")
                        if 'position_info' in suggestion and 'recommended' in suggestion['position_info']:
                            logger.info(f"  Position Size: {suggestion['position_info']['recommended']}")
                else:
                    logger.info(f"No trade suggestions found for {args.symbol}")
            else:
                logger.error(f"Error getting trade suggestions: {result.get('message', 'Unknown error')}")
        else:
            # Scan the market
            logger.info(f"Scanning {args.market} market...")
            scan_results = await service.get_market_scanner_results(args.market)
            
            if scan_results:
                logger.info(f"Found {len(scan_results)} potential opportunities")
                
                # Print details of the top 5 results
                for i, result in enumerate(scan_results[:5]):
                    logger.info(f"Opportunity {i+1}:")
                    logger.info(f"  Symbol: {result['symbol']}")
                    logger.info(f"  Bias: {result['bias']}")
                    logger.info(f"  Current Price: {result['current_price']}")
                    logger.info(f"  Strong Order Blocks: {result['has_strong_ob']}")
                    logger.info(f"  Score: {result['score']}")
                
                # Get detailed suggestions for the top result
                if scan_results:
                    top_symbol = scan_results[0]['symbol']
                    logger.info(f"Getting detailed suggestion for top opportunity: {top_symbol}")
                    
                    detailed_result = await service.get_trade_suggestions(args.market, top_symbol)
                    if detailed_result['success'] and detailed_result.get('suggestions'):
                        suggestion = detailed_result['suggestions'][0]
                        logger.info(f"Trade suggestion for {top_symbol}:")
                        logger.info(f"  Direction: {suggestion['direction']}")
                        logger.info(f"  Entry: {suggestion['entry']}")
                        logger.info(f"  Stop Loss: {suggestion['stop_loss']}")
                        logger.info(f"  Take Profit: {suggestion['take_profit']}")
                        logger.info(f"  Risk-Reward: {suggestion['risk_reward']:.2f}")
                        logger.info(f"  Reason: {suggestion['reason']}")
            else:
                logger.info(f"No opportunities found in {args.market} market")
        
        logger.info("Trading Bot completed successfully")
        
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        # Close the service
        await service.close()

def main():
    """Main function"""
    logger.info("Starting Trading Bot...")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Trading Bot')
    parser.add_argument('--use-web-scraper', action='store_true', help='Use web scraper for data')
    parser.add_argument('--use-mt5', action='store_true', help='Use MT5 for data')
    parser.add_argument('--start-mt5-bridge', action='store_true', help='Start MT5 bridge server')
    parser.add_argument('--market', type=str, default='forex', help='Market to scan (forex, crypto, indices, metals)')
    parser.add_argument('--symbol', type=str, help='Symbol to analyze (e.g., EURUSD)')
    parser.add_argument('--browser', type=str, default='chromium', help='Browser to use (chromium, firefox, edge)')
    args = parser.parse_args()
    
    # Run the async main function
    asyncio.run(async_main(args))

if __name__ == "__main__":
    main()
