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
import time  # Add time module import
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

def signal_handler(sig, frame):
    """Handle termination signals"""
    global running
    logger.info("Shutdown signal received. Closing all connections...")
    running = False


# Add the check_connections function
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
        
        # Set the dashboard URL as an environment variable
        os.environ["DASHBOARD_URL"] = public_url
        
        return public_url
    except ImportError:
        logger.warning("pyngrok not installed. Install with: pip install pyngrok")
        return None
    except Exception as e:
        logger.error(f"Error starting ngrok: {e}")
        return None

def run_web_dashboard(port=5000, use_ngrok=False):
    """Run the web dashboard in a separate thread"""
    if use_ngrok:
        dashboard_url = start_ngrok(port)
    else:
        dashboard_url = f"http://localhost:{port}"
    
    # Start the dashboard
    start_dashboard(host='0.0.0.0', port=port, debug=False)

async def run_telegram_bot(telegram_bot):
    """Run the Telegram bot asynchronously"""
    try:
        await telegram_bot.run_async()
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}", exc_info=True)
        
async def main_async():
    """Async version of the main function"""
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
        
        # Track active resources for cleanup
        active_resources = {
            'data_processor': data_processor,
            'ngrok_tunnels': [],
            'telegram_bot': None
        }
        
        # Start web dashboard if enabled
        dashboard_url = None
        dashboard_thread = None
        
        if DASHBOARD_ENABLED and not args.no_dashboard:
            dashboard_url = await setup_dashboard(args, active_resources)
            if dashboard_url:
                dashboard_thread = threading.Thread(
                    target=lambda: start_dashboard(host='0.0.0.0', port=args.port, debug=False),
                    daemon=True
                )
                dashboard_thread.start()
        
        # Start Telegram bot if enabled
        if not args.no_telegram:
            await setup_telegram_bot(dashboard_url, active_resources)
        
        # Main loop
        global running
        running = True
        
        try:
            logger.info("Trading bot started successfully!")
            logger.info("Press Ctrl+C to exit")
            
            # Keep the main thread alive with periodic connection checks
            connection_check_interval = 60
            last_check_time = time.time()
            
            while running:
                current_time = time.time()
                if current_time - last_check_time > connection_check_interval:
                    check_connections(data_processor)
                    last_check_time = current_time
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Shutting down...")
        finally:
            await cleanup_resources(active_resources)
            
    except Exception as e:
        logger.error(f"Critical error in main_async: {e}", exc_info=True)
        raise

async def setup_dashboard(args, active_resources):
    """Setup dashboard and ngrok if enabled"""
    try:
        logger.info("Starting web dashboard...")
        if args.use_ngrok:
            try:
                from pyngrok import ngrok, conf
                conf.get_default().auth_token = credentials.NGROK_AUTHTOKEN
                tunnel = ngrok.connect(args.port, "http")
                active_resources['ngrok_tunnels'].append(tunnel)
                dashboard_url = tunnel.public_url
                logger.info(f"Web dashboard available at: {dashboard_url}")
                os.environ["DASHBOARD_URL"] = dashboard_url
                return dashboard_url
            except ImportError:
                logger.warning("pyngrok not installed. Install with: pip install pyngrok")
            except Exception as e:
                logger.error(f"Error starting ngrok: {e}", exc_info=True)
        return f"http://localhost:{args.port}"
    except Exception as e:
        logger.error(f"Error setting up dashboard: {e}", exc_info=True)
        return None

async def setup_telegram_bot(dashboard_url, active_resources):
    """Setup and start Telegram bot"""
    try:
        logger.info("Starting Telegram bot...")
        telegram_bot = TelegramBot(dashboard_url=dashboard_url)
        active_resources['telegram_bot'] = telegram_bot
        await run_telegram_bot(telegram_bot)
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}", exc_info=True)

async def cleanup_resources(active_resources):
    """Clean up all active resources"""
    logger.info("Cleaning up resources...")
    
    # Close data processor connections
    if 'data_processor' in active_resources:
        try:
            logger.info("Closing data processor connections...")
            active_resources['data_processor'].close()
        except Exception as e:
            logger.error(f"Error closing data processor: {e}", exc_info=True)
    
    # Close ngrok tunnels
    if active_resources['ngrok_tunnels']:
        try:
            logger.info("Closing ngrok tunnels...")
            from pyngrok import ngrok
            for tunnel in active_resources['ngrok_tunnels']:
                ngrok.disconnect(tunnel.public_url)
        except Exception as e:
            logger.error(f"Error closing ngrok tunnels: {e}", exc_info=True)
    
    # Stop Telegram bot
    if active_resources['telegram_bot']:
        try:
            logger.info("Stopping Telegram bot...")
            try:
                await active_resources['telegram_bot'].application.stop()
            except RuntimeError as e:
                if "This Application is not running" not in str(e):
                    raise
                logger.warning("Telegram bot was not running, no need to stop")
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}", exc_info=True)
    
    logger.info("Trading bot shutdown complete.")

def main():
    """Main entry point for the trading bot"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the async main function
    asyncio.run(main_async())
if __name__ == "__main__":
    main()