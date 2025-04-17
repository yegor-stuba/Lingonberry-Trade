"""
Enhanced test script for ctrader data functionality
- Multiple timeframes
- Live data
- Different markets
"""

import os
import sys
import time
from datetime import datetime
import logging
import argparse
from collections import defaultdict

# Add the parent directory to the path so we can import from trading_bot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
    ProtoOAAccountAuthReq,
    ProtoOAGetTrendbarsReq,
    ProtoOASubscribeSpotsReq,
    ProtoOASubscribeLiveTrendbarReq,
    ProtoOASymbolsListReq
)
from twisted.internet import reactor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test cTrader data functionality')
parser.add_argument('--symbol', type=str, default='BTCUSD', help='Symbol name (e.g., BTCUSD, EURUSD)')
parser.add_argument('--timeframes', type=str, default='M1,M5,H1', 
                    help='Comma-separated list of timeframes (M1,M2,M3,M4,M5,M10,M15,M30,H1,H4,H12,D1,W1,MN1)')
parser.add_argument('--bars', type=int, default=10, help='Number of historical bars to fetch')
parser.add_argument('--live', action='store_true', help='Subscribe to live data')
parser.add_argument('--list-symbols', action='store_true', help='List available symbols')
parser.add_argument('--market', type=str, choices=['crypto', 'forex', 'indices', 'metals'], default='crypto', 
                    help='Market type to filter symbols')
parser.add_argument('--verbose', action='store_true', help='Show all updates (no throttling)')
parser.add_argument('--list-timeframes', action='store_true', help='List available timeframes')
args = parser.parse_args()

# Your credentials from the config file
CLIENT_ID = "14299_6GrwlOC8xpjw3wii01yK59g190srgNLugxrI8tLjS1yakA70ii"
CLIENT_SECRET = "03GGc3ehttopFBM159Ym6GkHuiE4e9hUgNMCa1eaM1JNYcPu6y"
ACCOUNT_ID = 43150007
ACCESS_TOKEN = "KDEAo6QWey1271hWVzmRmJH45sF3vTulBH26nlRo9Wg"

# Symbol mapping (you may need to update these IDs based on your broker)
SYMBOL_IDS = {
    # Crypto
    'BTCUSD': 101,
    'ETHUSD': 102,
    'XRPUSD': 2592,
    'ADAUSD': 2597,
    # Forex
    'EURUSD': 1,
    'GBPUSD': 2,
    'USDJPY': 4,
    'AUDUSD': 5,
    'USDCAD': 8,
    # Indices
    'US30': 2596,  # This might need to be updated
    'US500': 2596,  # This might need to be updated
    'USTEC': 2596,  # This might need to be updated
    # Metals
    'XAUUSD': 41,
    'XAGUSD': 42,
}

# Update the TIMEFRAME_PERIODS mapping based on cTrader API documentation
TIMEFRAME_PERIODS = {
    "M1": 1,    # 1 minute
    "M2": 2,    # 2 minutes
    "M3": 3,    # 3 minutes
    "M4": 4,    # 4 minutes
    "M5": 5,    # 5 minutes
    "M10": 6,   # 10 minutes
    "M15": 7,   # 15 minutes
    "M30": 8,   # 30 minutes
    "H1": 9,    # 1 hour
    "H4": 10,   # 4 hours
    "H12": 11,  # 12 hours
    "D1": 12,   # 1 day
    "W1": 13,   # 1 week
    "MN1": 14   # 1 month
}

# Initialize the client
client = Client(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)

# Global variables
historical_data_fetched = False
connection_successful = False
timeframes_to_process = args.timeframes.split(',')
current_timeframe_index = 0
symbol_id = SYMBOL_IDS.get(args.symbol.upper(), 101)  # Default to BTCUSD if not found
symbol_list = []
live_data_subscribed = False

def on_error(failure):
    logger.error(f"Error: {failure}")
    # Print more detailed error information
    if hasattr(failure, 'value'):
        logger.error(f"Error value: {failure.value}")
    if hasattr(failure, 'type'):
        logger.error(f"Error type: {failure.type}")
    reactor.stop()

def on_connected(client):
    global connection_successful
    connection_successful = True
    logger.info("Connected to cTrader Open API")
    
    # Application authentication
    app_auth_req = ProtoOAApplicationAuthReq()
    app_auth_req.clientId = CLIENT_ID
    app_auth_req.clientSecret = CLIENT_SECRET
    d = client.send(app_auth_req)
    d.addCallback(on_app_auth_response)
    d.addErrback(on_error)

