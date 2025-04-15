"""
Test for TraderMade API
Tests various endpoints for forex, crypto, and other financial data
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

class TraderMadeTest:
    """Test class for TraderMade API"""
    
    def __init__(self):
        """Initialize the test"""
        self.api_key = credentials.TRADE_MADE_API_KEY
        if not self.api_key:
            logger.error("TraderMade API key not found in credentials.py")
            raise ValueError("API key is required")
        
        self.base_url = "https://marketdata.tradermade.com/api/v1"
        self.results_dir = Path("test_results/tradermade")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        
        self.results = {}
    
    async def test_live_rates(self, currency_pairs):
        """
        Test live endpoint for current exchange rates
        
        Args:
            currency_pairs (list): List of currency pairs (e.g., ['EURUSD', 'GBPUSD'])
        """
        try:
            endpoint = "live"
            pairs_str = ",".join(currency_pairs)
            url = f"{self.base_url}/{endpoint}?currency={pairs_str}&api_key={self.api_key}"
            
            logger.info(f"Testing live rates for {pairs_str}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "quotes" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    quotes = data["quotes"]
                    logger.info(f"Received {len(quotes)} quotes")
                    
                    # Save to results
                    key = f"live_rates_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    self.results[key] = {
                        "timestamp": data.get("timestamp", ""),
                        "endpoint": endpoint,
                        "quotes": quotes
                    }
                    
                    # Save to CSV
                    df = pd.DataFrame(quotes)
                    csv_path = self.results_dir / f"live_rates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df.to_csv(csv_path, index=False)
                    logger.info(f"Saved live rates to {csv_path}")
                    
                    return quotes
        
        except Exception as e:
            logger.error(f"Error testing live rates: {e}")
            return None
    
    async def test_historical_data(self, currency_pair, date):
        """
        Test historical endpoint for daily OHLC data
        
        Args:
            currency_pair (str): Currency pair (e.g., 'EURUSD')
            date (str): Date in YYYY-MM-DD format
        """
        try:
            endpoint = "historical"
            url = f"{self.base_url}/{endpoint}?currency={currency_pair}&date={date}&api_key={self.api_key}"
            
            logger.info(f"Testing historical data for {currency_pair} on {date}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "quotes" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    quotes = data["quotes"]
                    logger.info(f"Received historical data for {len(quotes)} pairs")
                    
                    # Save to results
                    key = f"historical_{currency_pair}_{date}"
                    self.results[key] = {
                        "date": date,
                        "endpoint": endpoint,
                        "quotes": quotes
                    }
                    
                    # Save to CSV
                    df = pd.DataFrame(quotes)
                    csv_path = self.results_dir / f"historical_{currency_pair}_{date}.csv"
                    df.to_csv(csv_path, index=False)
                    logger.info(f"Saved historical data to {csv_path}")
                    
                    return quotes
        
        except Exception as e:
            logger.error(f"Error testing historical data: {e}")
            return None
    
    async def test_timeseries_data(self, currency_pair, start_date, end_date, interval="daily"):
        """
        Test timeseries endpoint for OHLC data over a period
        
        Args:
            currency_pair (str): Currency pair (e.g., 'EURUSD')
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            interval (str): Data interval ('daily', 'hourly', 'minute')
        """
        try:
            endpoint = "timeseries"
            url = f"{self.base_url}/{endpoint}?currency={currency_pair}&start_date={start_date}&end_date={end_date}&interval={interval}&api_key={self.api_key}"
            
            logger.info(f"Testing timeseries data for {currency_pair} from {start_date} to {end_date} ({interval})...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "quotes" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    quotes = data["quotes"]
                    logger.info(f"Received {len(quotes)} timeseries data points")
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(quotes)
                    
                    # Convert date to datetime
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)
                    
                    # Save to results
                    key = f"timeseries_{currency_pair}_{interval}_{start_date}_{end_date}"
                    self.results[key] = {
                        "currency_pair": currency_pair,
                        "start_date": start_date,
                        "end_date": end_date,
                        "interval": interval,
                        "endpoint": endpoint,
                        "data_points": len(quotes)
                    }
                    
                    # Save to CSV
                    csv_path = self.results_dir / f"timeseries_{currency_pair}_{interval}_{start_date}_{end_date}.csv"
                    df.to_csv(csv_path)
                    logger.info(f"Saved timeseries data to {csv_path}")
                    
                    return df
        
        except Exception as e:
            logger.error(f"Error testing timeseries data: {e}")
            return None
    
    async def test_minute_historical(self, currency_pair, date_time):
        """
        Test minute_historical endpoint for specific minute data
        
        Args:
            currency_pair (str): Currency pair (e.g., 'EURUSD')
            date_time (str): Date and time in YYYY-MM-DD-HH:MM format
        """
        try:
            endpoint = "minute_historical"
            url = f"{self.base_url}/{endpoint}?currency={currency_pair}&date_time={date_time}&api_key={self.api_key}"
            
            logger.info(f"Testing minute historical data for {currency_pair} at {date_time}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "quotes" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    quotes = data["quotes"]
                    logger.info(f"Received minute historical data for {len(quotes)} pairs")
                    
                    # Save to results
                    key = f"minute_historical_{currency_pair}_{date_time}"
                    self.results[key] = {
                        "date_time": date_time,
                        "endpoint": endpoint,
                        "quotes": quotes
                    }
                    
                    # Save to CSV
                    df = pd.DataFrame(quotes)
                    csv_path = self.results_dir / f"minute_historical_{currency_pair}_{date_time.replace(':', '')}.csv"
                    df.to_csv(csv_path, index=False)
                    logger.info(f"Saved minute historical data to {csv_path}")
                    
                    return quotes
        
        except Exception as e:
            logger.error(f"Error testing minute historical data: {e}")
            return None
    
    async def test_currency_conversion(self, from_currency, to_currency, amount):
        """
        Test convert endpoint for currency conversion
        
        Args:
            from_currency (str): Source currency (e.g., 'EUR')
            to_currency (str): Target currency (e.g., 'USD')
            amount (float): Amount to convert
        """
        try:
            endpoint = "convert"
            url = f"{self.base_url}/{endpoint}?from={from_currency}&to={to_currency}&amount={amount}&api_key={self.api_key}"
            
            logger.info(f"Testing currency conversion from {from_currency} to {to_currency} for amount {amount}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "total" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    logger.info(f"Conversion result: {data['total']} {to_currency}")
                    
                    # Save to results
                    key = f"convert_{from_currency}_{to_currency}_{amount}"
                    self.results[key] = {
                        "from": from_currency,
                        "to": to_currency,
                        "amount": amount,
                        "result": data.get("total", 0),
                        "rate": data.get("rate", 0),
                        "timestamp": data.get("timestamp", ""),
                        "endpoint": endpoint
                    }
                    
                    return data
        
        except Exception as e:
            logger.error(f"Error testing currency conversion: {e}")
            return None
    
    def save_results(self):
        """Save test results to file"""
        try:
            results_path = self.results_dir / f"tradermade_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
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
                "# TraderMade API Test Report",
                f"Generated on: {datetime.now().isoformat()}",
                "",
                "## API Key Status",
                f"API Key: {'Valid' if self.api_key else 'Missing'}",
                "",
                "## Live Exchange Rates",
                "",
                "| Timestamp | Currency Pairs | Status |",
                "| --------- | -------------- | ------ |"
            ]
            
            # Add live rates to report
            for key, result in self.results.items():
                if key.startswith("live_rates_"):
                    pairs_count = len(result.get("quotes", []))
                    report.append(
                        f"| {result.get('timestamp', 'N/A')} | {pairs_count} pairs | Success |"
                    )
            
            report.extend([
                "",
                "## Historical Data",
                "",
                "| Currency Pair | Date | Status |",
                "| ------------- | ---- | ------ |"
            ])
            
            # Add historical data to report
            for key, result in self.results.items():
                if key.startswith("historical_"):
                    parts = key.split("_")
                    if len(parts) >= 3:
                        currency_pair = parts[1]
                        date = parts[2]
                        report.append(
                            f"| {currency_pair} | {date} | Success |"
                        )
            
            report.extend([
                "",
                "## Timeseries Data",
                "",
                "| Currency Pair | Interval | Start Date | End Date | Data Points |",
                "| ------------- | -------- | ---------- | -------- | ----------- |"
            ])
            
            # Add timeseries data to report
            for key, result in self.results.items():
                if key.startswith("timeseries_"):
                    report.append(
                        f"| {result.get('currency_pair', 'N/A')} | "
                        f"{result.get('interval', 'N/A')} | "
                        f"{result.get('start_date', 'N/A')} | "
                        f"{result.get('end_date', 'N/A')} | "
                        f"{result.get('data_points', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Minute Historical Data",
                "",
                "| Currency Pair | Date Time | Status |",
                "| ------------- | --------- | ------ |"
            ])
            
            # Add minute historical data to report
            for key, result in self.results.items():
                if key.startswith("minute_historical_"):
                    parts = key.split("_")
                    if len(parts) >= 3:
                        currency_pair = parts[2]
                        date_time = parts[3]
                        report.append(
                            f"| {currency_pair} | {date_time} | Success |"
                        )
            
            report.extend([
                "",
                "## Currency Conversion",
                "",
                "| From | To | Amount | Result | Rate |",
                "| ---- | -- | ------ | ------ | ---- |"
            ])
            
            # Add currency conversion to report
            for key, result in self.results.items():
                if key.startswith("convert_"):
                    report.append(
                        f"| {result.get('from', 'N/A')} | "
                        f"{result.get('to', 'N/A')} | "
                        f"{result.get('amount', 'N/A')} | "
                        f"{result.get('result', 'N/A')} | "
                        f"{result.get('rate', 'N/A')} |"
                    )
            
            # Save report to file
            report_path = self.results_dir / "tradermade_report.md"
            with open(report_path, 'w') as f:
                f.write('\n'.join(report))
            
            logger.info(f"Generated summary report at {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")

async def run_tradermade_test():
    """Run the TraderMade API test"""
    try:
        test = TraderMadeTest()
        
        # Test live rates
        await test.test_live_rates(["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"])
        
        # Test historical data
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        await test.test_historical_data("EURUSD", yesterday)
        
        # Test timeseries data
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        await test.test_timeseries_data("EURUSD", start_date, end_date, "daily")
        
        # Test minute historical data
        # Format: YYYY-MM-DD-HH:MM
        minute_time = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d-12:00")
        await test.test_minute_historical("EURUSD", minute_time)
        
        # Test currency conversion
        await test.test_currency_conversion("EUR", "USD", 1000)
        
        # Save results
        test.save_results()
        
        logger.info("TraderMade API test completed")
        
    except Exception as e:
        logger.error(f"Error running TraderMade test: {e}")

if __name__ == "__main__":
    logger.info("Starting TraderMade API test...")
    asyncio.run(run_tradermade_test())

