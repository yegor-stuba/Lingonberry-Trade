"""
Test script for SMC strategy
"""

import os
import sys
import pandas as pd
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import time
import asyncio

# Add the parent directory to the path so we can import from trading_bot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_bot.strategy.smc_strategy import SMCStrategy
from trading_bot.strategy.signal_generator import SignalGenerator
from trading_bot.utils.visualization import create_price_chart, create_trade_chart
from trading_bot.data.data_processor import DataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_test_data(file_path):
    """Load test data from CSV file with flexible format detection"""
    try:
        # First check if it's a standard format with headers
        if "Historical data" in open(file_path, 'r').readline():
            # Skip the first two lines (headers)
            df = pd.read_csv(file_path, skiprows=2, header=None, sep=' ')
            df.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
        else:
            # Try to detect separator (tab or space)
            first_line = open(file_path, 'r').readline().strip()
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
        
        # Ensure datetime is the index
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
        
        logger.info(f"Loaded {len(df)} rows from {file_path}")
        return df
    
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def test_smc_strategy(symbol, timeframe, data_processor, use_live_data=False, bars=100):
    """
    Test the SMC strategy on a symbol and timeframe
    
    Args:
        symbol (str): Trading symbol
        timeframe (str): Timeframe
        data_processor (DataProcessor): Data processor instance
        use_live_data (bool): Whether to use live data
        bars (int): Number of bars to fetch
    """
    from pathlib import Path
    
    # Wait for connections to be established if using live data
    if use_live_data:
        logger.info("Waiting for API connections to be established...")
        time.sleep(2)  # Give time for connections to be established
    
    # Get data - explicitly specify source based on symbol
    if use_live_data:
        logger.info(f"Fetching live data for {symbol} {timeframe} from API...")
        
        # Determine appropriate source based on symbol
        if symbol in ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'NAS100']:
            source = 'ctrader'
        else:
            source = 'crypto'
            
        df = data_processor.get_data(symbol, timeframe, bars=bars, source=source)
    else:
        df = data_processor.get_data(symbol, timeframe, bars=bars)
    
    if df is None or df.empty:
        logger.error(f"No test data available for {symbol} {timeframe}")
        return
    
    logger.info(f"Successfully loaded {len(df)} candles for {symbol} {timeframe}")
    
    # Initialize strategy
    smc_strategy = SMCStrategy()
    signal_generator = SignalGenerator()
    signal_generator.strategies = [smc_strategy]  # Directly set the strategies list
    
    logger.info(f"Testing SMC strategy with {symbol} data")
    
    # Generate signals
    try:
        signals = signal_generator.generate_signals(symbol, df, timeframe)
        
        # Get analysis results
        analysis = smc_strategy.last_analysis
        
        if analysis:
            logger.info(f"Analysis bias: {analysis.get('bias', 'unknown')}")
            logger.info(f"Found {len(analysis.get('order_blocks', []))} order blocks")
            logger.info(f"Found {len(analysis.get('fair_value_gaps', []))} fair value gaps")
            logger.info(f"Found {len(analysis.get('liquidity_levels', []))} liquidity levels")
        
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
        
        # Generate trade setup for the best signal
        if signals:
            best_signal = signals[0]
            trade_setup = smc_strategy.get_trade_setup(best_signal)
            
            logger.info("Best Trade Setup:")
            logger.info(f"  Symbol: {trade_setup.get('symbol')}")
            logger.info(f"  Direction: {trade_setup.get('direction')}")
            logger.info(f"  Entry: {trade_setup.get('entry_price')}")
            logger.info(f"  Stop Loss: {trade_setup.get('stop_loss')}")
            logger.info(f"  Take Profit: {trade_setup.get('take_profit')}")
            logger.info(f"  Risk-Reward: {trade_setup.get('risk_reward')}")
            logger.info(f"  Risk %: {trade_setup.get('risk_pct')}")
            logger.info(f"  Reward %: {trade_setup.get('reward_pct')}")
            
            # Create trade chart
            if len(df) > 0:
                try:
                    trade_data = {
                        'symbol': symbol,
                        'direction': signal.get('type', 'BUY').upper(),
                        'entry_price': signal.get('entry', 0),
                        'stop_loss': signal.get('stop_loss', 0),
                        'take_profit': signal.get('take_profit', 0)
                    }
                
                    # Create chart without the linestyle parameter
                    chart_buffer = create_trade_chart(df.tail(50), trade_data)
                
                    if chart_buffer:
                        # Save chart to file
                        output_dir = Path("output")
                        output_dir.mkdir(exist_ok=True)
                    
                        chart_path = output_dir / f"{symbol}_{timeframe}_signal_{i}.png"
                    
                        with open(chart_path, 'wb') as f:
                            f.write(chart_buffer.getvalue())
                    
                        logger.info(f"  Chart saved to {chart_path}")
                    else:
                        logger.error(f"  Failed to create chart for signal {i}")
                except Exception as e:
                    logger.error(f"  Error creating chart: {e}")
    
    except Exception as e:
        logger.error(f"Error analyzing {symbol} {timeframe}: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run the SMC strategy test"""
    # Initialize a single data processor for all tests
    # This avoids the Twisted reactor restart issue
    data_processor = DataProcessor(use_live_data=True)
    
    try:
        # Test with forex data - use more bars to ensure enough data for analysis
        logger.info("\n=== Testing with EURUSD H1 data ===")
        test_smc_strategy("EURUSD", "H1", data_processor, use_live_data=True, bars=200)
        
        # Test with crypto data - use BTCUSDT instead of BTCUSD
        logger.info("\n=== Testing with BTCUSDT H1 data ===")
        test_smc_strategy("BTCUSDT", "H1", data_processor, use_live_data=True, bars=200)
        
        # Test with gold (XAUUSD)
        logger.info("\n=== Testing with XAUUSD H1 data (Gold) ===")
        test_smc_strategy("XAUUSD", "H1", data_processor, use_live_data=True, bars=200)
        
        # Test with NAS100 (NAS100)
        logger.info("\n=== Testing with NAS100 H1 data (Nasdaq 100) ===")
        test_smc_strategy("NAS100", "H1", data_processor, use_live_data=True, bars=200)
        
        logger.info("All tests completed")
    
    finally:
        # Ensure data processor is properly closed
        logger.info("Closing data processor connections...")
        data_processor.close()
        
        # Clean up any remaining asyncio resources
        try:
            # Get all running tasks
            pending = asyncio.all_tasks(asyncio.get_event_loop())
            if pending:
                logger.info(f"Cancelling {len(pending)} pending tasks...")
                for task in pending:
                    task.cancel()
        except RuntimeError:
            # Event loop might already be closed
            pass

if __name__ == "__main__":
    main()


