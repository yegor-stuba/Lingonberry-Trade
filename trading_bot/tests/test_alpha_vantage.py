"""
Test for Alpha Vantage API
Tests various endpoints for forex and stock data
"""

import logging
import asyncio
import aiohttp
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

from trading_bot.config import credentials

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlphaVantageTest:
    """Test class for Alpha Vantage API"""
    
    def __init__(self):
        """Initialize the test"""
        self.api_key = credentials.ALPHA_VANTAGE_API_KEY
        if not self.api_key:
            logger.error("Alpha Vantage API key not found in credentials.py")
            raise ValueError("API key is required")
        
        self.base_url = "https://www.alphavantage.co/query"
        self.results_dir = Path("test_results/alpha_vantage")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        
        self.results = {}
    
    async def test_forex_exchange_rate(self, from_currency, to_currency):
        """
        Test CURRENCY_EXCHANGE_RATE endpoint
        Gets the current exchange rate for a forex pair
        """
        try:
            endpoint = "CURRENCY_EXCHANGE_RATE"
            url = f"{self.base_url}?function={endpoint}&from_currency={from_currency}&to_currency={to_currency}&apikey={self.api_key}"
            
            logger.info(f"Testing CURRENCY_EXCHANGE_RATE for {from_currency}/{to_currency}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "Realtime Currency Exchange Rate" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    exchange_rate = data["Realtime Currency Exchange Rate"]
                    result = {
                        "from_currency": exchange_rate["1. From_Currency Code"],
                        "to_currency": exchange_rate["3. To_Currency Code"],
                        "exchange_rate": float(exchange_rate["5. Exchange Rate"]),
                        "last_refreshed": exchange_rate["6. Last Refreshed"],
                        "timezone": exchange_rate["7. Time Zone"],
                        "endpoint": endpoint
                    }
                    
                    logger.info(f"Exchange rate: {result['exchange_rate']}")
                    
                    # Save to results
                    key = f"forex_rate_{from_currency}_{to_currency}"
                    self.results[key] = result
                    
                    return result
        
        except Exception as e:
            logger.error(f"Error testing forex exchange rate: {e}")
            return None
    
    async def test_forex_intraday(self, from_currency, to_currency, interval="60min"):
        """
        Test FX_INTRADAY endpoint
        Gets intraday time series data for a forex pair
        """
        try:
            endpoint = "FX_INTRADAY"
            url = f"{self.base_url}?function={endpoint}&from_symbol={from_currency}&to_symbol={to_currency}&interval={interval}&outputsize=compact&apikey={self.api_key}"
            
            logger.info(f"Testing FX_INTRADAY for {from_currency}/{to_currency} at {interval}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    # Check for error messages
                    if "Error Message" in data:
                        logger.error(f"API error: {data['Error Message']}")
                        return None
                    
                    # Extract metadata
                    metadata = data.get("Meta Data", {})
                    
                    # Extract time series data
                    time_series_key = f"Time Series FX ({interval})"
                    
                    if time_series_key not in data:
                        logger.error(f"Time series data not found in response")
                        return None
                    
                    time_series = data[time_series_key]
                    
                    # Convert to DataFrame
                    df = pd.DataFrame.from_dict(time_series, orient='index')
                    
                    # Rename columns
                    df.columns = [col.split('. ')[1] for col in df.columns]
                    
                    # Convert to numeric
                    for col in df.columns:
                        df[col] = pd.to_numeric(df[col])
                    
                    # Convert index to datetime
                    df.index = pd.to_datetime(df.index)
                    df.index.name = 'timestamp'
                    
                    # Sort by datetime
                    df.sort_index(inplace=True)
                    
                    logger.info(f"Retrieved {len(df)} candles")
                    
                    # Save sample to CSV
                    csv_path = self.results_dir / f"forex_intraday_{from_currency}{to_currency}_{interval}.csv"
                    df.to_csv(csv_path)
                    logger.info(f"Saved sample data to {csv_path}")
                    
                    # Save to results
                    key = f"forex_intraday_{from_currency}_{to_currency}_{interval}"
                    self.results[key] = {
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "interval": interval,
                        "candle_count": len(df),
                        "start_date": df.index[0].isoformat() if not df.empty else None,
                        "end_date": df.index[-1].isoformat() if not df.empty else None,
                        "endpoint": endpoint,
                        "sample_path": str(csv_path)
                    }
                    
                    return df
        
        except Exception as e:
            logger.error(f"Error testing forex intraday: {e}")
            return None
    
    async def test_forex_daily(self, from_currency, to_currency):
        """
        Test FX_DAILY endpoint
        Gets daily time series data for a forex pair
        """
        try:
            endpoint = "FX_DAILY"
            url = f"{self.base_url}?function={endpoint}&from_symbol={from_currency}&to_symbol={to_currency}&outputsize=compact&apikey={self.api_key}"
            
            logger.info(f"Testing FX_DAILY for {from_currency}/{to_currency}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    # Check for error messages
                    if "Error Message" in data:
                        logger.error(f"API error: {data['Error Message']}")
                        return None
                    
                    # Extract metadata
                    metadata = data.get("Meta Data", {})
                    
                    # Extract time series data
                    time_series_key = "Time Series FX (Daily)"
                    
                    if time_series_key not in data:
                        logger.error(f"Time series data not found in response")
                        return None
                    
                    time_series = data[time_series_key]
                    
                    # Convert to DataFrame
                    df = pd.DataFrame.from_dict(time_series, orient='index')
                    
                    # Rename columns
                    df.columns = [col.split('. ')[1] for col in df.columns]
                    
                    # Convert to numeric
                    for col in df.columns:
                        df[col] = pd.to_numeric(df[col])
                    
                    # Convert index to datetime
                    df.index = pd.to_datetime(df.index)
                    df.index.name = 'timestamp'
                    
                    # Sort by datetime
                    df.sort_index(inplace=True)
                    
                    logger.info(f"Retrieved {len(df)} daily candles")
                    
                    # Save sample to CSV
                    csv_path = self.results_dir / f"forex_daily_{from_currency}{to_currency}.csv"
                    df.to_csv(csv_path)
                    logger.info(f"Saved sample data to {csv_path}")
                    
                    # Save to results
                    key = f"forex_daily_{from_currency}_{to_currency}"
                    self.results[key] = {
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "candle_count": len(df),
                        "start_date": df.index[0].isoformat() if not df.empty else None,
                        "end_date": df.index[-1].isoformat() if not df.empty else None,
                        "endpoint": endpoint,
                        "sample_path": str(csv_path)
                    }
                    
                    return df
        
        except Exception as e:
            logger.error(f"Error testing forex daily: {e}")
            return None
    
    async def test_stock_quote(self, symbol):
        """
        Test GLOBAL_QUOTE endpoint
        Gets the latest price and volume information for a stock
        """
        try:
            endpoint = "GLOBAL_QUOTE"
            url = f"{self.base_url}?function={endpoint}&symbol={symbol}&apikey={self.api_key}"
            
            logger.info(f"Testing GLOBAL_QUOTE for {symbol}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "Global Quote" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    quote = data["Global Quote"]
                    result = {
                        "symbol": quote["01. symbol"],
                        "price": float(quote["05. price"]),
                        "change": float(quote["09. change"]),
                        "change_percent": quote["10. change percent"],
                        "volume": int(quote["06. volume"]),
                        "latest_trading_day": quote["07. latest trading day"],
                        "endpoint": endpoint
                    }
                    
                    logger.info(f"Stock price: {result['price']}")
                    
                    # Save to results
                    key = f"stock_quote_{symbol}"
                    self.results[key] = result
                    
                    return result
        
        except Exception as e:
            logger.error(f"Error testing stock quote: {e}")
            return None
    
    async def test_stock_intraday(self, symbol, interval="60min"):
        """
        Test TIME_SERIES_INTRADAY endpoint
        Gets intraday time series data for a stock
        """
        try:
            endpoint = "TIME_SERIES_INTRADAY"
            url = f"{self.base_url}?function={endpoint}&symbol={symbol}&interval={interval}&outputsize=compact&apikey={self.api_key}"
            
            logger.info(f"Testing TIME_SERIES_INTRADAY for {symbol} at {interval}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    # Check for error messages
                    if "Error Message" in data:
                        logger.error(f"API error: {data['Error Message']}")
                        return None
                    
                    # Extract metadata
                    metadata = data.get("Meta Data", {})
                    
                    # Extract time series data
                    time_series_key = f"Time Series ({interval})"
                    
                    if time_series_key not in data:
                        logger.error(f"Time series data not found in response")
                        return None
                    
                    time_series = data[time_series_key]
                    
                    # Convert to DataFrame
                    df = pd.DataFrame.from_dict(time_series, orient='index')
                    
                    # Rename columns
                    df.columns = [col.split('. ')[1] for col in df.columns]
                    
                    # Convert to numeric
                    for col in df.columns:
                        df[col] = pd.to_numeric(df[col])
                    
                    # Convert index to datetime
                    df.index = pd.to_datetime(df.index)
                    df.index.name = 'timestamp'
                    
                    # Sort by datetime
                    df.sort_index(inplace=True)
                    
                    logger.info(f"Retrieved {len(df)} candles")
                    
                    # Save sample to CSV
                    csv_path = self.results_dir / f"stock_intraday_{symbol}_{interval}.csv"
                    df.to_csv(csv_path)
                    logger.info(f"Saved sample data to {csv_path}")
                    
                    # Save to results
                    key = f"stock_intraday_{symbol}_{interval}"
                    self.results[key] = {
                        "symbol": symbol,
                        "interval": interval,
                        "candle_count": len(df),
                        "start_date": df.index[0].isoformat() if not df.empty else None,
                        "end_date": df.index[-1].isoformat() if not df.empty else None,
                        "endpoint": endpoint,
                        "sample_path": str(csv_path)
                    }
                    
                    return df
        
        except Exception as e:
            logger.error(f"Error testing stock intraday: {e}")
            return None
    
    def save_results(self):
        """Save test results to file"""
        try:
            results_path = self.results_dir / f"alpha_vantage_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
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
                "# Alpha Vantage API Test Report",
                f"Generated on: {datetime.now().isoformat()}",
                "",
                "## API Key Status",
                f"API Key: {'Valid' if self.api_key else 'Missing'}",
                "",
                "## Forex Exchange Rates",
                "",
                "| From | To | Rate | Last Updated |",
                "| ---- | -- | ---- | ------------ |"
            ]
            
            # Add forex exchange rates to report
            for key, result in self.results.items():
                if key.startswith("forex_rate_"):
                    report.append(
                        f"| {result.get('from_currency', 'N/A')} | "
                        f"{result.get('to_currency', 'N/A')} | "
                        f"{result.get('exchange_rate', 'N/A')} | "
                        f"{result.get('last_refreshed', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Forex Time Series Data",
                "",
                "| Pair | Type | Interval | Candles | Start Date | End Date |",
                "| ---- | ---- | -------- | ------- | ---------- | -------- |"
            ])
            
            # Add forex time series data to report
            for key, result in self.results.items():
                if key.startswith("forex_intraday_") or key.startswith("forex_daily_"):
                    data_type = "Intraday" if "intraday" in key else "Daily"
                    interval = result.get('interval', 'N/A') if data_type == "Intraday" else "Daily"
                    
                    report.append(
                        f"| {result.get('from_currency', 'N/A')}{result.get('to_currency', 'N/A')} | "
                        f"{data_type} | {interval} | {result.get('candle_count', 'N/A')} | "
                        f"{result.get('start_date', 'N/A')} | {result.get('end_date', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Stock Data",
                "",
                "| Symbol | Type | Price/Candles | Change | Volume |",
                "| ------ | ---- | ------------- | ------ | ------ |"
            ])
            
            # Add stock data to report
            for key, result in self.results.items():
                if key.startswith("stock_quote_"):
                    report.append(
                        f"| {result.get('symbol', 'N/A')} | Quote | "
                        f"{result.get('price', 'N/A')} | {result.get('change_percent', 'N/A')} | "
                        f"{result.get('volume', 'N/A')} |"
                    )
                elif key.startswith("stock_intraday_"):
                    report.append(
                        f"| {result.get('symbol', 'N/A')} | Intraday ({result.get('interval', 'N/A')}) | "
                        f"{result.get('candle_count', 'N/A')} candles | N/A | N/A |"
                    )
            
            # Save report to file
            report_path = self.results_dir / "alpha_vantage_report.md"
            with open(report_path, 'w') as f:
                f.write('\n'.join(report))
            
            logger.info(f"Generated summary report at {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")

async def run_alpha_vantage_test():
    """Run the Alpha Vantage API test"""
    try:
        test = AlphaVantageTest()
        
        # Test forex exchange rates
        await test.test_forex_exchange_rate("EUR", "USD")
        await test.test_forex_exchange_rate("GBP", "USD")
        await test.test_forex_exchange_rate("USD", "JPY")
        
        # Test forex intraday data
        await test.test_forex_intraday("EUR", "USD", "15min")
        await test.test_forex_intraday("EUR", "USD", "60min")
        
        # Test forex daily data
        await test.test_forex_daily("EUR", "USD")
        
        # Test stock quotes
        await test.test_stock_quote("AAPL")
        await test.test_stock_quote("MSFT")
        
        # Test stock intraday data
        await test.test_stock_intraday("AAPL", "15min")
        
        # Save results
        test.save_results()
        
        logger.info("Alpha Vantage API test completed")
        
    except Exception as e:
        logger.error(f"Error running Alpha Vantage test: {e}")

if __name__ == "__main__":
    logger.info("Starting Alpha Vantage API test...")
    asyncio.run(run_alpha_vantage_test())
