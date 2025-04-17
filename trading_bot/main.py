"""
Main entry point for the trading bot
"""

import os
import sys
import logging
import asyncio
import threading
import time
import json
import subprocess
import requests
from pathlib import Path

from trading_bot.ui.telegram_bot import TelegramBot
from trading_bot.strategy.signal_generator import SignalGenerator
from trading_bot.data.data_processor import DataProcessor
from trading_bot.config.settings import DASHBOARD_URL, DASHBOARD_ENABLED
from trading_bot.ui.web_dashboard.app import app
from apscheduler.schedulers.background import BackgroundScheduler
from trading_bot.journal.trade_journal import TradeJournal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("trading_bot.log")
    ]
)
logger = logging.getLogger(__name__)

# Global variable to store ngrok process
ngrok_process = None
actual_dashboard_url = None

def start_ngrok(port):
    """Start ngrok and return the public URL"""
    global ngrok_process
    
    try:
        # Check if ngrok is installed
        try:
            subprocess.run(["ngrok", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("ngrok is not installed or not in PATH. Please install it first.")
            return None
        
        # Start ngrok process
        ngrok_process = subprocess.Popen(
            ["ngrok", "http", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"Started ngrok process (PID: {ngrok_process.pid})")
        
        # Wait for ngrok to start
        time.sleep(2)
        
        # Get the public URL from ngrok API
        try:
            response = requests.get("http://localhost:4040/api/tunnels")
            tunnels = json.loads(response.text)["tunnels"]
            if tunnels:
                public_url = tunnels[0]["public_url"]
                logger.info(f"ngrok public URL: {public_url}")
                return public_url
            else:
                logger.error("No ngrok tunnels found")
                return None
        except Exception as e:
            logger.error(f"Error getting ngrok URL: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Error starting ngrok: {e}")
        return None

def stop_ngrok():
    """Stop the ngrok process"""
    global ngrok_process
    if ngrok_process:
        logger.info(f"Stopping ngrok process (PID: {ngrok_process.pid})")
        ngrok_process.terminate()
        ngrok_process = None

def run_dashboard():
    """Run the web dashboard in a separate thread"""
    try:
        logger.info(f"Starting web dashboard on {DASHBOARD_URL}")
        # Parse the port from DASHBOARD_URL or use default 5000
        port = 5000
        if ":" in DASHBOARD_URL:
            try:
                port = int(DASHBOARD_URL.split(":")[-1].split("/")[0])
            except (ValueError, IndexError):
                pass
        
        # On macOS, use port 8080 instead of 5000 to avoid AirPlay conflict
        if sys.platform == 'darwin' and port == 5000:
            port = 8080
            logger.info(f"Using port {port} on macOS to avoid AirPlay conflict")
        
        # Make sure to bind to 0.0.0.0 to allow external connections
        app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
    except Exception as e:
        logger.error(f"Error starting web dashboard: {e}")

# Add a scheduled task to update trade statuses
def update_trade_statuses():
    """Update the status of pending and active trades"""
    try:
        logger.info("Updating trade statuses...")
        trade_journal = TradeJournal()
        
        # Create a data processor for getting current prices
        data_processor = DataProcessor()
        
        # Create an event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the check functions
        loop.run_until_complete(trade_journal.check_pending_trades(data_processor))
        loop.run_until_complete(trade_journal.check_active_trades(data_processor))
        
        # Close the loop
        loop.close()
        
        logger.info("Trade statuses updated successfully")
    except Exception as e:
        logger.error(f"Error updating trade statuses: {e}")

def get_ngrok_url():
    """Get the public URL from ngrok"""
    try:
        response = requests.get("http://localhost:4040/api/tunnels")
        tunnels = json.loads(response.text)["tunnels"]
        for tunnel in tunnels:
            if tunnel["proto"] == "https":
                return tunnel["public_url"]
        return None
    except Exception as e:
        logger.error(f"Error getting ngrok URL: {e}")
        return None

def main():
    """Main function to run the bot"""
    logger.info("Starting trading bot...")
    
    # Create data directories if they don't exist
    data_dirs = ["data", "charts", "charts/crypto", "charts/forex", "journal"]
    for directory in data_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Check if we need to start ngrok
    dashboard_url = DASHBOARD_URL
    ngrok_process = None
    
    if "localhost" in DASHBOARD_URL or "127.0.0.1" in DASHBOARD_URL:
        logger.info("Dashboard URL is set to localhost, starting ngrok...")
        
        # Start ngrok in a subprocess
        port = 8080  # Use the port we set for Flask
        if sys.platform == 'darwin':
            # On macOS, avoid port 5000 which is used by AirPlay
            port = 8080
        
        ngrok_command = ["ngrok", "http", str(port)]
        ngrok_process = subprocess.Popen(ngrok_command, stdout=subprocess.PIPE)
        logger.info(f"Started ngrok process (PID: {ngrok_process.pid})")
        
        # Wait for ngrok to start
        time.sleep(2)
        
        # Get the public URL
        ngrok_url = get_ngrok_url()
        if ngrok_url:
            dashboard_url = ngrok_url
            logger.info(f"ngrok public URL: {ngrok_url}")
            logger.info(f"Dashboard will be accessible at: {dashboard_url}")
    
    # Start the web dashboard in a separate thread
    if DASHBOARD_ENABLED:
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        dashboard_thread.start()
        logger.info("Web dashboard started in background thread")
    
    # Add a scheduled task to update trade statuses
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_trade_statuses, 'interval', hours=1)
    scheduler.start()
    logger.info("Trade status update scheduler started")
    
    # Initialize the Telegram bot with the correct dashboard URL
    telegram_bot = TelegramBot(dashboard_url=dashboard_url)
    
    # Run the bot
    telegram_bot.run()
    
    # Clean up ngrok process on exit
    if ngrok_process:
        ngrok_process.terminate()

if __name__ == "__main__":
    # Set a default event loop policy that works well with asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    main()