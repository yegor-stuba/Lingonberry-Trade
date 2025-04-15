"""
Test for EOD Historical Data (EODHD) API
Tests various endpoints for stock, forex, and crypto data
"""

import logging
import asyncio
import aiohttp
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

from trading_bot.config import credentials

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EODHDTest:
    """Test class for EOD Historical Data API"""
    
    def __init__(self):
        """Initialize the test"""
        # Check if EODHD API key exists in credentials
        self.api_key = getattr(credentials, 'EODHD_API_KEY', None)
        if not self.api_key:
            logger.error("EODHD API key not found in credentials.py")
            logger.info("Please add EODHD_API_KEY to credentials.py")
            raise ValueError("API key is required")
        
        self.base_url = "https://eodhistoricaldata.com/api"
        self.results_dir = Path("test_results/eodhd")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        
        self.results = {}
    
    async def test_real_time_stock(self, symbol):
        """
        Test real-time stock data endpoint
        Gets the latest price and volume information for a stock
        """
        try:
            endpoint = "real-time"
            url = f"{self.base_url}/{endpoint}/{symbol}?api_token={self.api_key}&fmt=json"
            
            logger.info(f"Testing real-time stock data for {symbol}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if isinstance(data, dict) and "error" in data:
                        logger.error(f"API error: {data['error']}")
                        return None
                    
                    result = {
                        "symbol": data.get("code", symbol),
                        "exchange": data.get("exchange", ""),
                        "price": data.get("close", 0),
                        "change": data.get("change", 0),
                        "change_percent": data.get("change_p", 0),
                        "volume": data.get("volume", 0),
                        "timestamp": data.get("timestamp", 0),
                        "endpoint": endpoint
                    }
                    
                    logger.info(f"Stock price: {result['price']}")
                    
                    # Save to results
                    key = f"stock_realtime_{symbol}"
                    self.results[key] = result
                    
                    return result
        
        except Exception as e:
            logger.error(f"Error testing real-time stock data: {e}")
            return None
    
    async def test_historical_stock(self, symbol, period="d", from_date=None, to_date=None):
        """
        Test historical stock data endpoint
        Gets historical OHLCV data for a stock
        
        Args:
            symbol (str): Stock symbol
            period (str): Data period ('d' for daily, 'w' for weekly, 'm' for monthly, 'h' for hourly)
            from_date (str): Start date in YYYY-MM-DD format
            to_date (str): End date in YYYY-MM-DD format
        """
        try:
            endpoint = "eod"
            
            # Set default dates if not provided
            if not to_date:
                to_date = datetime.now().strftime("%Y-%m-%d")
            
            if not from_date:
                # Default to 100 days ago for daily data
                days_ago = 100 if period == 'd' else 365
                from_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            url = f"{self.base_url}/{endpoint}/{symbol}?api_token={self.api_key}&period={period}&from={from_date}&to={to_date}&fmt=json"
            
            logger.info(f"Testing historical stock data for {symbol} with period {period}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if isinstance(data, dict) and "error" in data:
                        logger.error(f"API error: {data['error']}")
                        return None
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(data)
                    
                    if df.empty:
                        logger.error("No data returned")
                        return None
                    
                    # Convert date to datetime
                    df['date'] = pd.to_datetime(df['date'])
                    
                    # Set date as index
                    df.set_index('date', inplace=True)
                    
                    logger.info(f"Retrieved {len(df)} candles")
                    
                    # Save sample to CSV
                    period_name = {
                        'd': 'daily',
                        'w': 'weekly',
                        'm': 'monthly',
                        'h': 'hourly'
                    }.get(period, period)
                    
                    csv_path = self.results_dir / f"stock_historical_{symbol}_{period_name}.csv"
                    df.to_csv(csv_path)
                    logger.info(f"Saved sample data to {csv_path}")
                    
                    # Save to results
                    key = f"stock_historical_{symbol}_{period}"
                    self.results[key] = {
                        "symbol": symbol,
                        "period": period,
                        "period_name": period_name,
                        "from_date": from_date,
                        "to_date": to_date,
                        "candle_count": len(df),
                        "start_date": df.index[0].isoformat() if not df.empty else None,
                        "end_date": df.index[-1].isoformat() if not df.empty else None,
                        "endpoint": endpoint,
                        "sample_path": str(csv_path)
                    }
                    
                    return df
        
        except Exception as e:
            logger.error(f"Error testing historical stock data: {e}")
            return None
    
    async def test_forex_historical(self, symbol, period="d", from_date=None, to_date=None):
        """
        Test historical forex data endpoint
        Gets historical OHLCV data for a forex pair
        
        Args:
            symbol (str): Forex symbol (e.g., 'EUR.USD')
            period (str): Data period ('d' for daily, 'w' for weekly, 'm' for monthly, 'h' for hourly)
            from_date (str): Start date in YYYY-MM-DD format
            to_date (str): End date in YYYY-MM-DD format
        """
        try:
            endpoint = "eod"
            
            # Format symbol for EODHD (EUR.USD format)
            if '.' not in symbol and len(symbol) == 6:
                formatted_symbol = f"{symbol[:3]}.{symbol[3:]}"
            else:
                formatted_symbol = symbol
            
            # Set default dates if not provided
            if not to_date:
                to_date = datetime.now().strftime("%Y-%m-%d")
            
            if not from_date:
                # Default to 100 days ago for daily data
                days_ago = 100 if period == 'd' else 365
                from_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            url = f"{self.base_url}/{endpoint}/{formatted_symbol}?api_token={self.api_key}&period={period}&from={from_date}&to={to_date}&fmt=json"
            
            logger.info(f"Testing historical forex data for {formatted_symbol} with period {period}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if isinstance(data, dict) and "error" in data:
                        logger.error(f"API error: {data['error']}")
                        return None
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(data)
                    
                    if df.empty:
                        logger.error("No data returned")
                        return None
                    
                    # Convert date to datetime
                    df['date'] = pd.to_datetime(df['date'])
                    
                    # Set date as index
                    df.set_index('date', inplace=True)
                    
                    logger.info(f"Retrieved {len(df)} candles")
                    
                    # Save sample to CSV
                    period_name = {
                        'd': 'daily',
                        'w': 'weekly',
                        'm': 'monthly',
                        'h': 'hourly'
                    }.get(period, period)
                    
                    csv_path = self.results_dir / f"forex_historical_{formatted_symbol.replace('.', '')}_{period_name}.csv"
                    df.to_csv(csv_path)
                    logger.info(f"Saved sample data to {csv_path}")
                    
                    # Save to results
                    key = f"forex_historical_{formatted_symbol.replace('.', '')}_{period}"
                    self.results[key] = {
                        "symbol": formatted_symbol,
                        "period": period,
                        "period_name": period_name,
                        "from_date": from_date,
                        "to_date": to_date,
                        "candle_count": len(df),
                        "start_date": df.index[0].isoformat() if not df.empty else None,
                        "end_date": df.index[-1].isoformat() if not df.empty else None,
                        "endpoint": endpoint,
                        "sample_path": str(csv_path)
                    }
                    
                    return df
        
        except Exception as e:
            logger.error(f"Error testing historical forex data: {e}")
            return None
    
    async def test_crypto_historical(self, symbol, period="d", from_date=None, to_date=None):
        """
        Test historical crypto data endpoint
        Gets historical OHLCV data for a cryptocurrency
        
        Args:
            symbol (str): Crypto symbol (e.g., 'BTC-USD')
            period (str): Data period ('d' for daily, 'w' for weekly, 'm' for monthly, 'h' for hourly)
            from_date (str): Start date in YYYY-MM-DD format
            to_date (str): End date in YYYY-MM-DD format
        """
        try:
            endpoint = "eod"
            exchange = "CC" # Cryptocompare exchange code
            
            # Format symbol for EODHD (BTC-USD format)
            if '-' not in symbol:
                if '/' in symbol:
                    parts = symbol.split('/')
                    formatted_symbol = f"{parts[0]}-{parts[1]}"
                else:
                    formatted_symbol = f"{symbol}-USD"
            else:
                formatted_symbol = symbol
            
            # Set default dates if not provided
            if not to_date:
                to_date = datetime.now().strftime("%Y-%m-%d")
            
            if not from_date:
                # Default to 100 days ago for daily data
                days_ago = 100 if period == 'd' else 365
                from_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            url = f"{self.base_url}/{endpoint}/{exchange}.{formatted_symbol}?api_token={self.api_key}&period={period}&from={from_date}&to={to_date}&fmt=json"
            
            logger.info(f"Testing historical crypto data for {formatted_symbol} with period {period}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if isinstance(data, dict) and "error" in data:
                        logger.error(f"API error: {data['error']}")
                        return None
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(data)
                    
                    if df.empty:
                        logger.error("No data returned")
                        return None
                    
                    # Convert date to datetime
                    df['date'] = pd.to_datetime(df['date'])
                    
                    # Set date as index
                    df.set_index('date', inplace=True)
                    
                    logger.info(f"Retrieved {len(df)} candles")
                    
                    # Save sample to CSV
                    period_name = {
                        'd': 'daily',
                        'w': 'weekly',
                        'm': 'monthly',
                        'h': 'hourly'
                    }.get(period, period)
                    
                    csv_path = self.results_dir / f"crypto_historical_{formatted_symbol.replace('-', '')}_{period_name}.csv"
                    df.to_csv(csv_path)
                    logger.info(f"Saved sample data to {csv_path}")
                    
                    # Save to results
                    key = f"crypto_historical_{formatted_symbol.replace('-', '')}_{period}"
                    self.results[key] = {
                        "symbol": formatted_symbol,
                        "period": period,
                        "period_name": period_name,
                        "from_date": from_date,
                        "to_date": to_date,
                        "candle_count": len(df),
                        "start_date": df.index[0].isoformat() if not df.empty else None,
                        "end_date": df.index[-1].isoformat() if not df.empty else None,
                        "endpoint": endpoint,
                        "sample_path": str(csv_path)
                    }
                    
                    return df
        
        except Exception as e:
            logger.error(f"Error testing historical crypto data: {e}")
            return None
    
    async def test_intraday_data(self, symbol, interval="5m", from_timestamp=None, to_timestamp=None):
        """
        Test intraday data endpoint
        Gets intraday OHLCV data for a symbol
        
        Args:
            symbol (str): Symbol (stock, forex, crypto)
            interval (str): Time interval ('1m', '5m', '15m', '30m', '1h')
            from_timestamp (int): Start timestamp (Unix time)
            to_timestamp (int): End timestamp (Unix time)
        """
        try:
            endpoint = "intraday"
            
            # Set default timestamps if not provided
            if not to_timestamp:
                to_timestamp = int(datetime.now().timestamp())
            
            if not from_timestamp:
                # Default to 1 day ago
                from_timestamp = int((datetime.now() - timedelta(days=1)).timestamp())
            
            # Map interval to EODHD format
            interval_map = {
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h'
            }
            
            eodhd_interval = interval_map.get(interval, interval)
            
            url = f"{self.base_url}/{endpoint}/{symbol}?api_token={self.api_key}&interval={eodhd_interval}&from={from_timestamp}&to={to_timestamp}&fmt=json"
            
            logger.info(f"Testing intraday data for {symbol} with interval {interval}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if isinstance(data, dict) and "error" in data:
                        logger.error(f"API error: {data['error']}")
                        return None
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(data)
                    
                    if df.empty:
                        logger.error("No data returned")
                        return None
                    
                    # Convert timestamp to datetime
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                    
                    # Set datetime as index
                    df.set_index('datetime', inplace=True)
                    
                    logger.info(f"Retrieved {len(df)} candles")
                    
                    # Save sample to CSV
                    csv_path = self.results_dir / f"intraday_{symbol}_{interval}.csv"
                    df.to_csv(csv_path)
                    logger.info(f"Saved sample data to {csv_path}")
                    
                    # Save to results
                    key = f"intraday_{symbol}_{interval}"
                    self.results[key] = {
                        "symbol": symbol,
                        "interval": interval,
                        "from_timestamp": from_timestamp,
                        "to_timestamp": to_timestamp,
                        "candle_count": len(df),
                        "start_date": df.index[0].isoformat() if not df.empty else None,
                        "end_date": df.index[-1].isoformat() if not df.empty else None,
                        "endpoint": endpoint,
                        "sample_path": str(csv_path)
                    }
                    
                    return df
        
        except Exception as e:
            logger.error(f"Error testing intraday data: {e}")
            return None
    
    def save_results(self):
        """Save test results to file"""
        try:
            results_path = self.results_dir / f"eodhd_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Add timestamp to results
            self.results["timestamp"] = datetime.now().isoformat()
            self.results["api_key_used"] = self.api_key[:5] + "..." + self.api_key[-5:] if self.api_key else None
            
            with open(results_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            
            logger.info(f"Saved test results to {results_path}")
            
            # Generate summary report
            self._generate_summary_report()
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def _generate_summary_report(self):
        """Generate a summary report of the test results"""
        try:
            # Create summary report
            report = [
                "# EOD Historical Data API Test Report",
                f"Generated on: {datetime.now().isoformat()}",
                "",
                "## API Key Status",
                f"API Key: {'Valid' if self.api_key else 'Missing'}",
                "",
                "## Real-Time Stock Data",
                "",
                "| Symbol | Price | Change % | Volume | Timestamp |",
                "| ------ | ----- | -------- | ------ | --------- |"
            ]
            
            # Add real-time stock data to report
            for key, result in self.results.items():
                if key.startswith("stock_realtime_"):
                    report.append(
                        f"| {result.get('symbol', 'N/A')} | "
                        f"{result.get('price', 'N/A')} | "
                        f"{result.get('change_percent', 'N/A')} | "
                        f"{result.get('volume', 'N/A')} | "
                        f"{datetime.fromtimestamp(result.get('timestamp', 0)).isoformat() if result.get('timestamp') else 'N/A'} |"
                    )
            
            report.extend([
                "",
                "## Historical Stock Data",
                "",
                "| Symbol | Period | Candles | Start Date | End Date |",
                "| ------ | ------ | ------- | ---------- | -------- |"
            ])
            
            # Add historical stock data to report
            for key, result in self.results.items():
                if key.startswith("stock_historical_"):
                    report.append(
                        f"| {result.get('symbol', 'N/A')} | "
                        f"{result.get('period_name', 'N/A')} | "
                        f"{result.get('candle_count', 'N/A')} | "
                        f"{result.get('start_date', 'N/A')} | "
                        f"{result.get('end_date', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Historical Forex Data",
                "",
                "| Symbol | Period | Candles | Start Date | End Date |",
                "| ------ | ------ | ------- | ---------- | -------- |"
            ])
            
            # Add historical forex data to report
            for key, result in self.results.items():
                if key.startswith("forex_historical_"):
                    report.append(
                        f"| {result.get('symbol', 'N/A')} | "
                        f"{result.get('period_name', 'N/A')} | "
                        f"{result.get('candle_count', 'N/A')} | "
                        f"{result.get('start_date', 'N/A')} | "
                        f"{result.get('end_date', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Historical Crypto Data",
                "",
                "| Symbol | Period | Candles | Start Date | End Date |",
                "| ------ | ------ | ------- | ---------- | -------- |"
            ])
            
            # Add historical crypto data to report
            for key, result in self.results.items():
                if key.startswith("crypto_historical_"):
                    report.append(
                        f"| {result.get('symbol', 'N/A')} | "
                        f"{result.get('period_name', 'N/A')} | "
                        f"{result.get('candle_count', 'N/A')} | "
                        f"{result.get('start_date', 'N/A')} | "
                        f"{result.get('end_date', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Intraday Data",
                "",
                "| Symbol | Interval | Candles | Start Date | End Date |",
                "| ------ | -------- | ------- | ---------- | -------- |"
            ])
            
            # Add intraday data to report
            for key, result in self.results.items():
                if key.startswith("intraday_"):
                    report.append(
                        f"| {result.get('symbol', 'N/A')} | "
                        f"{result.get('interval', 'N/A')} | "
                        f"{result.get('candle_count', 'N/A')} | "
                        f"{result.get('start_date', 'N/A')} | "
                        f"{result.get('end_date', 'N/A')} |"
                    )
            
            # Save report to file
            report_path = self.results_dir / "eodhd_report.md"
            with open(report_path, 'w') as f:
                f.write('\n'.join(report))
            
            logger.info(f"Generated summary report at {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")

async def run_eodhd_test():
    """Run the EOD Historical Data API test"""
    try:
        test = EODHDTest()
        
        # Test historical forex data
        await test.test_forex_historical("EUR.USD", period="d")  # Daily
        await test.test_forex_historical("GBP.USD", period="d")  # Daily
        
        # Test historical crypto data
        await test.test_crypto_historical("BTC-USD", period="d")  # Daily
        await test.test_crypto_historical("ETH-USD", period="d")  # Daily
        
        # Test intraday data
        await test.test_intraday_data("AAPL.US", interval="5m")  # 5-minute
        await test.test_intraday_data("AAPL.US", interval="1h")  # 1-hour
        
        # Test forex intraday data
        await test.test_intraday_data("FOREX:EUR.USD", interval="5m")  # 5-minute
        
        # Test crypto intraday data
        await test.test_intraday_data("CC:BTC.USD", interval="5m")  # 5-minute
        
        # Save results
        test.save_results()
        
        logger.info("EOD Historical Data API test completed")
        
    except Exception as e:
        logger.error(f"Error running EOD Historical Data test: {e}")

if __name__ == "__main__":
    logger.info("Starting EOD Historical Data API test...")
    asyncio.run(run_eodhd_test())


