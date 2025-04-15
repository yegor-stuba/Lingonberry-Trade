"""
Comprehensive test for all market data sources
Tests both current prices and historical OHLCV data
"""

import logging
import asyncio
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_SYMBOLS = {
    'forex': ['EURUSD', 'GBPUSD', 'USDJPY'],
    'crypto': ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
}

TEST_TIMEFRAMES = ['15m', '1h', '4h']
CANDLE_COUNT = 100  # Number of candles to fetch for historical data

class MarketScanner:
    """Class to test various market data sources"""
    
    def __init__(self):
        """Initialize the market scanner"""
        self.results = {
            'current_prices': {},
            'historical_data': {}
        }
    
    async def test_exchange_rate_api(self, symbol):
        """Test ExchangeRate API for current forex prices"""
        try:
            import aiohttp
            
            # Format symbol
            if len(symbol) == 6:
                base = symbol[:3]
                quote = symbol[3:]
            else:
                parts = symbol.split('/')
                base = parts[0]
                quote = parts[1] if len(parts) > 1 else 'USD'
            
            # Construct URL
            url = f"https://open.er-api.com/v6/latest/{base}"
            
            # Send request
            logger.info(f"Testing ExchangeRate API for {symbol}...")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"Error fetching forex data: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if not data or not data.get('rates') or quote not in data['rates']:
                        logger.error("No forex data returned")
                        return None
                    
                    # Extract price
                    rate = data['rates'][quote]
                    
                    # Return price information
                    return {
                        'symbol': symbol,
                        'price': rate,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'exchangerate-api.com'
                    }
            
        except Exception as e:
            logger.error(f"Error testing ExchangeRate API for {symbol}: {e}")
            return None
    
    async def test_ccxt_current_price(self, symbol):
        """Test CCXT for current crypto prices"""
        try:
            import ccxt.async_support as ccxt
            
            # Format symbol for CCXT
            if 'USDT' in symbol and '/' not in symbol:
                formatted_symbol = f"{symbol.replace('USDT', '')}/USDT"
            elif 'USD' in symbol and '/' not in symbol and 'USDT' not in symbol:
                formatted_symbol = f"{symbol.replace('USD', '')}/USD"
            else:
                formatted_symbol = symbol
            
            # Initialize exchange
            exchange = ccxt.binance({
                'enableRateLimit': True,
            })
            
            try:
                logger.info(f"Testing CCXT (Binance) for {symbol}...")
                
                # Fetch ticker
                ticker = await exchange.fetch_ticker(formatted_symbol)
                
                # Close exchange
                await exchange.close()
                
                if not ticker:
                    logger.error(f"No ticker data returned for {formatted_symbol}")
                    return None
                
                # Extract price
                price = ticker['last']
                
                # Return price information
                return {
                    'symbol': symbol,
                    'price': price,
                    'bid': ticker.get('bid'),
                    'ask': ticker.get('ask'),
                    'volume': ticker.get('volume'),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'ccxt.binance'
                }
                
            except Exception as e:
                # Make sure to close the exchange
                await exchange.close()
                raise e
            
        except Exception as e:
            logger.error(f"Error testing CCXT for {symbol}: {e}")
            return None
    
    async def test_ccxt_historical_data(self, symbol, timeframe, limit=100):
        """Test CCXT for historical OHLCV data"""
        try:
            import ccxt.async_support as ccxt
            
            # Format symbol for CCXT
            if 'USDT' in symbol and '/' not in symbol:
                formatted_symbol = f"{symbol.replace('USDT', '')}/USDT"
            elif 'USD' in symbol and '/' not in symbol and 'USDT' not in symbol:
                formatted_symbol = f"{symbol.replace('USD', '')}/USD"
            else:
                formatted_symbol = symbol
            
            # Initialize exchange
            exchange = ccxt.binance({
                'enableRateLimit': True,
            })
            
            try:
                logger.info(f"Testing CCXT historical data for {symbol} on {timeframe} timeframe...")
                
                # Fetch OHLCV data
                ohlcv = await exchange.fetch_ohlcv(formatted_symbol, timeframe, limit=limit)
                
                # Close exchange
                await exchange.close()
                
                if not ohlcv:
                    logger.error(f"No OHLCV data returned for {formatted_symbol} on {timeframe}")
                    return None
                
                # Convert to DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                logger.info(f"Fetched {len(df)} candles for {symbol} on {timeframe}")
                
                # Return data information
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'candle_count': len(df),
                    'start_date': df.index[0].isoformat(),
                    'end_date': df.index[-1].isoformat(),
                    'source': 'ccxt.binance',
                    'data': df
                }
                
            except Exception as e:
                # Make sure to close the exchange
                await exchange.close()
                raise e
            
        except Exception as e:
            logger.error(f"Error testing CCXT historical data for {symbol} on {timeframe}: {e}")
            return None
    
    async def test_alpha_vantage_forex(self, symbol, interval='60min'):
        """Test Alpha Vantage API for forex data"""
        try:
            import aiohttp
            from trading_bot.config import credentials
            
            # Get API key
            api_key = credentials.ALPHA_VANTAGE_API_KEY
            
            if not api_key:
                logger.error("Alpha Vantage API key not found")
                return None
            
            # Format symbol
            if len(symbol) == 6:
                from_currency = symbol[:3]
                to_currency = symbol[3:]
            else:
                parts = symbol.split('/')
                from_currency = parts[0]
                to_currency = parts[1] if len(parts) > 1 else 'USD'
            
            # Construct URL
            url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={from_currency}&to_symbol={to_currency}&interval={interval}&apikey={api_key}"
            
            # Send request
            logger.info(f"Testing Alpha Vantage for {symbol} on {interval}...")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"Error fetching Alpha Vantage data: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if 'Error Message' in data:
                        logger.error(f"Alpha Vantage error: {data['Error Message']}")
                        return None
                    
                    # Extract time series data
                    time_series_key = f"Time Series FX ({interval})"
                    
                    if time_series_key not in data:
                        logger.error(f"No time series data found in Alpha Vantage response")
                        return None
                    
                    time_series = data[time_series_key]
                    
                    # Convert to DataFrame
                    df = pd.DataFrame.from_dict(time_series, orient='index')
                    
                    # Rename columns
                    df.columns = [col.split('. ')[1] for col in df.columns]
                    df.rename(columns={
                        'open': 'open',
                        'high': 'high',
                        'low': 'low',
                        'close': 'close',
                        'volume': 'volume'
                    }, inplace=True)
                    
                    # Convert to numeric
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col])
                    
                    # Convert index to datetime
                    df.index = pd.to_datetime(df.index)
                    df.index.name = 'timestamp'
                    
                    # Sort by datetime
                    df.sort_index(inplace=True)
                    
                    logger.info(f"Fetched {len(df)} candles for {symbol} from Alpha Vantage")
                    
                    # Return data information
                    return {
                        'symbol': symbol,
                        'timeframe': interval,
                        'candle_count': len(df),
                        'start_date': df.index[0].isoformat(),
                        'end_date': df.index[-1].isoformat(),
                        'source': 'alphavantage',
                        'data': df
                    }
            
        except Exception as e:
            logger.error(f"Error testing Alpha Vantage for {symbol}: {e}")
            return None
    
    async def test_csv_data(self, symbol, timeframe):
        """Test CSV data files"""
        try:
            # Determine market type
            market_type = 'crypto' if any(crypto_marker in symbol for crypto_marker in ['BTC', 'ETH', 'USDT', 'XRP', 'ADA']) else 'forex'
            
            # Map timeframe to CSV suffix
            timeframe_map = {
                '1m': '1',
                '5m': '5',
                '15m': '15',
                '30m': '30',
                '1h': '60',
                '4h': '240',
                '1d': '1440'
            }
            
            if timeframe not in timeframe_map:
                logger.error(f"Invalid timeframe for CSV: {timeframe}")
                return None
            
            csv_suffix = timeframe_map[timeframe]
            
            # Format symbol for CSV
            if '/' in symbol:
                formatted_symbol = symbol.replace('/', '')
            else:
                formatted_symbol = symbol
            
            # Construct CSV path
            csv_path = Path(f"charts/{market_type.lower()}/{formatted_symbol}{csv_suffix}.csv")
            
            logger.info(f"Testing CSV data for {symbol} on {timeframe} from {csv_path}...")
            
            if not csv_path.exists():
                logger.error(f"CSV file not found: {csv_path}")
                return None
            
            # Read CSV file
            df = pd.read_csv(csv_path, sep='\t', header=None)
            
            # Rename columns
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            
            # Convert datetime
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            # Set datetime as index
            df.set_index('datetime', inplace=True)
            
            logger.info(f"Loaded {len(df)} candles from CSV for {symbol} on {timeframe}")
            
            # Return data information
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'candle_count': len(df),
                'start_date': df.index[0].isoformat(),
                'end_date': df.index[-1].isoformat(),
                'source': 'csv',
                'data': df
            }
            
        except Exception as e:
            logger.error(f"Error testing CSV data for {symbol} on {timeframe}: {e}")
            return None
    
    async def run_tests(self):
        """Run all tests"""
        # Test current prices
        logger.info("Testing current prices...")
        
        # Test forex prices with ExchangeRate API
        for symbol in TEST_SYMBOLS['forex']:
            result = await self.test_exchange_rate_api(symbol)
            if result:
                self.results['current_prices'][f"{symbol}_exchangerate"] = result
        
        # Test crypto prices with CCXT
        for symbol in TEST_SYMBOLS['crypto']:
            result = await self.test_ccxt_current_price(symbol)
            if result:
                self.results['current_prices'][f"{symbol}_ccxt"] = result
        
        # Test historical data
        logger.info("Testing historical data...")
        
        # Test forex historical data from CSV
        for symbol in TEST_SYMBOLS['forex']:
            for timeframe in TEST_TIMEFRAMES:
                result = await self.test_csv_data(symbol, timeframe)
                if result:
                    key = f"{symbol}_{timeframe}_csv"
                    self.results['historical_data'][key] = {
                        'symbol': result['symbol'],
                        'timeframe': result['timeframe'],
                        'candle_count': result['candle_count'],
                        'start_date': result['start_date'],
                        'end_date': result['end_date'],
                        'source': result['source']
                    }
                    # Save a sample chart
                    self._save_sample_chart(result['data'], symbol, timeframe, 'csv')
        
        # Test crypto historical data from CCXT
        for symbol in TEST_SYMBOLS['crypto']:
            for timeframe in TEST_TIMEFRAMES:
                result = await self.test_ccxt_historical_data(symbol, timeframe, CANDLE_COUNT)
                if result:
                    key = f"{symbol}_{timeframe}_ccxt"
                    self.results['historical_data'][key] = {
                        'symbol': result['symbol'],
                        'timeframe': result['timeframe'],
                        'candle_count': result['candle_count'],
                        'start_date': result['start_date'],
                        'end_date': result['end_date'],
                        'source': result['source']
                    }
                    # Save a sample chart
                    self._save_sample_chart(result['data'], symbol, timeframe, 'ccxt')
        
        # Test forex historical data from Alpha Vantage
        # Map timeframes to Alpha Vantage intervals
        av_intervals = {
            '15m': '15min',
            '1h': '60min',
            '4h': '60min'  # Alpha Vantage doesn't have 4h, use 1h instead
        }
        
        for symbol in TEST_SYMBOLS['forex'][:1]:  # Test only one forex pair to avoid API limits
            for timeframe in TEST_TIMEFRAMES[:2]:  # Test only a couple of timeframes
                interval = av_intervals.get(timeframe)
                result = await self.test_alpha_vantage_forex(symbol, interval)
                if result:
                    key = f"{symbol}_{timeframe}_alphavantage"
                    self.results['historical_data'][key] = {
                        'symbol': result['symbol'],
                        'timeframe': result['timeframe'],
                        'candle_count': result['candle_count'],
                        'start_date': result['start_date'],
                        'end_date': result['end_date'],
                        'source': result['source']
                    }
                    # Save a sample chart
                    self._save_sample_chart(result['data'], symbol, timeframe, 'alphavantage')
        
        # Test crypto historical data from CSV
        for symbol in TEST_SYMBOLS['crypto']:
            # Convert symbol format for CSV lookup
            csv_symbol = symbol.replace('/', '')
            for timeframe in TEST_TIMEFRAMES:
                result = await self.test_csv_data(csv_symbol, timeframe)
                if result:
                    key = f"{symbol}_{timeframe}_csv"
                    self.results['historical_data'][key] = {
                        'symbol': result['symbol'],
                        'timeframe': result['timeframe'],
                        'candle_count': result['candle_count'],
                        'start_date': result['start_date'],
                        'end_date': result['end_date'],
                        'source': result['source']
                    }
                    # Save a sample chart
                    self._save_sample_chart(result['data'], symbol, timeframe, 'csv')
        
        # Save all results to file
        self._save_results()
    
    def _save_sample_chart(self, df, symbol, timeframe, source):
        """Save a sample chart of the data"""
        try:
            # Create charts directory if it doesn't exist
            charts_dir = Path('test_charts')
            charts_dir.mkdir(exist_ok=True)
            
            # Create a candlestick chart
            plt.figure(figsize=(12, 6))
            
            # Plot candlesticks
            width = 0.6
            width2 = 0.1
            
            up = df[df.close >= df.open]
            down = df[df.close < df.open]
            
            # Plot up candles
            plt.bar(up.index, up.close-up.open, width, bottom=up.open, color='green')
            plt.bar(up.index, up.high-up.close, width2, bottom=up.close, color='green')
            plt.bar(up.index, up.low-up.open, width2, bottom=up.open, color='green')
            
            # Plot down candles
            plt.bar(down.index, down.close-down.open, width, bottom=down.open, color='red')
            plt.bar(down.index, down.high-down.open, width2, bottom=down.open, color='red')
            plt.bar(down.index, down.low-down.close, width2, bottom=down.close, color='red')
            
            # Format the chart
            plt.title(f'{symbol} - {timeframe} ({source})')
            plt.xlabel('Date')
            plt.ylabel('Price')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save the chart
            chart_path = charts_dir / f"{symbol.replace('/', '_')}_{timeframe}_{source}.png"
            plt.savefig(chart_path)
            plt.close()
            
            logger.info(f"Saved sample chart to {chart_path}")
            
        except Exception as e:
            logger.error(f"Error saving sample chart: {e}")
    
    def _save_results(self):
        """Save test results to file"""
        try:
            # Create results directory if it doesn't exist
            results_dir = Path('test_results')
            results_dir.mkdir(exist_ok=True)
            
            # Save results to file
            results_path = results_dir / f"market_scanner_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Convert results to serializable format
            serializable_results = {
                'current_prices': self.results['current_prices'],
                'historical_data': self.results['historical_data'],
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'current_prices_count': len(self.results['current_prices']),
                    'historical_data_count': len(self.results['historical_data'])
                }
            }
            
            with open(results_path, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            
            logger.info(f"Saved test results to {results_path}")
            
            # Generate summary report
            self._generate_summary_report(results_path)
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def _generate_summary_report(self, results_path):
        """Generate a summary report of the test results"""
        try:
            # Create summary report
            report = [
                "# Market Data Sources Test Report",
                f"Generated on: {datetime.now().isoformat()}",
                "",
                "## Current Prices",
                "",
                "| Symbol | Price | Source |",
                "| ------ | ----- | ------ |"
            ]
            
            # Add current prices to report
            for key, result in self.results['current_prices'].items():
                report.append(f"| {result['symbol']} | {result['price']} | {result['source']} |")
            
            report.extend([
                "",
                "## Historical Data",
                "",
                "| Symbol | Timeframe | Candles | Start Date | End Date | Source |",
                "| ------ | --------- | ------- | ---------- | -------- | ------ |"
            ])
            
            # Add historical data to report
            for key, result in self.results['historical_data'].items():
                report.append(
                    f"| {result['symbol']} | {result['timeframe']} | {result['candle_count']} | "
                    f"{result['start_date']} | {result['end_date']} | {result['source']} |"
                )
            
            # Save report to file
            report_path = Path('test_results') / "market_data_report.md"
            with open(report_path, 'w') as f:
                f.write('\n'.join(report))
            
            logger.info(f"Generated summary report at {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")

async def run_market_scanner():
    """Run the market scanner"""
    scanner = MarketScanner()
    await scanner.run_tests()

if __name__ == "__main__":
    logger.info("Starting market scanner test...")
    asyncio.run(run_market_scanner())
    logger.info("Market scanner test completed")
