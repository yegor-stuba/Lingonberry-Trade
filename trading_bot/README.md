# Lingonberry Trading Bot

A comprehensive algorithmic trading system that analyzes markets using Smart Money Concepts (SMC) and provides trade suggestions.

## Features

- Multi-market analysis (Forex, Crypto, Indices, Metals)
- Smart Money Concepts (SMC) analysis
- Trade suggestion with entry, stop loss, and take profit levels
- Risk management
- Trade journaling and performance analytics
- MetaTrader 4 integration via ZeroMQ

## Project Structure

trading_bot/ ├── analysis/ # Market analysis modules ├── bridges/ # External system bridges (MT4, etc.) ├── config/ # Configuration files ├── data/ # Data providers and storage ├── journal/ # Trade journaling ├── risk/ # Risk management ├── services/ # Business logic services ├── tests/ # Test files ├── utils/ # Utility functions ├── bot.py # Main bot class └── main.py # Entry point


## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt

2. Configure your environment:
Configure your API keys in config/credentials.py
3. 
Set up MetaTrader 4 with ZeroMQ bridge (see documentation in bridges/mt4)
4. 
Run the bot:
python main.py



## Data Sources
The bot uses multiple data sources with automatic fallback:

MetaTrader 4 (via ZeroMQ bridge)
Local CSV files
Alpha Vantage API
Other external APIs
License
This project is proprietary and confidential.