def on_app_auth_response(response):
    logger.info("Application authenticated successfully")
    
    # Account authentication
    account_auth_req = ProtoOAAccountAuthReq()
    account_auth_req.ctidTraderAccountId = ACCOUNT_ID
    account_auth_req.accessToken = ACCESS_TOKEN
    d = client.send(account_auth_req)
    d.addCallback(on_account_auth_response)
    d.addErrback(on_error)

def on_account_auth_response(response):
    logger.info("Account authenticated successfully")
    
    # If list-timeframes flag is set, just print the timeframe mapping and exit
    if args.list_timeframes:
        logger.info("Available timeframes and their values:")
        for tf, value in sorted(TIMEFRAME_PERIODS.items(), key=lambda x: x[1]):
            logger.info(f"  {tf}: {value}")
        reactor.callLater(1, reactor.stop)
        return
    
    # If list-symbols flag is set, request symbol list
    if args.list_symbols:
        request_symbol_list()
    else:
        # Start fetching historical data
        start_data_fetching()

def request_symbol_list():
    logger.info("Requesting symbol list...")
    symbols_req = ProtoOASymbolsListReq()
    symbols_req.ctidTraderAccountId = ACCOUNT_ID
    d = client.send(symbols_req)
    d.addCallback(on_symbols_list_response)
    d.addErrback(on_error)

def on_symbols_list_response(response):
    global symbol_list
    
    # Extract the symbols using the Protobuf helper
    symbols_response = Protobuf.extract(response)
    
    if hasattr(symbols_response, 'symbol'):
        symbol_list = symbols_response.symbol
        logger.info(f"Received {len(symbol_list)} symbols")
        
        # Filter symbols by market type
        market_filters = {
            'crypto': ['BTC', 'ETH', 'XRP', 'ADA', 'DOT', 'USDT'],
            'forex': ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD'],
            'indices': ['IDX', 'US30', 'US500', 'USTEC', 'UK100', 'GER40'],
            'metals': ['XAU', 'XAG', 'GOLD', 'SILVER']
        }
        
        filter_terms = market_filters.get(args.market, [])
        
        # Print filtered symbols
        logger.info(f"Symbols for {args.market} market:")
        for symbol in symbol_list:
            if hasattr(symbol, 'symbolName'):
                symbol_name = symbol.symbolName
                if any(term in symbol_name for term in filter_terms):
                    symbol_id = getattr(symbol, 'symbolId', 'N/A')
                    logger.info(f"  {symbol_name} (ID: {symbol_id})")
    
    # Stop the reactor after listing symbols
    reactor.callLater(2, reactor.stop)

def start_data_fetching():
    global current_timeframe_index
    
    if current_timeframe_index < len(timeframes_to_process):
        current_timeframe = timeframes_to_process[current_timeframe_index]
        
        if current_timeframe in TIMEFRAME_PERIODS:
            period = TIMEFRAME_PERIODS[current_timeframe]
            logger.info(f"Processing timeframe {current_timeframe} for {args.symbol}")
            request_historical_data(symbol_id, period, args.bars, current_timeframe)
        else:
            logger.error(f"Invalid timeframe: {current_timeframe}")
            current_timeframe_index += 1
            start_data_fetching()
    elif args.live:
        # After fetching all historical data, subscribe to live data
        subscribe_to_live_data()
    else:
        logger.info("All timeframes processed successfully!")
        reactor.callLater(2, reactor.stop)

def request_historical_data(symbol_id, period, count, timeframe):
    # Calculate period in minutes for timestamp calculation
    period_minutes = get_period_minutes(timeframe)
    
    now = int(time.time() * 1000)  # Current time in milliseconds
    from_timestamp = now - (period_minutes * count * 60 * 1000)  # Calculate start time
    
    logger.info(f"Requesting {count} {timeframe} historical bars...")
    logger.info(f"From: {datetime.fromtimestamp(from_timestamp/1000)}")
    logger.info(f"To: {datetime.fromtimestamp(now/1000)}")
    
    trendbars_req = ProtoOAGetTrendbarsReq()
    trendbars_req.ctidTraderAccountId = ACCOUNT_ID
    trendbars_req.symbolId = symbol_id
    trendbars_req.period = period  # Use the correct enum value
    trendbars_req.fromTimestamp = from_timestamp
    trendbars_req.toTimestamp = now
    
    d = client.send(trendbars_req)
    d.addCallback(lambda response: on_trendbars_response(response, timeframe))
    d.addErrback(on_error)

