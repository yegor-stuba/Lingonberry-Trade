# MT4 ZeroMQ Bridge

This bridge allows the trading bot to communicate with MetaTrader 4 using ZeroMQ.

## Setup Instructions

### 1. Install ZeroMQ for MQL4

1. Download the ZeroMQ for MQL4 library from [GitHub](https://github.com/dingmaotu/mql-zmq)
2. Copy the `Include/Zmq` folder to your MT4 `Include` directory
3. Copy the `Library/MT4/` DLLs to your MT4 `Libraries` directory

### 2. Install the DWX_ZeroMQ_Server EA

1. Copy the `DWX_ZeroMQ_Server.mq4` file to your MT4 `Experts` directory
2. Compile the EA in MetaEditor
3. Restart MetaTrader 4

### 3. Run the ZeroMQ Server

1. Drag and drop the `DWX_ZeroMQ_Server` EA onto a chart
2. Make sure "Allow DLL imports" is enabled in MT4 settings
3. Click "OK" to start the server

### 4. Test the Connection

Run the test script to verify the connection:

```bash
python -m trading_bot.bridges.mt4.test_bridge
```

## Troubleshooting

### Common Issues

1. **"Failed to connect to MT4 ZeroMQ bridge server"**
   - Make sure the EA is running in MT4
   - Check that the ports (5555, 5556, 5557) are not blocked by firewall
   - Verify that ZeroMQ DLLs are properly installed

2. **"Error getting historical data"**
   - Check that the symbol exists in your MT4 terminal
   - Verify that you have sufficient historical data downloaded

3. **"DLL imports not allowed"**
   - Go to MT4 Tools > Options > Expert Advisors
   - Enable "Allow DLL imports"
   - Restart MT4

### Logs

Check the MT4 Experts log for any error messages from the ZeroMQ server.
```

Let's also update the requirements.txt file to include ZeroMQ:

```text:trading_bot/requirements.txt
# Core dependencies
pandas>=1.3.0
numpy>=1.20.0
matplotlib>=3.4.0
scikit-learn>=0.24.0
python-telegram-bot>=13.7
aiohttp>=3.7.4
asyncio>=3.4.3

# Data sources
alpha_vantage>=2.3.1
yfinance>=0.1.63
ccxt>=1.60.0

# Database
sqlite3>=3.35.0

# ZeroMQ for MT4 bridge
pyzmq>=22.3.0

# Utilities
python-dotenv>=0.19.0
```

Now, let's examine the repository structure and make sure everything is organized properly:

1. First, let's create the necessary directories if they don't exist:

```bash
mkdir -p trading_bot/bridges/mt4/mql4
```

2. Let's update the repository with our new files:

```bash
git add trading_bot/data/forex_data.py
git add trading_bot/bridges/mt4/__init__.py
git add trading_bot/bridges/mt4/client.py
git add trading_bot/bridges/mt4/mql4/DWX_ZeroMQ_Server.mq4
git add trading_bot/bridges/mt4/test_bridge.py
git add trading_bot/bridges/mt4/README.md
git add trading_bot/requirements.txt
git commit -m "Implement MT4 ZeroMQ bridge for forex data"
git push
