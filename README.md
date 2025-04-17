# Lingonberry Trade Bot

A trading bot that analyzes markets (forex, indices, metals, crypto) using Smart Money Concepts (SMC) and ICT methodologies.

## Features

- Multi-market analysis (Forex, Crypto, Indices, Metals)
- SMC/ICT strategy implementation
- Trade suggestion with entry, stop loss, and take profit
- Trade journaling and performance analytics
- Backtesting capabilities

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yegor-stuba/Lingonberry-Trade.git
cd Lingonberry-Trade
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r trading_bot/requirements.txt
```

## Usage

1. Configure your API credentials in `trading_bot/config/credentials.py`
2. Run the bot:
```bash
python -m trading_bot/main.py
```

## Data Sources

- Forex: cTrader API
- Crypto: CCXT (Binance, etc.)
- Indices & Metals: Yahoo Finance

## License

MIT