def get_period_minutes(timeframe):
    """Convert timeframe to minutes for timestamp calculation"""
    if timeframe == 'M1':
        return 1
    elif timeframe == 'M2':
        return 2
    elif timeframe == 'M3':
        return 3
    elif timeframe == 'M4':
        return 4
    elif timeframe == 'M5':
        return 5
    elif timeframe == 'M10':
        return 10
    elif timeframe == 'M15':
        return 15
    elif timeframe == 'M30':
        return 30
    elif timeframe == 'H1':
        return 60
    elif timeframe == 'H4':
        return 240
    elif timeframe == 'H12':
        return 720
    elif timeframe == 'D1':
        return 1440
    elif timeframe == 'W1':
        return 10080
    elif timeframe == 'MN1':
        return 43200
    else:
        return 1  # Default to 1 minute

def on_trendbars_response(response, timeframe):
    global current_timeframe_index, historical_data_fetched
    
    # Extract the trendbars using the Protobuf helper
    trendbars = Protobuf.extract(response)
    
    if not hasattr(trendbars, 'trendbar') or len(trendbars.trendbar) == 0:
        logger.warning(f"No data received for {timeframe}")
        current_timeframe_index += 1
        start_data_fetching()
        return
    
    logger.info(f"Received {len(trendbars.trendbar)} historical trendbars for {timeframe}")
    
    # Format data in the required format
    formatted_data = []
    for bar in trendbars.trendbar:
        timestamp = datetime.fromtimestamp(bar.utcTimestampInMinutes * 60)
        date_str = timestamp.strftime('%Y-%m-%d %H:%M')
        
        # Convert prices from points to actual prices (divide by 100000)
        # Check which fields are available
        if hasattr(bar, 'low') and hasattr(bar, 'deltaOpen') and hasattr(bar, 'deltaHigh') and hasattr(bar, 'deltaClose'):
            # Using delta format
            low_price = bar.low / 100000
            open_price = (bar.low + bar.deltaOpen) / 100000
            high_price = (bar.low + bar.deltaHigh) / 100000
            close_price = (bar.low + bar.deltaClose) / 100000
        else:
            # Try direct access
            try:
                low_price = getattr(bar, 'low', 0) / 100000
                open_price = getattr(bar, 'open', low_price) / 100000
                high_price = getattr(bar, 'high', low_price) / 100000
                close_price = getattr(bar, 'close', low_price) / 100000
            except AttributeError:
                logger.error(f"Error: Unable to access price fields in trendbar")
                continue
        
        volume = getattr(bar, 'volume', 0)
        
        # Format as required: "2009-04-01 20:00 1.32310 1.32470 1.32245 1.32461 6663"
        line = f"{date_str} {open_price:.5f} {high_price:.5f} {low_price:.5f} {close_price:.5f} {volume}"
        formatted_data.append(line)
    
    # Print the first few bars
    for i, line in enumerate(formatted_data[:5]):
        logger.info(f"{timeframe}: {line}")
    
    if len(formatted_data) > 5:
        logger.info(f"... and {len(formatted_data) - 5} more bars")
    
    # Save to file
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{args.symbol}_{timeframe}.csv"
    
    with open(filename, 'w') as f:
        f.write(f"# Historical data for {args.symbol} {timeframe}\n")
        f.write("# timestamp open high low close volume\n")
        f.write('\n'.join(formatted_data))
    
    logger.info(f"Historical data saved to {filename}")
    
    # Move to the next timeframe
    current_timeframe_index += 1
    historical_data_fetched = True
    
    # Process the next timeframe
    start_data_fetching()

def subscribe_to_live_data():
    global live_data_subscribed
    
    if live_data_subscribed:
        return
    
    logger.info(f"Subscribing to live data for {args.symbol}...")
    
    # First subscribe to spots
    spot_sub_req = ProtoOASubscribeSpotsReq()
    spot_sub_req.ctidTraderAccountId = ACCOUNT_ID
    spot_sub_req.symbolId.append(symbol_id)
    d = client.send(spot_sub_req)
    d.addCallback(on_spot_subscription_response)
    d.addErrback(on_error)

def on_spot_subscription_response(response):
    logger.info(f"Successfully subscribed to {args.symbol} spots")
    
    # Now subscribe to live trend bars for each timeframe
    for timeframe in timeframes_to_process:
        if timeframe in TIMEFRAME_PERIODS:
            period = TIMEFRAME_PERIODS[timeframe]
            subscribe_to_live_trendbars(period, timeframe)

def subscribe_to_live_trendbars(period, timeframe):
    logger.info(f"Subscribing to live {timeframe} trendbars for {args.symbol}...")
    
    trendbar_sub_req = ProtoOASubscribeLiveTrendbarReq()
    trendbar_sub_req.ctidTraderAccountId = ACCOUNT_ID
    trendbar_sub_req.symbolId = symbol_id
    trendbar_sub_req.period = period
    
    d = client.send(trendbar_sub_req)
    d.addCallback(lambda response: on_trendbar_subscription_response(response, timeframe))
    d.addErrback(on_error)

