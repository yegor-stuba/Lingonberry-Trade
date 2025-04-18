"""
Web dashboard for the trading bot
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime, timedelta
import json
from flask_cors import CORS  # Add this import

from trading_bot.journal.trade_journal import TradeJournal
from trading_bot.data.data_processor import DataProcessor
from trading_bot.backtesting.engine import BacktestEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize trade journal
trade_journal = TradeJournal()

# Initialize data processor
data_processor = DataProcessor()

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')

@app.route('/performance')
def performance():
    """Render the performance page"""
    return render_template('performance.html')

@app.route('/backtesting')
def backtesting():
    """Render the backtesting page"""
    return render_template('backtesting.html')

@app.route('/api/trades')
def get_trades():
    """API endpoint to get trades"""
    user_id = request.args.get('user_id', type=int)
    status = request.args.get('status')
    symbol = request.args.get('symbol')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = request.args.get('limit', 100, type=int)
    
    trades = trade_journal.get_trades(
        user_id=user_id,
        status=status,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return jsonify(trades)

@app.route('/api/performance')
def get_performance():
    """API endpoint to get performance metrics"""
    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    metrics = trade_journal.calculate_performance_metrics(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return jsonify(metrics)

@app.route('/api/performance/history')
def get_performance_history():
    """API endpoint to get performance history for charts"""
    user_id = request.args.get('user_id', type=int)
    days = request.args.get('days', 30, type=int)
    
    history = trade_journal.get_performance_history(
        user_id=user_id,
        days=days
    )
    
    return jsonify(history)

@app.route('/api/symbols')
def get_symbols():
    """API endpoint to get available symbols"""
    market = request.args.get('market')
    
    # Get symbols from data processor
    symbols = data_processor.get_available_symbols(market)
    
    return jsonify(symbols)

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """API endpoint to run a backtest"""
    data = request.json
    
    # Extract backtest parameters
    symbol = data.get('symbol')
    timeframe = data.get('timeframe')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    strategy = data.get('strategy')
    parameters = data.get('parameters', {})
    
    # TODO: Implement actual backtesting
    # For now, return dummy data
    
    return jsonify({
        'success': True,
        'results': {
            'trades': [],
            'metrics': {
                'win_rate': 65.0,
                'profit_factor': 1.8,
                'total_pnl': 1250.0
            }
        }
    })

@app.route('/telegram-mini-app')
def telegram_mini_app():
    """Render the Telegram Mini App version of the dashboard"""
    return render_template('telegram_mini_app.html')

def start_dashboard(host='0.0.0.0', port=5000, debug=False):
    """Start the web dashboard"""
    logger.info(f"Starting web dashboard on {host}:{port}")
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    start_dashboard(debug=True)
# Add authentication status endpoint to the web dashboard
@app.route('/api/status')
def get_status():
    """API endpoint to get system status"""
    # Check cTrader connection
    from trading_bot.data.ctrader_data import CTraderData
    ctrader = CTraderData()
    
    # Get data processor status
    from trading_bot.data.data_processor import DataProcessor
    data_processor = DataProcessor()
    
    status = {
        'ctrader': {
            'connected': ctrader.connected,
            'authenticated': ctrader.authenticated
        },
        'system': {
            'uptime': get_system_uptime(),
            'version': '0.1.0'  # Update with your version
        },
        'data_sources': {
            'csv_available': True,  # Always available
            'ctrader_available': ctrader.connected and ctrader.authenticated,
            'crypto_available': True  # Update based on your crypto provider
        }
    }
    
    return jsonify(status)

def get_system_uptime():
    """Get system uptime in seconds"""
    import time
    global start_time
    if not hasattr(app, 'start_time'):
        app.start_time = time.time()
    return int(time.time() - app.start_time)

@app.route('/telegram_journal')
def telegram_journal():
    """Render the journal page optimized for Telegram mini app"""
    return render_template('telegram_journal.html')

@app.route('/api/journal_summary')
def get_journal_summary():
    """API endpoint to get a summary of the journal for Telegram"""
    user_id = request.args.get('user_id', type=int)
    
    # Get trades
    closed_trades = trade_journal.get_closed_trades(user_id=user_id)
    active_trades = trade_journal.get_active_trades(user_id=user_id)
    pending_trades = trade_journal.get_pending_trades(user_id=user_id)
    
    # Get performance metrics
    metrics = trade_journal.calculate_performance_metrics(user_id=user_id)
    
    # Create summary
    summary = {
        'metrics': metrics,
        'trade_counts': {
            'active': len(active_trades),
            'pending': len(pending_trades),
            'closed': len(closed_trades)
        },
        'recent_trades': closed_trades[-5:] if closed_trades else []
    }
    
    return jsonify(summary)