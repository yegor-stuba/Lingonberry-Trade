"""
Comprehensive test for all data providers
Tests and compares all available data sources
"""

import logging
import asyncio
import aiohttp
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path
import os
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_bot.config import credentials
from trading_bot.data.forex_data import ForexDataProvider
from trading_bot.bridges.mt5.client import MT5BridgeClient

# Import test modules
from test_alpha_vantage import AlphaVantageTest
from test_eodhd_api import EODHDTest
from test_tradermade_api import TraderMadeTest
from test_fx_api import FXAPITest

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataProviderComparison:
    """Class to compare different data providers"""
    
    def __init__(self):
        """Initialize the comparison test"""
        self.results_dir = Path("test_results/comparison")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        
        self.results = {
            "providers": {},
            "comparisons": {},
            "recommendations": {}
        }
        
        # Initialize data providers
        self.forex_provider = ForexDataProvider()
        
        # Initialize test classes
        try:
            self.alpha_vantage_test = AlphaVantageTest()
            self.results["providers"]["alpha_vantage"] = {"status": "initialized"}
        except Exception as e:
            logger.error(f"Error initializing Alpha Vantage test: {e}")
            self.alpha_vantage_test = None
            self.results["providers"]["alpha_vantage"] = {"status": "error", "error": str(e)}
        
        try:
            self.eodhd_test = EODHDTest()
            self.results["providers"]["eodhd"] = {"status": "initialized"}
        except Exception as e:
            logger.error(f"Error initializing EODHD test: {e}")
            self.eodhd_test = None
            self.results["providers"]["eodhd"] = {"status": "error", "error": str(e)}
        
        try:
            self.tradermade_test = TraderMadeTest()
            self.results["providers"]["tradermade"] = {"status": "initialized"}
        except Exception as e:
            logger.error(f"Error initializing TraderMade test: {e}")
            self.tradermade_test = None
            self.results["providers"]["tradermade"] = {"status": "error", "error": str(e)}
        
        try:
            self.fx_api_test = FXAPITest()
            self.results["providers"]["fx_api"] = {"status": "initialized"}
        except Exception as e:
            logger.error(f"Error initializing FX API test: {e}")
            self.fx_api_test = None
            self.results["providers"]["fx_api"] = {"status": "error", "error": str(e)}
        
        # Check MT5 bridge
        try:
            self.mt5_client = MT5BridgeClient()
            self.mt5_connected = self.mt5_client.connect()
            self.results["providers"]["mt5_bridge"] = {
                "status": "connected" if self.mt5_connected else "disconnected"
            }
        except Exception as e:
            logger.error(f"Error connecting to MT5 bridge: {e}")
            self.mt5_client = None
            self.mt5_connected = False
            self.results["providers"]["mt5_bridge"] = {"status": "error", "error": str(e)}
        
        # Check CSV data
        try:
            self.csv_data_available = self._check_csv_data()
            self.results["providers"]["csv"] = {
                "status": "available" if self.csv_data_available else "unavailable",
                "details": self.csv_data_available
            }
        except Exception as e:
            logger.error(f"Error checking CSV data: {e}")
            self.csv_data_available = False
            self.results["providers"]["csv"] = {"status": "error", "error": str(e)}
    
    def _check_csv_data(self):
        """Check availability of CSV data"""
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        charts_dir = base_dir / "charts"
        
        if not charts_dir.exists():
            return False
        
        result = {
            "forex": [],
            "crypto": [],
            "indices": [],
            "metals": []
        }
        
        # Check forex data
        forex_dir = charts_dir / "forex"
        if forex_dir.exists():
            forex_files = list(forex_dir.glob("*.csv"))
            forex_pairs = set()
            for file in forex_files:
                # Extract pair name (remove timeframe suffix)
                pair = ''.join([c for c in file.stem if not c.isdigit()])
                forex_pairs.add(pair)
            result["forex"] = list(forex_pairs)
        
        # Check crypto data
        crypto_dir = charts_dir / "crypto"
        if crypto_dir.exists():
            crypto_files = list(crypto_dir.glob("*.csv"))
            crypto_pairs = set()
            for file in crypto_files:
                # Extract pair name (remove timeframe suffix)
                pair = ''.join([c for c in file.stem if not c.isdigit()])
                crypto_pairs.add(pair)
            result["crypto"] = list(crypto_pairs)
        
        # Check indices data
        indices_dir = charts_dir / "indeces"  # Note the spelling in the directory structure
        if indices_dir.exists():
            indices_files = list(indices_dir.glob("*.csv"))
            indices_pairs = set()
            for file in indices_files:
                # Extract pair name (remove timeframe suffix)
                pair = ''.join([c for c in file.stem if not c.isdigit()])
                indices_pairs.add(pair)
            result["indices"] = list(indices_pairs)
        
        # Check metals data
        metals_dir = charts_dir / "metals"
        if metals_dir.exists():
            metals_files = list(metals_dir.glob("*.csv"))
            metals_pairs = set()
            for file in metals_files:
                # Extract pair name (remove timeframe suffix)
                pair = ''.join([c for c in file.stem if not c.isdigit()])
                metals_pairs.add(pair)
            result["metals"] = list(metals_pairs)
        
        return result
    
    async def test_forex_providers(self, pairs=None, timeframes=None):
        """
        Test all forex data providers
        
        Args:
            pairs (list): List of forex pairs to test
            timeframes (list): List of timeframes to test
        """
        if pairs is None:
            pairs = ["EURUSD", "GBPUSD", "USDJPY"]
        
        if timeframes is None:
            timeframes = ["1h", "4h", "1d"]
        
        logger.info(f"Testing forex data providers for pairs {pairs} and timeframes {timeframes}...")
        
        comparison_results = {}
        
        # Test CSV data
        if self.csv_data_available and any(pair in self.csv_data_available.get("forex", []) for pair in pairs):
            logger.info("Testing CSV data for forex...")
            csv_results = {}
            
            for pair in pairs:
                pair_results = {}
                for tf in timeframes:
                    try:
                        df = await self.forex_provider.get_ohlcv(pair, tf, source='csv')
                        if df is not None and not df.empty:
                            pair_results[tf] = {
                                "status": "success",
                                "candles": len(df),
                                "start_date": df.index[0].isoformat(),
                                "end_date": df.index[-1].isoformat()
                            }
                        else:
                            pair_results[tf] = {"status": "no_data"}
                    except Exception as e:
                        logger.error(f"Error getting CSV data for {pair} {tf}: {e}")
                        pair_results[tf] = {"status": "error", "error": str(e)}
                
                csv_results[pair] = pair_results
            
            comparison_results["csv"] = csv_results
        
        # Test MT5 bridge
        if self.mt5_connected:
            logger.info("Testing MT5 bridge for forex...")
            mt5_results = {}
            
            for pair in pairs:
                pair_results = {}
                for tf in timeframes:
                    try:
                        # Map timeframe to MT5 format
                        tf_map = {
                            "1m": "M1",
                            "5m": "M5",
                            "15m": "M15",
                            "30m": "M30",
                            "1h": "H1",
                            "4h": "H4",
                            "1d": "D1",
                            "1w": "W1"
                        }
                        mt5_tf = tf_map.get(tf)
                        
                        if mt5_tf:
                            df = self.mt5_client.get_forex_data(pair, mt5_tf, 100)
                            if df is not None and not df.empty:
                                pair_results[tf] = {
                                    "status": "success",
                                    "candles": len(df),
                                    "start_date": df.index[0].isoformat(),
                                    "end_date": df.index[-1].isoformat()
                                }
                            else:
                                pair_results[tf] = {"status": "no_data"}
                        else:
                            pair_results[tf] = {"status": "unsupported_timeframe"}
                    except Exception as e:
                        logger.error(f"Error getting MT5 data for {pair} {tf}: {e}")
                        pair_results[tf] = {"status": "error", "error": str(e)}
                
                mt5_results[pair] = pair_results
            
            comparison_results["mt5"] = mt5_results
        
        # Test Alpha Vantage
        if self.alpha_vantage_test:
            logger.info("Testing Alpha Vantage for forex...")
            av_results = {}
            
            for pair in pairs:
                pair_results = {}
                
                # Alpha Vantage uses different format for forex pairs
                from_currency = pair[:3]
                to_currency = pair[3:]
                
                # Test daily data
                if "1d" in timeframes:
                    try:
                        df = await self.alpha_vantage_test.test_forex_daily(from_currency, to_currency)
                        if df is not None and not df.empty:
                            pair_results["1d"] = {
                                "status": "success",
                                "candles": len(df),
                                "start_date": df.index[0].isoformat(),
                                "end_date": df.index[-1].isoformat()
                            }
                        else:
                            pair_results["1d"] = {"status": "no_data"}
                    except Exception as e:
                        logger.error(f"Error getting Alpha Vantage daily data for {pair}: {e}")
                        pair_results["1d"] = {"status": "error", "error": str(e)}
                
                # Test intraday data
                for tf in [t for t in timeframes if t != "1d"]:
                    try:
                        # Map timeframe to Alpha Vantage format
                        tf_map = {
                            "1m": "1min",
                            "5m": "5min",
                            "15m": "15min",
                            "30m": "30min",
                            "1h": "60min",
                            "4h": "NONE"  # Not supported
                        }
                        av_tf = tf_map.get(tf)
                        
                        if av_tf and av_tf != "NONE":
                            df = await self.alpha_vantage_test.test_forex_intraday(from_currency, to_currency, av_tf)
                            if df is not None and not df.empty:
                                pair_results[tf] = {
                                    "status": "success",
                                    "candles": len(df),
                                    "start_date": df.index[0].isoformat(),
                                    "end_date": df.index[-1].isoformat()
                                }
                            else:
                                pair_results[tf] = {"status": "no_data"}
                        else:
                            pair_results[tf] = {"status": "unsupported_timeframe"}
                    except Exception as e:
                        logger.error(f"Error getting Alpha Vantage intraday data for {pair} {tf}: {e}")
                        pair_results[tf] = {"status": "error", "error": str(e)}
                
                av_results[pair] = pair_results
            
            comparison_results["alpha_vantage"] = av_results
        
        # Test TraderMade
        if self.tradermade_test:
            logger.info("Testing TraderMade for forex...")
            tm_results = {}
            
            for pair in pairs:
                pair_results = {}
                
                # Test daily data (using timeseries endpoint)
                if "1d" in timeframes:
                    try:
                        end_date = datetime.now().strftime("%Y-%m-%d")
                        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                        df = await self.tradermade_test.test_timeseries_data(pair, start_date, end_date, "daily")
                        if df is not None and not df.empty:
                            pair_results["1d"] = {
                                "status": "success",
                                "candles": len(df),
                                "start_date": df.index[0].isoformat(),
                                "end_date": df.index[-1].isoformat()
                            }
                        else:
                            pair_results["1d"] = {"status": "no_data"}
                    except Exception as e:
                        logger.error(f"Error getting TraderMade daily data for {pair}: {e}")
                        pair_results["1d"] = {"status": "error", "error": str(e)}
                
                # Test hourly data
                if "1h" in timeframes:
                    try:
                        end_date = datetime.now().strftime("%Y-%m-%d")
                        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                        df = await self.tradermade_test.test_timeseries_data(pair, start_date, end_date, "hourly")
                        if df is not None and not df.empty:
                            pair_results["1h"] = {
                                "status": "success",
                                "candles": len(df),
                                "start_date": df.index[0].isoformat(),
                                "end_date": df.index[-1].isoformat()
                            }
                        else:
                            pair_results["1h"] = {"status": "no_data"}
                    except Exception as e:
                        logger.error(f"Error getting TraderMade hourly data for {pair}: {e}")
                        pair_results["1h"] = {"status": "error", "error": str(e)}
                
                # Other timeframes are not directly supported by TraderMade
                for tf in [t for t in timeframes if t not in ["1d", "1h"]]:
                    pair_results[tf] = {"status": "unsupported_timeframe"}
                
                tm_results[pair] = pair_results
            
            comparison_results["tradermade"] = tm_results
        
        # Test FX API
        if self.fx_api_test:
            logger.info("Testing FX API for forex...")
            fx_results = {}
            
            for pair in pairs:
                pair_results = {}
                
                # FX API doesn't provide OHLC data, only current and historical rates
                # We'll test the historical endpoint for daily data
                if "1d" in timeframes:
                    try:
                        # Split pair into from/to currencies
                        from_currency = pair[:3]
                        to_currency = pair[3:]
                        
                        # Get historical data for the last 30 days
                        end_date = datetime.now().strftime("%Y-%m-%d")
                        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                        df = await self.fx_api_test.test_time_series(start_date, end_date, from_currency, to_currency)
                        if df is not None and not df.empty:
                            pair_results["1d"] = {
                                "status": "success",
                                "candles": len(df),
                                "start_date": df["date"].min().isoformat(),
                                "end_date": df["date"].max().isoformat()
                            }
                        else:
                            pair_results["1d"] = {"status": "no_data"}
                    except Exception as e:
                        logger.error(f"Error getting FX API daily data for {pair}: {e}")
                        pair_results["1d"] = {"status": "error", "error": str(e)}
                
                # FX API doesn't support intraday data
                for tf in [t for t in timeframes if t != "1d"]:
                    pair_results[tf] = {"status": "unsupported_timeframe"}
                
                fx_results[pair] = pair_results
            
            comparison_results["fx_api"] = fx_results
        
        # Store comparison results
        self.results["comparisons"]["forex"] = comparison_results
        
        # Generate recommendations
        self._generate_forex_recommendations(comparison_results)
        
        return comparison_results
    
    async def test_crypto_providers(self, pairs=None, timeframes=None):
        """
        Test all crypto data providers
        
        Args:
            pairs (list): List of crypto pairs to test
            timeframes (list): List of timeframes to test
        """
        if pairs is None:
            pairs = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        
        if timeframes is None:
            timeframes = ["1h", "4h", "1d"]
        
        logger.info(f"Testing crypto data providers for pairs {pairs} and timeframes {timeframes}...")
        
        comparison_results = {}
        
        # Test CSV data
        if self.csv_data_available and any(pair in self.csv_data_available.get("crypto", []) for pair in pairs):
            logger.info("Testing CSV data for crypto...")
            csv_results = {}
            
            for pair in pairs:
                pair_results = {}
                for tf in timeframes:
                    try:
                        df = await self.forex_provider.get_ohlcv(pair, tf, source='csv')
                        if df is not None and not df.empty:
                            pair_results[tf] = {
                                "status": "success",
                                "candles": len(df),
                                "start_date": df.index[0].isoformat(),
                                "end_date": df.index[-1].isoformat()
                            }
                        else:
                            pair_results[tf] = {"status": "no_data"}
                    except Exception as e:
                        logger.error(f"Error getting CSV data for {pair} {tf}: {e}")
                        pair_results[tf] = {"status": "error", "error": str(e)}
                
                csv_results[pair] = pair_results
            
            comparison_results["csv"] = csv_results
        
        # Test Alpha Vantage
        if self.alpha_vantage_test:
            logger.info("Testing Alpha Vantage for crypto...")
            av_results = {}
            
            for pair in pairs:
                pair_results = {}
                
                # Alpha Vantage uses different format for crypto pairs
                # Extract symbol and market from pair (e.g., BTCUSDT -> BTC, USD)
                if "USDT" in pair:
                    symbol = pair.replace("USDT", "")
                    market = "USD"  # Alpha Vantage uses USD instead of USDT
                else:
                    # Default assumption for other formats
                    symbol = pair[:3]
                    market = pair[3:]
                
                # Test daily data
                if "1d" in timeframes:
                    try:
                        df = await self.alpha_vantage_test.test_crypto_daily(symbol, market)
                        if df is not None and not df.empty:
                            pair_results["1d"] = {
                                "status": "success",
                                "candles": len(df),
                                "start_date": df.index[0].isoformat(),
                                "end_date": df.index[-1].isoformat()
                            }
                        else:
                            pair_results["1d"] = {"status": "no_data"}
                    except Exception as e:
                        logger.error(f"Error getting Alpha Vantage daily data for {pair}: {e}")
                        pair_results["1d"] = {"status": "error", "error": str(e)}
                
                # Test intraday data
                for tf in [t for t in timeframes if t != "1d"]:
                    try:
                        # Map timeframe to Alpha Vantage format
                        tf_map = {
                            "1m": "1min",
                            "5m": "5min",
                            "15m": "15min",
                            "30m": "30min",
                            "1h": "60min",
                            "4h": "NONE"  # Not supported
                        }
                        av_tf = tf_map.get(tf)
                        
                        if av_tf and av_tf != "NONE":
                            df = await self.alpha_vantage_test.test_crypto_intraday(symbol, market, av_tf)
                            if df is not None and not df.empty:
                                pair_results[tf] = {
                                    "status": "success",
                                    "candles": len(df),
                                    "start_date": df.index[0].isoformat(),
                                    "end_date": df.index[-1].isoformat()
                                }
                            else:
                                pair_results[tf] = {"status": "no_data"}
                        else:
                            pair_results[tf] = {"status": "unsupported_timeframe"}
                    except Exception as e:
                        logger.error(f"Error getting Alpha Vantage intraday data for {pair} {tf}: {e}")
                        pair_results[tf] = {"status": "error", "error": str(e)}
                
                av_results[pair] = pair_results
            
            comparison_results["alpha_vantage"] = av_results
        
        # Store comparison results
        self.results["comparisons"]["crypto"] = comparison_results
        
        # Generate recommendations
        self._generate_crypto_recommendations(comparison_results)
        
        return comparison_results
    
    def _generate_forex_recommendations(self, comparison_results):
        """
        Generate recommendations for forex data providers
        
        Args:
            comparison_results (dict): Results of forex provider comparison
        """
        recommendations = {
            "primary": None,
            "secondary": None,
            "fallback": None,
            "reasoning": []
        }
        
        # Count successful requests for each provider
        success_counts = {}
        timeframe_support = {}
        
        for provider, provider_results in comparison_results.items():
            success_counts[provider] = 0
            timeframe_support[provider] = set()
            
            for pair, pair_results in provider_results.items():
                for tf, tf_result in pair_results.items():
                    if tf_result.get("status") == "success":
                        success_counts[provider] += 1
                        timeframe_support[provider].add(tf)
        
        # Rank providers by success count
        ranked_providers = sorted(success_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Determine primary provider
        if ranked_providers:
            primary_provider = ranked_providers[0][0]
            primary_count = ranked_providers[0][1]
            
            if primary_count > 0:
                recommendations["primary"] = primary_provider
                recommendations["reasoning"].append(
                    f"Selected {primary_provider} as primary provider with {primary_count} successful requests"
                )
                
                # Determine secondary provider
                if len(ranked_providers) > 1:
                    secondary_provider = ranked_providers[1][0]
                    secondary_count = ranked_providers[1][1]
                    
                    if secondary_count > 0:
                        recommendations["secondary"] = secondary_provider
                        recommendations["reasoning"].append(
                            f"Selected {secondary_provider} as secondary provider with {secondary_count} successful requests"
                        )
                
                # Determine fallback provider
                if len(ranked_providers) > 2:
                    fallback_provider = ranked_providers[2][0]
                    fallback_count = ranked_providers[2][1]
                    
                    if fallback_count > 0:
                        recommendations["fallback"] = fallback_provider
                        recommendations["reasoning"].append(
                            f"Selected {fallback_provider} as fallback provider with {fallback_count} successful requests"
                        )
        
        # Add timeframe support information
        recommendations["timeframe_support"] = {}
        for provider, timeframes in timeframe_support.items():
            recommendations["timeframe_support"][provider] = list(timeframes)
        
        # Store recommendations
        self.results["recommendations"]["forex"] = recommendations
    
    def _generate_crypto_recommendations(self, comparison_results):
        """
        Generate recommendations for crypto data providers
        
        Args:
            comparison_results (dict): Results of crypto provider comparison
        """
        recommendations = {
            "primary": None,
            "secondary": None,
            "fallback": None,
            "reasoning": []
        }
        
        # Count successful requests for each provider
        success_counts = {}
        timeframe_support = {}
        
        for provider, provider_results in comparison_results.items():
            success_counts[provider] = 0
            timeframe_support[provider] = set()
            
            for pair, pair_results in provider_results.items():
                for tf, tf_result in pair_results.items():
                    if tf_result.get("status") == "success":
                        success_counts[provider] += 1
                        timeframe_support[provider].add(tf)
        
        # Rank providers by success count
        ranked_providers = sorted(success_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Determine primary provider
        if ranked_providers:
            primary_provider = ranked_providers[0][0]
            primary_count = ranked_providers[0][1]
            
            if primary_count > 0:
                recommendations["primary"] = primary_provider
                recommendations["reasoning"].append(
                    f"Selected {primary_provider} as primary provider with {primary_count} successful requests"
                )
                
                # Determine secondary provider
                if len(ranked_providers) > 1:
                    secondary_provider = ranked_providers[1][0]
                    secondary_count = ranked_providers[1][1]
                    
                    if secondary_count > 0:
                        recommendations["secondary"] = secondary_provider
                        recommendations["reasoning"].append(
                            f"Selected {secondary_provider} as secondary provider with {secondary_count} successful requests"
                        )
                
                # Determine fallback provider
                if len(ranked_providers) > 2:
                    fallback_provider = ranked_providers[2][0]
                    fallback_count = ranked_providers[2][1]
                    
                    if fallback_count > 0:
                        recommendations["fallback"] = fallback_provider
                        recommendations["reasoning"].append(
                            f"Selected {fallback_provider} as fallback provider with {fallback_count} successful requests"
                        )
        
        # Add timeframe support information
        recommendations["timeframe_support"] = {}
        for provider, timeframes in timeframe_support.items():
            recommendations["timeframe_support"][provider] = list(timeframes)
        
        # Store recommendations
        self.results["recommendations"]["crypto"] = recommendations
    
    def save_results(self):
        """Save test results to file"""
        try:
            results_path = self.results_dir / f"provider_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Add timestamp to results
            self.results["timestamp"] = datetime.now().isoformat()
            
            with open(results_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            
            logger.info(f"Saved comparison results to {results_path}")
            
            # Generate summary report
            self._generate_summary_report()
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def _generate_summary_report(self):
        """Generate a summary report of the test results"""
        try:
            # Create summary report
            report = [
                "# Data Provider Comparison Report",
                f"Generated on: {datetime.now().isoformat()}",
                "",
                "## Provider Status",
                "",
                "| Provider | Status | Details |",
                "| -------- | ------ | ------- |"
            ]
            
            # Add provider status to report
            for provider, status in self.results["providers"].items():
                report.append(
                    f"| {provider} | {status.get('status', 'N/A')} | "
                    f"{status.get('details', status.get('error', 'N/A'))} |"
                )
            
            # Add forex recommendations
            if "forex" in self.results["recommendations"]:
                forex_rec = self.results["recommendations"]["forex"]
                report.extend([
                    "",
                    "## Forex Data Recommendations",
                    "",
                    f"**Primary Provider:** {forex_rec.get('primary', 'None')}",
                    "",
                    f"**Secondary Provider:** {forex_rec.get('secondary', 'None')}",
                    "",
                    f"**Fallback Provider:** {forex_rec.get('fallback', 'None')}",
                    "",
                    "### Reasoning",
                    ""
                ])
                
                for reason in forex_rec.get("reasoning", []):
                    report.append(f"- {reason}")
                
                report.extend([
                    "",
                    "### Timeframe Support",
                    "",
                    "| Provider | Supported Timeframes |",
                    "| -------- | -------------------- |"
                ])
                
                for provider, timeframes in forex_rec.get("timeframe_support", {}).items():
                    report.append(
                        f"| {provider} | {', '.join(timeframes)} |"
                    )
            
            # Add crypto recommendations
            if "crypto" in self.results["recommendations"]:
                crypto_rec = self.results["recommendations"]["crypto"]
                report.extend([
                    "",
                    "## Crypto Data Recommendations",
                    "",
                    f"**Primary Provider:** {crypto_rec.get('primary', 'None')}",
                    "",
                    f"**Secondary Provider:** {crypto_rec.get('secondary', 'None')}",
                    "",
                    f"**Fallback Provider:** {crypto_rec.get('fallback', 'None')}",
                    "",
                    "### Reasoning",
                    ""
                ])
                
                for reason in crypto_rec.get("reasoning", []):
                    report.append(f"- {reason}")
                
                report.extend([
                    "",
                    "### Timeframe Support",
                    "",
                    "| Provider | Supported Timeframes |",
                    "| -------- | -------------------- |"
                ])
                
                for provider, timeframes in crypto_rec.get("timeframe_support", {}).items():
                    report.append(
                        f"| {provider} | {', '.join(timeframes)} |"
                    )
            
            # Save report to file
            report_path = self.results_dir / "provider_comparison_report.md"
            with open(report_path, 'w') as f:
                f.write('\n'.join(report))
            
            logger.info(f"Generated summary report at {report_path}")
            
            # Generate visualization
            self._generate_visualization()
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
    
    def _generate_visualization(self):
        """Generate visualizations of the comparison results"""
        try:
            # Create visualization directory
            viz_dir = self.results_dir / "visualizations"
            viz_dir.mkdir(exist_ok=True)
            
            # Generate provider success rate chart
            self._generate_success_rate_chart(viz_dir)
            
            # Generate timeframe support chart
            self._generate_timeframe_support_chart(viz_dir)
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")
    
    def _generate_success_rate_chart(self, viz_dir):
        """
        Generate chart showing success rate for each provider
        
        Args:
            viz_dir (Path): Directory to save visualization
        """
        try:
            # Calculate success rates for forex
            if "forex" in self.results["comparisons"]:
                forex_success = {}
                forex_total = {}
                
                for provider, provider_results in self.results["comparisons"]["forex"].items():
                    forex_success[provider] = 0
                    forex_total[provider] = 0
                    
                    for pair, pair_results in provider_results.items():
                        for tf, tf_result in pair_results.items():
                            forex_total[provider] += 1
                            if tf_result.get("status") == "success":
                                forex_success[provider] += 1
                
                # Calculate success rates
                forex_rates = {
                    provider: (success / total * 100 if total > 0 else 0) 
                    for provider, success in forex_success.items() 
                    for total in [forex_total[provider]]
                }
                
                # Create bar chart
                plt.figure(figsize=(10, 6))
                plt.bar(forex_rates.keys(), forex_rates.values(), color='skyblue')
                plt.title('Forex Data Provider Success Rates')
                plt.xlabel('Provider')
                plt.ylabel('Success Rate (%)')
                plt.ylim(0, 100)
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                
                # Add value labels on top of bars
                for i, (provider, rate) in enumerate(forex_rates.items()):
                    plt.text(i, rate + 2, f'{rate:.1f}%', ha='center')
                
                # Save chart
                plt.tight_layout()
                plt.savefig(viz_dir / "forex_success_rates.png")
                plt.close()
            
            # Calculate success rates for crypto
            if "crypto" in self.results["comparisons"]:
                crypto_success = {}
                crypto_total = {}
                
                for provider, provider_results in self.results["comparisons"]["crypto"].items():
                    crypto_success[provider] = 0
                    crypto_total[provider] = 0
                    
                    for pair, pair_results in provider_results.items():
                        for tf, tf_result in pair_results.items():
                            crypto_total[provider] += 1
                            if tf_result.get("status") == "success":
                                crypto_success[provider] += 1
                
                # Calculate success rates
                crypto_rates = {
                    provider: (success / total * 100 if total > 0 else 0) 
                    for provider, success in crypto_success.items() 
                    for total in [crypto_total[provider]]
                }
                
                # Create bar chart
                plt.figure(figsize=(10, 6))
                plt.bar(crypto_rates.keys(), crypto_rates.values(), color='lightgreen')
                plt.title('Crypto Data Provider Success Rates')
                plt.xlabel('Provider')
                plt.ylabel('Success Rate (%)')
                plt.ylim(0, 100)
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                
                # Add value labels on top of bars
                for i, (provider, rate) in enumerate(crypto_rates.items()):
                    plt.text(i, rate + 2, f'{rate:.1f}%', ha='center')
                
                # Save chart
                plt.tight_layout()
                plt.savefig(viz_dir / "crypto_success_rates.png")
                plt.close()
            
        except Exception as e:
            logger.error(f"Error generating success rate chart: {e}")
    
    def _generate_timeframe_support_chart(self, viz_dir):
        """
        Generate chart showing timeframe support for each provider
        
        Args:
            viz_dir (Path): Directory to save visualization
        """
        try:
            # Get timeframe support for forex
            if "forex" in self.results["recommendations"]:
                forex_tf_support = self.results["recommendations"]["forex"].get("timeframe_support", {})
                
                if forex_tf_support:
                    # Create a matrix of provider vs timeframe
                    providers = list(forex_tf_support.keys())
                    all_timeframes = set()
                    for tfs in forex_tf_support.values():
                        all_timeframes.update(tfs)
                    all_timeframes = sorted(all_timeframes)
                    
                    # Create matrix
                    matrix = []
                    for provider in providers:
                        row = []
                        for tf in all_timeframes:
                            row.append(1 if tf in forex_tf_support[provider] else 0)
                        matrix.append(row)
                    
                    # Create heatmap
                    plt.figure(figsize=(10, 6))
                    plt.imshow(matrix, cmap='YlGn', aspect='auto')
                    plt.title('Forex Timeframe Support by Provider')
                    plt.xlabel('Timeframe')
                    plt.ylabel('Provider')
                    plt.xticks(range(len(all_timeframes)), all_timeframes)
                    plt.yticks(range(len(providers)), providers)
                    
                    # Add text annotations
                    for i in range(len(providers)):
                        for j in range(len(all_timeframes)):
                            plt.text(j, i, "✓" if matrix[i][j] else "✗", 
                                    ha="center", va="center", color="black")
                    
                    # Save chart
                    plt.tight_layout()
                    plt.savefig(viz_dir / "forex_timeframe_support.png")
                    plt.close()
            
            # Get timeframe support for crypto
            if "crypto" in self.results["recommendations"]:
                crypto_tf_support = self.results["recommendations"]["crypto"].get("timeframe_support", {})
                
                if crypto_tf_support:
                    # Create a matrix of provider vs timeframe
                    providers = list(crypto_tf_support.keys())
                    all_timeframes = set()
                    for tfs in crypto_tf_support.values():
                        all_timeframes.update(tfs)
                    all_timeframes = sorted(all_timeframes)
                    
                    # Create matrix
                    matrix = []
                    for provider in providers:
                        row = []
                        for tf in all_timeframes:
                            row.append(1 if tf in crypto_tf_support[provider] else 0)
                        matrix.append(row)
                    
                    # Create heatmap
                    plt.figure(figsize=(10, 6))
                    plt.imshow(matrix, cmap='YlGn', aspect='auto')
                    plt.title('Crypto Timeframe Support by Provider')
                    plt.xlabel('Timeframe')
                    plt.ylabel('Provider')
                    plt.xticks(range(len(all_timeframes)), all_timeframes)
                    plt.yticks(range(len(providers)), providers)
                    
                    # Add text annotations
                    for i in range(len(providers)):
                        for j in range(len(all_timeframes)):
                            plt.text(j, i, "✓" if matrix[i][j] else "✗", 
                                    ha="center", va="center", color="black")
                    
                    # Save chart
                    plt.tight_layout()
                    plt.savefig(viz_dir / "crypto_timeframe_support.png")
                    plt.close()
            
        except Exception as e:
            logger.error(f"Error generating timeframe support chart: {e}")

async def run_provider_comparison():
    """Run the data provider comparison test"""
    try:
        comparison = DataProviderComparison()
        
        # Test forex providers
        forex_pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
        forex_timeframes = ["1h", "4h", "1d"]
        await comparison.test_forex_providers(forex_pairs, forex_timeframes)
        
        # Test crypto providers
        crypto_pairs = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        crypto_timeframes = ["1h", "4h", "1d"]
        await comparison.test_crypto_providers(crypto_pairs, crypto_timeframes)
        
        # Save results
        comparison.save_results()
        
        logger.info("Data provider comparison completed")
        
    except Exception as e:
        logger.error(f"Error running provider comparison: {e}")

if __name__ == "__main__":
    logger.info("Starting data provider comparison...")
    asyncio.run(run_provider_comparison())


