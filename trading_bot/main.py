"""
Main entry point for the Lingonberry Trade Bot
Launches all components of the trading system
"""

import os
import sys
import logging
import threading
import argparse
import asyncio
import signal
import time
from pathlib import Path


# Add the project root to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from trading_bot.data.data_processor import DataProcessor
from trading_bot.strategy.signal_generator import SignalGenerator
from trading_bot.ui.telegram_bot import TelegramBot
from trading_bot.ui.web_dashboard.app import start_dashboard
from trading_bot.config.settings import DASHBOARD_ENABLED, DASHBOARD_URL
from trading_bot.journal.trade_journal import TradeJournal
from trading_bot.config import credentials

# Create necessary directories
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("charts", exist_ok=True)
os.makedirs("charts/crypto", exist_ok=True)
os.makedirs("charts/forex", exist_ok=True)

# Ensure the database file path exists
db_path = Path("data/trade_journal.db")
if not db_path.parent.exists():
    os.makedirs(db_path.parent, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/trading_bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global flag to control the main loop
running = True

# Global variables for resources
data_processor = None
telegram_bot = None
ngrok_tunnels = []

def signal_handler(sig, frame):
    """Handle termination signals"""
    global running
    logger.info("Shutdown signal received. Closing all connections...")
    running = False


def check_connections(data_processor):
    """Periodically check and restore connections if needed"""
    try:
        # Check if cTrader is connected
        ctrader = data_processor.ctrader
        if hasattr(ctrader, 'connected') and not ctrader.connected:
            logger.info("Detected disconnected cTrader, attempting to reconnect...")
            ctrader.connect()
    except Exception as e:
        logger.error(f"Error checking connections: {e}", exc_info=True)


def start_ngrok(port=5000):
    """Start ngrok tunnel for the web dashboard"""
    try:
        from pyngrok import ngrok, conf
        
        # Configure ngrok
        conf.get_default().auth_token = credentials.NGROK_AUTHTOKEN
        
        # Start ngrok tunnel
        public_url = ngrok.connect(port, "http")
        logger.info(f"Web dashboard available at: {public_url}")
        
        # Extract the URL as a string
        if hasattr(public_url, 'public_url'):
            url_str = public_url.public_url
        else:
            url_str = str(public_url)
        
        # Set the dashboard URL as an environment variable
        os.environ["DASHBOARD_URL"] = url_str
        
        # Add to global list for cleanup
        global ngrok_tunnels
        ngrok_tunnels.append(public_url)
        
        return url_str
    except ImportError:
        logger.warning("pyngrok not installed. Install with: pip install pyngrok")
        return None
    except Exception as e:
        logger.error(f"Error starting ngrok: {e}")
        return None





async def run_telegram_bot(telegram_bot):
    """Run the Telegram bot asynchronously"""
    try:
        # Start the application without using updater.start_polling directly
        await telegram_bot.application.initialize()
        await telegram_bot.application.start()
        await telegram_bot.application.updater.start_polling()
        
        logger.info("Telegram bot started successfully")
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}", exc_info=True)


async def cleanup_resources():
    """Clean up all active resources"""
    global data_processor, telegram_bot, ngrok_tunnels
    
    logger.info("Cleaning up resources...")
    
    # Close data processor connections
    if data_processor:
        try:
            logger.info("Closing data processor connections...")
            data_processor.close()
        except Exception as e:
            logger.error(f"Error closing data processor: {e}", exc_info=True)
    
    # Close ngrok tunnels
    if ngrok_tunnels:
        try:
            logger.info("Closing ngrok tunnels...")
            from pyngrok import ngrok
            for tunnel in ngrok_tunnels:
                ngrok.disconnect(tunnel)
        except Exception as e:
            logger.error(f"Error closing ngrok tunnels: {e}", exc_info=True)
    
    # Stop Telegram bot
    if telegram_bot:
        try:
            logger.info("Stopping Telegram bot...")
            try:
                await telegram_bot.application.stop()
            except RuntimeError as e:
                if "This Application is not running" not in str(e):
                    raise
                logger.warning("Telegram bot was not running, no need to stop")
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}", exc_info=True)
    
    logger.info("Trading bot shutdown complete.")


async def main_async():
    """Async version of the main function"""
    global data_processor, telegram_bot, ngrok_tunnels
    
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Lingonberry Trade Bot")
        parser.add_argument("--no-dashboard", action="store_true", help="Disable web dashboard")
        parser.add_argument("--no-telegram", action="store_true", help="Disable Telegram bot")
        parser.add_argument("--port", type=int, default=5000, help="Port for web dashboard")
        parser.add_argument("--use-ngrok", action="store_true", help="Use ngrok for web dashboard")
        parser.add_argument("--no-cache", action="store_true", help="Disable initial data caching")
        args = parser.parse_args()
        
        # Initialize components
        logger.info("Initializing trading bot components...")
        
        # Initialize core components with error handling
        try:
            data_processor = DataProcessor()
            trade_journal = TradeJournal()
            signal_generator = SignalGenerator()
        except Exception as e:
            logger.error(f"Failed to initialize core components: {e}", exc_info=True)
            return
        
        # Start web dashboard if enabled
        dashboard_url = None
        dashboard_thread = None

        if DASHBOARD_ENABLED and not args.no_dashboard:
            logger.info("Starting web dashboard...")
            
            # Start ngrok if requested
            if args.use_ngrok:
                dashboard_url = start_ngrok(args.port)
                # Set the environment variable for other components
                os.environ["DASHBOARD_URL"] = dashboard_url
            else:
                dashboard_url = f"http://localhost:{args.port}"
            
            # Start dashboard in a thread
            dashboard_thread = threading.Thread(
                target=lambda: start_dashboard(host='0.0.0.0', port=args.port, debug=False),
                daemon=True
            )
            dashboard_thread.start()

        # Start Telegram bot if enabled
        if not args.no_telegram:
            logger.info("Starting Telegram bot...")
            try:
                # Initialize the Telegram bot with the dashboard URL
                telegram_bot = TelegramBot(dashboard_url=dashboard_url)
                
                # Start the Telegram bot asynchronously
                await run_telegram_bot(telegram_bot)
            except Exception as e:
                logger.error(f"Error starting Telegram bot: {e}", exc_info=True)        
        # Main loop
        global running
        running = True
        
        try:
            logger.info("Trading bot started successfully!")
            logger.info("Press Ctrl+C to exit")
            
            # Keep the main thread alive
            connection_check_interval = 60  # Check every 60 seconds
            last_check_time = time.time()
            
            while running:
                # Perform periodic tasks
                current_time = time.time()
                if current_time - last_check_time > connection_check_interval:
                    check_connections(data_processor)
                    last_check_time = current_time
                    
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Shutting down...")
        
        finally:
            # Clean up resources
            await cleanup_resources()
    
    except Exception as e:
        logger.error(f"Critical error in main_async: {e}", exc_info=True)
        await cleanup_resources()


def main():
    """Main entry point for the trading bot"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the async main function
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