def on_trendbar_subscription_response(response, timeframe):
    global live_data_subscribed
    
    logger.info(f"Successfully subscribed to {args.symbol} {timeframe} live trend bars")
    live_data_subscribed = True
    
    # Set a timeout to stop after receiving some live data
    if timeframe == timeframes_to_process[-1]:  # If this is the last timeframe
        logger.info(f"Waiting for live data... (Will automatically stop after 60 seconds)")
        logger.info(f"Press Ctrl+C to stop earlier")
        reactor.callLater(60, reactor.stop)  # Stop after 60 seconds of live data

def on_disconnected(client, reason):
    logger.info(f"Disconnected: {reason}")
    try:
        reactor.stop()
    except:
        pass  # Reactor might already be stopped

def on_message_received(client, message):
    try:
        # Extract the message
        extracted_message = Protobuf.extract(message)
        message_type = type(extracted_message).__name__
        
        # Check if it's a spot event with trendbar data
        if hasattr(extracted_message, 'trendbar') and len(extracted_message.trendbar) > 0:
            # This is a trendbar update
            period = getattr(extracted_message, 'period', None)
            for trendbar in extracted_message.trendbar:
                process_trendbar(trendbar, period)
        elif hasattr(extracted_message, 'symbolId') and hasattr(extracted_message, 'bid') and hasattr(extracted_message, 'ask'):
            # This is a spot price update
            symbol_id = extracted_message.symbolId
            bid = extracted_message.bid / 100000
            ask = extracted_message.ask / 100000
            if args.verbose:  # Only show if verbose mode is enabled
                logger.info(f"SPOT UPDATE: {args.symbol} - Bid: {bid:.5f}, Ask: {ask:.5f}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()

def process_trendbar(bar, period=None):
    try:
        # Convert period to timeframe string
        if period is not None:
            # Reverse lookup the timeframe from the period value
            timeframe = next((tf for tf, p in TIMEFRAME_PERIODS.items() if p == period), f"Period{period}")
        else:
            timeframe = "Unknown"
        
        # Get the timestamp in seconds
        bar_timestamp = bar.utcTimestampInMinutes * 60
        timestamp = datetime.fromtimestamp(bar_timestamp)
        date_str = timestamp.strftime('%Y-%m-%d %H:%M')
        
        # Convert prices from points to actual prices (divide by 100000)
        # Check which fields are available
        if hasattr(bar, 'low') and hasattr(bar, 'deltaOpen') and hasattr(bar, 'deltaHigh') and hasattr(bar, 'deltaClose'):
            # Using delta format
            low_price = bar.low / 100000
            open_price = (bar.low + bar.deltaOpen) / 100000
            high_price = (bar.low + bar.deltaHigh) / 100000
            close_price = (bar.low + bar.deltaClose) / 100000
        else:
            # Try direct access
            try:
                low_price = getattr(bar, 'low', 0) / 100000
                open_price = getattr(bar, 'open', low_price) / 100000
                high_price = getattr(bar, 'high', low_price) / 100000
                close_price = getattr(bar, 'close', low_price) / 100000
            except AttributeError:
                logger.error(f"Error: Unable to access price fields in trendbar")
                return
        
        volume = getattr(bar, 'volume', 0)
        
        # Format as required: "2009-04-01 20:00 1.32310 1.32470 1.32245 1.32461 6663"
        line = f"{date_str} {open_price:.5f} {high_price:.5f} {low_price:.5f} {close_price:.5f} {volume}"
        
        logger.info(f"LIVE {timeframe} TRENDBAR: {line}")
        
        # Append to file
        output_dir = "data"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{output_dir}/{args.symbol}_{timeframe}_live.csv"
        
        with open(filename, 'a') as f:
            f.write(f"{line}\n")
        
    except Exception as e:
        logger.error(f"Error processing trendbar: {e}")
        import traceback
        traceback.print_exc()


def main():
    logger.info(f"Starting connection to cTrader for {args.symbol} with timeframes {args.timeframes}...")
    
    # Set callbacks
    client.setConnectedCallback(on_connected)
    client.setDisconnectedCallback(on_disconnected)
    client.setMessageReceivedCallback(on_message_received)
    
    # Start the client service
    client.startService()
    
    try:
        reactor.run()
    except KeyboardInterrupt:
        logger.info("\nStopping the client...")
        reactor.stop()
    
    # Check if connection was successful
    if not connection_successful:
        logger.error("Failed to connect to cTrader API")
        return 1
    
    # Check if we fetched historical data successfully
    if not args.list_symbols and not args.list_timeframes and not historical_data_fetched:
        logger.error("Failed to fetch historical data")
        return 1
    
    logger.info("Test completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
