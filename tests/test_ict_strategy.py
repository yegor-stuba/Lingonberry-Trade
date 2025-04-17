"""
Test script for ICT strategy
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime

# Add the parent directory to the path so we can import from trading_bot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_bot.strategy.ict_strategy import ICTStrategy
from trading_bot.strategy.signal_generator import SignalGenerator
from trading_bot.data.data_processor import DataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_test_data(file_path):
    """Load test data from CSV file with flexible format detection"""
    try:
        # First check if it's a standard format with headers
        first_line = open(file_path, 'r').readline().strip()
        
        if "Historical data" in first_line:
            # Skip the first two lines (headers)
            df = pd.read_csv(file_path, skiprows=2, header=None, sep=' ')
            df.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        else:
            # Try to detect separator (tab or space)
            sep = '\t' if '\t' in first_line else ' '
            
            # Load data
            df = pd.read_csv(file_path, header=None, sep=sep)
            
            # Handle different formats
            if len(df.columns) == 6:  # Date and time combined
                df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            elif len(df.columns) == 7:  # Date and time separate
                df.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
                df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
                df.drop(['date', 'time'], axis=1, inplace=True)
            else:
                # Try to infer format
                df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume'] + [f'extra{i}' for i in range(len(df.columns)-6)]
        
        # Ensure datetime is the index
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
        
        # Ensure column names are lowercase
        df.columns = [col.lower() for col in df.columns]
        
        logger.info(f"Loaded {len(df)} rows from {file_path}")
        return df
    
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def test_ict_strategy(symbol, timeframe, data_processor=None, use_live_data=False, bars=100):
    """
    Test the ICT strategy on a symbol and timeframe
    """
    # Get data
    if data_processor and use_live_data:
        logger.info(f"Fetching live data for {symbol} {timeframe} from API...")
        
        # Determine appropriate source based on symbol
        if symbol in ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'NAS100']:
            source = 'ctrader'
        else:
            source = 'crypto'
            
        df = data_processor.get_data(symbol, timeframe, bars=bars, source=source)
    else:
        # Try to load from file
        file_path = f"data/{symbol}_{timeframe}.csv"
        if not os.path.exists(file_path):
            # Try alternative paths
            alt_paths = [
                f"charts/crypto/{symbol}{timeframe}.csv",
                f"charts/forex/{symbol}{timeframe}.csv",
                f"data/{symbol.replace('/', '')}_H1.csv"
            ]
            
            for path in alt_paths:
                if os.path.exists(path):
                    file_path = path
                    break
        
        df = load_test_data(file_path)
    
    if df is None or df.empty:
        logger.error(f"No test data available for {symbol} {timeframe}")
        return
    
    logger.info(f"Successfully loaded {len(df)} candles for {symbol} {timeframe}")
    
    # Initialize strategy
    ict_strategy = ICTStrategy()
    signal_generator = SignalGenerator()
    signal_generator.add_strategy("ict", ict_strategy)
    
    logger.info(f"Testing ICT strategy with {symbol} data")
    
    # Generate signals
    signals = signal_generator.generate_signals(symbol, df, timeframe)
    
    # Get analysis results
    analysis = ict_strategy.last_analysis
    
    if analysis:
        logger.info(f"Analysis bias: {analysis.get('bias', 'unknown')}")
        logger.info(f"Found {len(analysis.get('order_blocks', []))} order blocks")
        logger.info(f"Found {len(analysis.get('fair_value_gaps', []))} fair value gaps")
        logger.info(f"Found {len(analysis.get('liquidity_levels', []))} liquidity levels")
        
        # ICT-specific concepts
        ict_concepts = analysis.get('ict_concepts', {})
        logger.info(f"Found {len(ict_concepts.get('ote_zones', []))} OTE zones")
        logger.info(f"Found {len(ict_concepts.get('breaker_blocks', []))} breaker blocks")
        logger.info(f"Found {len(ict_concepts.get('kill_zones', {}))} kill zones")
    
    # Log signals
    logger.info(f"Generated {len(signals)} signals")
    
    # Print signals
    for i, signal in enumerate(signals):
        logger.info(f"Signal {i+1}:")
        logger.info(f"  Type: {signal.get('type')}")
        logger.info(f"  Entry: {signal.get('entry')}")
        logger.info(f"  Stop Loss: {signal.get('stop_loss')}")
        logger.info(f"  Take Profit: {signal.get('take_profit')}")
        logger.info(f"  Risk-Reward: {signal.get('risk_reward', 0):.2f}")
        logger.info(f"  Strength: {signal.get('strength', 0)}")
        logger.info(f"  Reason: {signal.get('reason', 'No reason provided')}")

if __name__ == "__main__":
    # Test with crypto
    test_ict_strategy("BTCUSD", "H1")
    
    # Test with forex
    test_ict_strategy("EURUSD", "H1")
