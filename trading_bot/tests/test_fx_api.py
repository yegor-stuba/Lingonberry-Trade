"""
Test for FX API
Tests various endpoints for forex data
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

class FXAPITest:
    """Test class for FX API"""
    
    def __init__(self):
        """Initialize the test"""
        self.api_key = credentials.FX_API_KEY
        if not self.api_key:
            logger.error("FX API key not found in credentials.py")
            raise ValueError("API key is required")
        
        self.base_url = "https://api.fastforex.io"
        self.results_dir = Path("test_results/fx_api")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        
        self.results = {}
    
    async def test_fetch_all(self):
        """
        Test fetch-all endpoint for all currency rates
        """
        try:
            endpoint = "fetch-all"
            url = f"{self.base_url}/{endpoint}?api_key={self.api_key}"
            
            logger.info(f"Testing fetch-all endpoint...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "results" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    results = data["results"]
                    base = data.get("base", "USD")
                    updated = data.get("updated", "")
                    
                    logger.info(f"Received rates for {len(results)} currencies with base {base}")
                    
                    # Save to results
                    key = f"fetch_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    self.results[key] = {
                        "base": base,
                        "updated": updated,
                        "endpoint": endpoint,
                        "currencies_count": len(results),
                        "sample_rates": dict(list(results.items())[:5])  # Save first 5 rates as sample
                    }
                    
                    # Save to CSV
                    df = pd.DataFrame([{"currency": k, "rate": v} for k, v in results.items()])
                    csv_path = self.results_dir / f"fetch_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df.to_csv(csv_path, index=False)
                    logger.info(f"Saved all rates to {csv_path}")
                    
                    return results
        
        except Exception as e:
            logger.error(f"Error testing fetch-all: {e}")
            return None
    
    async def test_fetch_multi(self, from_currency, to_currencies):
        """
        Test fetch-multi endpoint for multiple currency rates
        
        Args:
            from_currency (str): Base currency (e.g., 'USD')
            to_currencies (list): List of target currencies (e.g., ['EUR', 'GBP', 'JPY'])
        """
        try:
            endpoint = "fetch-multi"
            currencies_str = ",".join(to_currencies)
            url = f"{self.base_url}/{endpoint}?from={from_currency}&to={currencies_str}&api_key={self.api_key}"
            
            logger.info(f"Testing fetch-multi endpoint for {from_currency} to {currencies_str}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "results" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    results = data["results"]
                    base = data.get("base", from_currency)
                    updated = data.get("updated", "")
                    
                    logger.info(f"Received rates for {len(results)} currencies with base {base}")
                    
                    # Save to results
                    key = f"fetch_multi_{from_currency}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    self.results[key] = {
                        "base": base,
                        "updated": updated,
                        "endpoint": endpoint,
                        "currencies": to_currencies,
                        "rates": results
                    }
                    
                    # Save to CSV
                    df = pd.DataFrame([{"currency": k, "rate": v} for k, v in results.items()])
                    csv_path = self.results_dir / f"fetch_multi_{from_currency}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df.to_csv(csv_path, index=False)
                    logger.info(f"Saved multi rates to {csv_path}")
                    
                    return results
        
        except Exception as e:
            logger.error(f"Error testing fetch-multi: {e}")
            return None
    
    async def test_fetch_one(self, from_currency, to_currency):
        """
        Test fetch-one endpoint for a single currency rate
        
        Args:
            from_currency (str): Base currency (e.g., 'USD')
            to_currency (str): Target currency (e.g., 'EUR')
        """
        try:
            endpoint = "fetch-one"
            url = f"{self.base_url}/{endpoint}?from={from_currency}&to={to_currency}&api_key={self.api_key}"
            
            logger.info(f"Testing fetch-one endpoint for {from_currency} to {to_currency}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "result" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    result = data["result"]
                    base = data.get("base", from_currency)
                    updated = data.get("updated", "")
                    
                    rate = result.get(to_currency)
                    logger.info(f"Received rate for {from_currency} to {to_currency}: {rate}")
                    
                    # Save to results
                    key = f"fetch_one_{from_currency}_{to_currency}"
                    self.results[key] = {
                        "base": base,
                        "target": to_currency,
                        "rate": rate,
                        "updated": updated,
                        "endpoint": endpoint
                    }
                    
                    return result
        
        except Exception as e:
            logger.error(f"Error testing fetch-one: {e}")
            return None
    
    async def test_convert(self, from_currency, to_currency, amount):
        """
        Test convert endpoint for currency conversion
        
        Args:
            from_currency (str): Source currency (e.g., 'USD')
            to_currency (str): Target currency (e.g., 'EUR')
            amount (float): Amount to convert
        """
        try:
            endpoint = "convert"
            url = f"{self.base_url}/{endpoint}?from={from_currency}&to={to_currency}&amount={amount}&api_key={self.api_key}"
            
            logger.info(f"Testing convert endpoint for {amount} {from_currency} to {to_currency}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "result" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    result = data["result"]
                    base = data.get("base", from_currency)
                    updated = data.get("updated", "")
                    
                    converted_amount = result.get(to_currency)
                    logger.info(f"Converted {amount} {from_currency} to {converted_amount} {to_currency}")
                    
                    # Save to results
                    key = f"convert_{from_currency}_{to_currency}_{amount}"
                    self.results[key] = {
                        "base": base,
                        "target": to_currency,
                        "amount": amount,
                        "result": converted_amount,
                        "updated": updated,
                        "endpoint": endpoint
                    }
                    
                    return result
        
        except Exception as e:
            logger.error(f"Error testing convert: {e}")
            return None
    
    async def test_historical(self, date, from_currency, to_currencies=None):
        """
        Test historical endpoint for historical rates
        
        Args:
            date (str): Date in YYYY-MM-DD format
            from_currency (str): Base currency (e.g., 'USD')
            to_currencies (list, optional): List of target currencies
        """
        try:
            endpoint = "historical"
            url = f"{self.base_url}/{endpoint}?date={date}&from={from_currency}&api_key={self.api_key}"
            
            if to_currencies:
                currencies_str = ",".join(to_currencies)
                url += f"&to={currencies_str}"
            
            logger.info(f"Testing historical endpoint for {from_currency} on {date}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "results" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    results = data["results"]
                    base = data.get("base", from_currency)
                    
                    logger.info(f"Received historical rates for {len(results)} currencies with base {base} on {date}")
                    
                    # Save to results
                    key = f"historical_{from_currency}_{date}"
                    self.results[key] = {
                        "base": base,
                        "date": date,
                        "endpoint": endpoint,
                        "currencies_count": len(results),
                        "sample_rates": dict(list(results.items())[:5])  # Save first 5 rates as sample
                    }
                    
                    # Save to CSV
                    df = pd.DataFrame([{"currency": k, "rate": v} for k, v in results.items()])
                    csv_path = self.results_dir / f"historical_{from_currency}_{date}.csv"
                    df.to_csv(csv_path, index=False)
                    logger.info(f"Saved historical rates to {csv_path}")
                    
                    return results
        
        except Exception as e:
            logger.error(f"Error testing historical: {e}")
            return None
    
    async def test_time_series(self, start_date, end_date, from_currency, to_currency):
        """
        Test time-series endpoint for historical rates over a period
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            from_currency (str): Base currency (e.g., 'USD')
            to_currency (str): Target currency (e.g., 'EUR')
        """
        try:
            endpoint = "time-series"
            url = f"{self.base_url}/{endpoint}?start={start_date}&end={end_date}&from={from_currency}&to={to_currency}&api_key={self.api_key}"
            
            logger.info(f"Testing time-series endpoint for {from_currency} to {to_currency} from {start_date} to {end_date}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "results" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    results = data["results"]
                    base = data.get("base", from_currency)
                    
                    # Count the number of days in the results
                    days_count = len(results)
                    logger.info(f"Received time-series data for {days_count} days")
                    
                    # Convert to DataFrame for easier analysis
                    df_data = []
                    for date, rates in results.items():
                        df_data.append({
                            "date": date,
                            "rate": rates.get(to_currency)
                        })
                    
                    df = pd.DataFrame(df_data)
                    df["date"] = pd.to_datetime(df["date"])
                    df.sort_values("date", inplace=True)
                    
                    # Save to results
                    key = f"time_series_{from_currency}_{to_currency}_{start_date}_{end_date}"
                    self.results[key] = {
                        "base": base,
                        "target": to_currency,
                        "start_date": start_date,
                        "end_date": end_date,
                        "days_count": days_count,
                        "endpoint": endpoint
                    }
                    
                    # Save to CSV
                    csv_path = self.results_dir / f"time_series_{from_currency}_{to_currency}_{start_date}_{end_date}.csv"
                    df.to_csv(csv_path, index=False)
                    logger.info(f"Saved time-series data to {csv_path}")
                    
                    return df
        
        except Exception as e:
            logger.error(f"Error testing time-series: {e}")
            return None
    
    async def test_currencies(self):
        """
        Test currencies endpoint to get a list of supported currencies
        """
        try:
            endpoint = "currencies"
            url = f"{self.base_url}/{endpoint}?api_key={self.api_key}"
            
            logger.info(f"Testing currencies endpoint...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if "currencies" not in data:
                        logger.error(f"Error in response: {data}")
                        return None
                    
                    currencies = data["currencies"]
                    
                    logger.info(f"Received {len(currencies)} supported currencies")
                    
                    # Save to results
                    key = "currencies"
                    self.results[key] = {
                        "endpoint": endpoint,
                        "currencies_count": len(currencies),
                        "sample_currencies": dict(list(currencies.items())[:10])  # Save first 10 currencies as sample
                    }
                    
                    # Save to CSV
                    df = pd.DataFrame([{"code": k, "name": v} for k, v in currencies.items()])
                    csv_path = self.results_dir / "currencies.csv"
                    df.to_csv(csv_path, index=False)
                    logger.info(f"Saved currencies to {csv_path}")
                    
                    return currencies
        
        except Exception as e:
            logger.error(f"Error testing currencies: {e}")
            return None
    
    def save_results(self):
        """Save test results to file"""
        try:
            results_path = self.results_dir / f"fx_api_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
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
                "# FX API Test Report",
                f"Generated on: {datetime.now().isoformat()}",
                "",
                "## API Key Status",
                f"API Key: {'Valid' if self.api_key else 'Missing'}",
                "",
                "## Fetch All Rates",
                "",
                "| Base | Currencies | Updated |",
                "| ---- | ---------- | ------- |"
            ]
            
            # Add fetch-all results to report
            for key, result in self.results.items():
                if key.startswith("fetch_all_"):
                    report.append(
                        f"| {result.get('base', 'N/A')} | "
                        f"{result.get('currencies_count', 'N/A')} | "
                        f"{result.get('updated', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Fetch Multiple Rates",
                "",
                "| Base | Targets | Updated |",
                "| ---- | ------- | ------- |"
            ])
            
            # Add fetch-multi results to report
            for key, result in self.results.items():
                if key.startswith("fetch_multi_"):
                    report.append(
                        f"| {result.get('base', 'N/A')} | "
                        f"{', '.join(result.get('currencies', []))[:30]}... | "
                        f"{result.get('updated', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Fetch Single Rate",
                "",
                "| From | To | Rate | Updated |",
                "| ---- | -- | ---- | ------- |"
            ])
            
            # Add fetch-one results to report
            for key, result in self.results.items():
                if key.startswith("fetch_one_"):
                    report.append(
                        f"| {result.get('base', 'N/A')} | "
                        f"{result.get('target', 'N/A')} | "
                        f"{result.get('rate', 'N/A')} | "
                        f"{result.get('updated', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Currency Conversion",
                "",
                "| From | To | Amount | Result | Updated |",
                "| ---- | -- | ------ | ------ | ------- |"
            ])
            
            # Add convert results to report
            for key, result in self.results.items():
                if key.startswith("convert_"):
                    report.append(
                        f"| {result.get('base', 'N/A')} | "
                        f"{result.get('target', 'N/A')} | "
                        f"{result.get('amount', 'N/A')} | "
                        f"{result.get('result', 'N/A')} | "
                        f"{result.get('updated', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Historical Rates",
                "",
                "| Base | Date | Currencies |",
                "| ---- | ---- | ---------- |"
            ])
            
            # Add historical results to report
            for key, result in self.results.items():
                if key.startswith("historical_"):
                    report.append(
                        f"| {result.get('base', 'N/A')} | "
                        f"{result.get('date', 'N/A')} | "
                        f"{result.get('currencies_count', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Time Series Data",
                "",
                "| From | To | Start Date | End Date | Days |",
                "| ---- | -- | ---------- | -------- | ---- |"
            ])
            
            # Add time-series results to report
            for key, result in self.results.items():
                if key.startswith("time_series_"):
                    report.append(
                        f"| {result.get('base', 'N/A')} | "
                        f"{result.get('target', 'N/A')} | "
                        f"{result.get('start_date', 'N/A')} | "
                        f"{result.get('end_date', 'N/A')} | "
                        f"{result.get('days_count', 'N/A')} |"
                    )
            
            report.extend([
                "",
                "## Supported Currencies",
                "",
                "| Count | Sample |",
                "| ----- | ------ |"
            ])
            
            # Add currencies results to report
            if "currencies" in self.results:
                result = self.results["currencies"]
                sample_currencies = list(result.get("sample_currencies", {}).keys())
                report.append(
                    f"| {result.get('currencies_count', 'N/A')} | "
                    f"{', '.join(sample_currencies)[:50]}... |"
                )
            
            # Save report to file
            report_path = self.results_dir / "fx_api_report.md"
            with open(report_path, 'w') as f:
                f.write('\n'.join(report))
            
            logger.info(f"Generated summary report at {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")

async def run_fx_api_test():
    """Run the FX API test"""
    try:
        test = FXAPITest()
        
        # Test fetch-all endpoint
        await test.test_fetch_all()
        
        # Test fetch-multi endpoint
        await test.test_fetch_multi("USD", ["EUR", "GBP", "JPY", "CAD", "AUD"])
        
        # Test fetch-one endpoint
        await test.test_fetch_one("USD", "EUR")
        await test.test_fetch_one("EUR", "USD")
        
        # Test convert endpoint
        await test.test_convert("USD", "EUR", 1000)
        await test.test_convert("EUR", "USD", 1000)
        
        # Test historical endpoint
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        await test.test_historical(yesterday, "USD", ["EUR", "GBP", "JPY"])
        
        # Test time-series endpoint
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        await test.test_time_series(start_date, end_date, "USD", "EUR")
        
        # Test currencies endpoint
        await test.test_currencies()
        
        # Save results
        test.save_results()
        
        logger.info("FX API test completed")
        
    except Exception as e:
        logger.error(f"Error running FX API test: {e}")

if __name__ == "__main__":
    logger.info("Starting FX API test...")
    asyncio.run(run_fx_api_test())
