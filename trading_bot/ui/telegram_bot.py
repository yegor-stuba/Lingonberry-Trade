"""
Telegram bot interface for the trading bot
"""

import logging
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import io
from datetime import datetime
import pandas as pd


from telegram import Update, Message
from telegram.ext import ContextTypes
from trading_bot.config import credentials
from trading_bot.strategy.signal_generator import SignalGenerator
from trading_bot.data.data_processor import DataProcessor
from trading_bot.utils.visualization import create_price_chart, create_trade_chart, create_analysis_chart
from trading_bot.journal.trade_journal import TradeJournal
from trading_bot.config.settings import DASHBOARD_URL

logger = logging.getLogger(__name__)

class TelegramBot:
    """
    Telegram bot interface for the trading bot
    """
    
    def __init__(self, dashboard_url=None):
        """Initialize the Telegram bot"""
        self.token = credentials.TELEGRAM_TOKEN
        self.application = Application.builder().token(self.token).build()
        self.data_processor = DataProcessor()
        self.signal_generator = SignalGenerator()
        
        # Default settings
        self.default_timeframe = "H1"
        self.default_bars = 100
        
        # Available pairs
        self.crypto_pairs = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT"]
        self.forex_pairs = ["EURUSD", "GBPUSD", "GBPJPY", "USDJPY", "AUDUSD", "USDCAD"]
        self.indices_pairs = ["US30", "US500", "USTEC", "UK100", "GER40"]
        self.metals_pairs = ["XAUUSD", "XAGUSD"]
        
        # TradingView symbol mapping
        self.tradingview_symbols = {
            # Crypto
            "BTCUSDT": "BINANCE:BTCUSDT",
            "ETHUSDT": "BINANCE:ETHUSDT",
            "XRPUSDT": "BINANCE:XRPUSDT",
            "ADAUSDT": "BINANCE:ADAUSDT",
            "SOLUSDT": "BINANCE:SOLUSDT",
            # Forex
            "EURUSD": "FX:EURUSD",
            "GBPUSD": "FX:GBPUSD",
            "GBPJPY": "FX:GBPJPY",
            "USDJPY": "FX:USDJPY",
            "AUDUSD": "FX:AUDUSD",
            "USDCAD": "FX:USDCAD",
            # Indices
            "US30": "DJ:DJI",
            "US500": "SP:SPX",
            "NAS100": "NASDAQ:NDX",
            "UK100": "OANDA:UK100GBP",
            "GER40": "OANDA:DE30EUR",
            # Metals
            "XAUUSD": "OANDA:XAUUSD",
            "XAGUSD": "OANDA:XAGUSD"
        }
        
          # Initialize trade journal
        self.trade_journal = TradeJournal()
        
        # Use provided dashboard URL or default from settings
        # If dashboard_url is provided, it takes precedence over the environment variable
        if dashboard_url:
            self.dashboard_url = dashboard_url
        else:
            # Try to get from environment variable first, then fall back to settings
            self.dashboard_url = os.environ.get("DASHBOARD_URL", DASHBOARD_URL)
        
        # Log the dashboard URL being used
        logger.info(f"Telegram bot using dashboard URL: {self.dashboard_url}")
        
        # Register handlers
        self.register_handlers()
        
    def register_handlers(self):
        """Register command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("account", self.account_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("analyze", self.analyze_command))
        self.application.add_handler(CommandHandler("pairs", self.pairs_command))
        self.application.add_handler(CommandHandler("timeframes", self.timeframes_command))
        self.application.add_handler(CommandHandler("chart", self.chart_command))
        self.application.add_handler(CommandHandler("journal", self.journal_command))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        await update.message.reply_text(
            "Welcome to the Trading Bot! 📈\n\n"
            "This bot analyzes markets using Smart Money Concepts and ICT methodologies.\n\n"
            "Use /help to see available commands."
        )
    

    # Add this new method:
    async def account_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /account command to set up account information"""
        # Check if arguments are provided
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Please provide account size and risk percentage.\n\n"
                "Example: /account 10000 1.0\n\n"
                "This sets up an account with $10,000 and 1% risk per trade."
            )
            return
        
        try:
            # Parse arguments
            account_size = float(context.args[0])
            risk_percentage = float(context.args[1])
            
            # Validate inputs
            if account_size <= 0:
                await update.message.reply_text("Account size must be greater than 0.")
                return
            
            if risk_percentage <= 0 or risk_percentage > 5:
                await update.message.reply_text("Risk percentage must be between 0 and 5.")
                return
            
            # Get user ID
            user_id = update.effective_user.id
            
            # Set account information
            success = self.trade_journal.set_account_info(
                user_id=user_id,
                account_size=account_size,
                risk_per_trade=risk_percentage
            )
            
            if success:
                await update.message.reply_text(
                    f"✅ Account information set successfully!\n\n"
                    f"Account Size: ${account_size:,.2f}\n"
                    f"Risk per Trade: {risk_percentage}%\n\n"
                    f"This information will be used to calculate position sizes for your trades."
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to set account information. Please try again later."
                )
        
        except ValueError:
            await update.message.reply_text(
                "Invalid input. Please provide valid numbers for account size and risk percentage."
            )
        except Exception as e:
            logger.error(f"Error in account_command: {e}", exc_info=True)
            await update.message.reply_text(
                "An error occurred. Please try again later."
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        help_text = (
            "🤖 *Available Commands*\n\n"
            "🚀 *Basic Commands*\n"
            "• /start - Start the bot\n"
            "• /help - Show this help message\n"
            "• /account <size> <risk%> - Set your account size and risk percentage\n\n"
            "📊 *Trading Commands*\n"
            "• /analyze - Analyze a trading pair\n"
            "• /pairs - Show available trading pairs\n"
            "• /timeframes - Show available timeframes\n"
            "• /chart - View interactive TradingView chart\n\n"
            "📝 *Journal*\n"
            "• /journal - View trading journal\n\n"
            "📌 *Examples*\n"
            "• /analyze BTCUSDT H1\n"
            "• /analyze EURUSD H4\n"
            "• /chart XAUUSD\n"
            "• /account 10000 1.0"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def chart_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /chart command"""
        # Check if arguments are provided
        if not context.args:
            # Show pair selection keyboard
            keyboard = [
                [InlineKeyboardButton("Crypto", callback_data="chart_crypto")],
                [InlineKeyboardButton("Forex", callback_data="chart_forex")],
                [InlineKeyboardButton("Indices", callback_data="chart_indices")],
                [InlineKeyboardButton("Metals", callback_data="chart_metals")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Select a market category to view chart:",
                reply_markup=reply_markup
            )
            return
        
        # Parse arguments
        symbol = context.args[0].upper()
        
        # Show TradingView chart
        await self._show_tradingview_chart(update.message, symbol)
    
    async def pairs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /pairs command"""
        # Create keyboard with market categories
        keyboard = [
            [InlineKeyboardButton("Crypto", callback_data="pairs_crypto")],
            [InlineKeyboardButton("Forex", callback_data="pairs_forex")],
            [InlineKeyboardButton("Indices", callback_data="pairs_indices")],
            [InlineKeyboardButton("Metals", callback_data="pairs_metals")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Select a market category:",
            reply_markup=reply_markup
        )
    
    async def timeframes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /timeframes command"""
        timeframes_text = (
            "Available timeframes:\n\n"
            "M1 - 1 minute\n"
            "M5 - 5 minutes\n"
            "M15 - 15 minutes\n"
            "M30 - 30 minutes\n"
            "H1 - 1 hour\n"
            "H4 - 4 hours\n"
            "D1 - 1 day\n"
            "W1 - 1 week\n"
        )
        await update.message.reply_text(timeframes_text)
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /analyze command"""
        # Check if arguments are provided
        if not context.args:
            # Show pair selection keyboard
            keyboard = [
                [InlineKeyboardButton("Crypto", callback_data="analyze_crypto")],
                [InlineKeyboardButton("Forex", callback_data="analyze_forex")],
                [InlineKeyboardButton("Indices", callback_data="analyze_indices")],
                [InlineKeyboardButton("Metals", callback_data="analyze_metals")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Select a market category to analyze:",
                reply_markup=reply_markup
            )
            return
        
        # Parse arguments
        symbol = context.args[0].upper()
        timeframe = context.args[1].upper() if len(context.args) > 1 else self.default_timeframe
        
        # Send "analyzing" message
        message = await update.message.reply_text(f"Analyzing {symbol} on {timeframe} timeframe... ⏳")
        
        # Perform analysis
        await self.perform_analysis(update, context, symbol, timeframe, message)
    
    async def journal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /journal command"""
        try:
            # Get recent trades
            closed_trades = self.trade_journal.get_closed_trades()
            active_trades = self.trade_journal.get_active_trades()
            pending_trades = self.trade_journal.get_pending_trades()
            
            # Calculate performance metrics
            metrics = self.trade_journal.calculate_performance_metrics()
            
            # Handle case where metrics is None
            if metrics is None:
                metrics = {}
            
            # Ensure all required metrics exist
            metrics.setdefault('total_trades', len(closed_trades) + len(active_trades) + len(pending_trades))
            metrics.setdefault('win_rate', 0.0)
            metrics.setdefault('net_profit', 0.0)
            metrics.setdefault('profit_factor', 0.0)
            
            # Create message
            message = (
                "📊 *Trade Journal Summary*\n\n"
                f"*Performance Metrics:*\n"
                f"Total Trades: {metrics['total_trades']}\n"
                f"Win Rate: {metrics['win_rate']:.2%}\n"
                f"Net Profit: {metrics['net_profit']:.2f}\n"
                f"Profit Factor: {metrics['profit_factor']:.2f}\n\n"
                
                f"*Active Trades:* {len(active_trades)}\n"
                f"*Pending Trades:* {len(pending_trades)}\n"
                f"*Closed Trades:* {len(closed_trades)}\n\n"
            )
            
            # Add recent trades
            if closed_trades:
                message += "*Recent Closed Trades:*\n"
                for trade in closed_trades[-5:]:  # Show last 5 trades
                    outcome = trade.get("outcome", "unknown")
                    outcome_emoji = "✅" if outcome == "win" else "❌"
                    profit_loss = trade.get("profit_loss", 0.0)
                    profit_loss_str = f"({profit_loss:.2f})" if isinstance(profit_loss, (int, float)) else "(0.00)"
                    
                    message += (
                        f"{outcome_emoji} {trade.get('symbol', 'Unknown')} {trade.get('direction', 'Unknown')} "
                        f"{profit_loss_str}\n"
                    )
            else:
                message += "*No closed trades yet.*\n"
            
            # Create keyboard with options
            keyboard = [
                [
                    InlineKeyboardButton("View Active Trades", callback_data="journal_active"),
                    InlineKeyboardButton("View Pending Trades", callback_data="journal_pending")
                ],
                [
                    InlineKeyboardButton("View Performance", callback_data="journal_performance")
                ]
            ]
            
            # Prepare journal URL for web app
            # First, check if we have a valid dashboard URL (not localhost)
            has_valid_url = (
                self.dashboard_url and 
                not "localhost" in self.dashboard_url and 
                not "127.0.0.1" in self.dashboard_url
            )
            
            if has_valid_url:
                # Format the URL properly
                base_url = self.dashboard_url
                if base_url.endswith('/'):
                    base_url = base_url[:-1]
                
                # Create the journal URL
                journal_url = f"{base_url}/performance"
                
                # Add parameters to bypass ngrok warning if needed
                if "ngrok" in journal_url:
                    journal_url += "?ngrok-skip-browser-warning=true"
                
                logger.info(f"Using journal URL: {journal_url}")
                
                # Add web app button
                keyboard.append([
                    InlineKeyboardButton("Open Journal 📊", web_app=WebAppInfo(url=journal_url))
                ])
            else:
                logger.warning(f"Not adding web app button because URL is invalid: {self.dashboard_url}")
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Check if this is a callback query or a direct command
            if update.callback_query:
                # This is a button click
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                # This is a direct command
                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error in journal_command: {e}", exc_info=True)
            
            # Handle error response based on update type
            error_message = "Sorry, there was an error retrieving your journal data. Please try again later."
            
            if update.callback_query:
                await update.callback_query.edit_message_text(error_message)
            elif update.message:
                await update.message.reply_text(error_message)
            else:
                logger.error("Could not respond to user - neither callback_query nor message available")




    async def show_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show performance metrics from the journal"""
        try:
            # Get performance metrics
            metrics = self.trade_journal.calculate_performance_metrics()
            
            # Handle case where metrics is None
            if metrics is None:
                metrics = {}
            
            # Ensure all required metrics exist
            metrics.setdefault('total_trades', 0)
            metrics.setdefault('win_rate', 0.0)
            metrics.setdefault('net_profit', 0.0)
            metrics.setdefault('profit_factor', 0.0)
            metrics.setdefault('max_drawdown', 0.0)
            metrics.setdefault('avg_win', 0.0)
            metrics.setdefault('avg_loss', 0.0)
            
            # Get performance history for chart
            history = self.trade_journal.get_performance_history(days=30)
            
            # Create message
            message = (
                "📊 *Performance Metrics*\n\n"
                f"Total Trades: {metrics['total_trades']}\n"
                f"Win Rate: {metrics['win_rate']:.2%}\n"
                f"Net Profit: {metrics['net_profit']:.2f}\n"
                f"Profit Factor: {metrics['profit_factor']:.2f}\n"
                f"Max Drawdown: {metrics['max_drawdown']:.2%}\n"
                f"Avg Win: {metrics['avg_win']:.2f}\n"
                f"Avg Loss: {metrics['avg_loss']:.2f}\n\n"
            )
            
            # Create keyboard with back button
            keyboard = [
                [InlineKeyboardButton("◀️ Back to Journal", callback_data="journal")]
            ]
            
            # Add web app button if dashboard URL is available
            journal_url = f"{self.dashboard_url}/performance"
            if self.dashboard_url and not "localhost" in self.dashboard_url and not "127.0.0.1" in self.dashboard_url:
                keyboard.append([
                    InlineKeyboardButton("Open Performance Dashboard 📊", web_app=WebAppInfo(url=journal_url))
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error showing performance: {e}", exc_info=True)
            await update.callback_query.edit_message_text(
                text="Sorry, an error occurred while processing your request. Please try again later."
            )

    async def show_active_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show active trades from the journal"""
        active_trades = self.trade_journal.get_active_trades()
        
        if not active_trades:
            await update.callback_query.edit_message_text(
                text="📊 *Trading Journal - Active Trades*\n\nNo active trades found.",
                parse_mode='Markdown'
            )
            return
        
        # Format the active trades
        text = "📊 *Trading Journal - Active Trades*\n\n"
        for trade in active_trades:
            text += f"*{trade['symbol']}* ({trade['direction']})\n"
            text += f"Entry: {trade['entry_price']:.5f}\n"
            text += f"Stop Loss: {trade['stop_loss']:.5f}\n"
            text += f"Take Profit: {trade['take_profit']:.5f}\n"
            text += f"Status: {trade['status']}\n"
            text += f"Date: {trade['date']}\n\n"
        
        # Add back button
        keyboard = [
            [InlineKeyboardButton("◀️ Back to Journal", callback_data="journal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send the formatted text
        await update.callback_query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def show_pending_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pending trades from the journal"""
        # Use check_pending_trades instead of get_pending_trades
        pending_trades = self.trade_journal.check_pending_trades()
        
        if not pending_trades:
            await update.callback_query.edit_message_text(
                text="📊 *Trading Journal - Pending Trades*\n\nNo pending trades found.",
                parse_mode='Markdown'
            )
            return
        
        # Format the pending trades
        text = "📊 *Trading Journal - Pending Trades*\n\n"
        for trade in pending_trades:
            text += f"*{trade['symbol']}* ({trade['direction']})\n"
            text += f"Entry: {trade['entry_price']:.5f}\n"
            text += f"Stop Loss: {trade['stop_loss']:.5f}\n"
            text += f"Take Profit: {trade['take_profit']:.5f}\n"
            text += f"Status: {trade['status']}\n"
            text += f"Date: {trade['date']}\n\n"
        
        # Send the formatted text
        await update.callback_query.edit_message_text(
            text=text,
            parse_mode='Markdown'
        )
        
    async def handle_trade_decision(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user decision on a trade setup"""
        query = update.callback_query
        await query.answer()
        
        # Get trade data from callback data
        callback_data = query.data
        parts = callback_data.split("_")
        action = parts[1]
        
        # Get trade data from context
        trade_data = context.user_data.get("current_trade_setup")
        
        if not trade_data:
            await query.edit_message_text("Error: No trade setup found.")
            return
        
        if action == "accept":
            # Get user ID
            user_id = update.effective_user.id
            
            # Record the trade with user ID
            trade_id = self.trade_journal.record_trade(trade_data, user_id=user_id)
            
            # Create keyboard with journal button
            keyboard = [
                [InlineKeyboardButton("View Journal Summary", callback_data="journal")]
            ]
            
            # Add web app button only if we have a valid URL
            journal_url = f"{self.dashboard_url}/telegram_journal"
            if self.dashboard_url.endswith('/'):
                journal_url = f"{self.dashboard_url[:-1]}/telegram_journal"
            
            if not "localhost" in self.dashboard_url and not "127.0.0.1" in self.dashboard_url:
                keyboard[0].append(
                    InlineKeyboardButton("Open Journal 📊", web_app=WebAppInfo(url=journal_url))
                )
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send confirmation with buttons
            await query.edit_message_text(
                f"✅ Trade accepted and recorded!\n\n"
                f"Symbol: {trade_data['symbol']}\n"
                f"Direction: {trade_data['direction']}\n"
                f"Entry: {trade_data['entry_price']}\n"
                f"Stop Loss: {trade_data['stop_loss']}\n"
                f"Take Profit: {trade_data['take_profit']}\n"
                f"Risk/Reward: {trade_data['risk_reward']:.2f}\n\n"
                f"Trade ID: {trade_id}\n\n"
                f"The trade has been added to your journal and will be monitored.",
                reply_markup=reply_markup
            )
                
        elif action == "reject":
            # Just acknowledge rejection
            await query.edit_message_text(
                f"❌ Trade rejected.\n\n"
                f"Symbol: {trade_data['symbol']}\n"
                f"Direction: {trade_data['direction']}\n\n"
                f"The trade has not been recorded."
            )
            
        elif action == "modify":
            # Show modification options
            keyboard = [
                [
                    InlineKeyboardButton("Change Entry", callback_data=f"modify_entry"),
                    InlineKeyboardButton("Change Stop Loss", callback_data=f"modify_sl")
                ],
                [
                    InlineKeyboardButton("Change Take Profit", callback_data=f"modify_tp"),
                    InlineKeyboardButton("Cancel", callback_data=f"modify_cancel")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"🔧 Modify Trade Setup\n\n"
                f"Symbol: {trade_data['symbol']}\n"
                f"Direction: {trade_data['direction']}\n"
                f"Entry: {trade_data['entry_price']}\n"
                f"Stop Loss: {trade_data['stop_loss']}\n"
                f"Take Profit: {trade_data['take_profit']}\n"
                f"Risk/Reward: {trade_data['risk_reward']:.2f}\n\n"
                f"What would you like to modify?",
                reply_markup=reply_markup
            )
        
        # Clear the current trade setup
        if action != "modify":
            context.user_data.pop("current_trade_setup", None)

    async def perform_analysis(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE,
        symbol: str, 
        timeframe: str, 
        message: Message
    ):
        """Perform analysis on a symbol and timeframe"""
        try:
            # Determine data source based on symbol
            if symbol in self.forex_pairs or symbol in self.indices_pairs or symbol in self.metals_pairs:
                source = 'ctrader'
            else:
                source = 'crypto'
                
            # Get data with fallback options
            df = None
            error_message = None
            
            try:
                # Try primary source first
                df = await self.data_processor.get_data(symbol, timeframe, bars=self.default_bars, source=source)
            except Exception as e:
                error_message = f"Error fetching data from {source}: {str(e)}"
                logger.warning(error_message)
            
            # If primary source failed, try CSV
            if df is None or df.empty:
                if error_message:
                    logger.info(f"Attempting to load data from CSV as fallback for {symbol} {timeframe}")
                try:
                    df = await self.data_processor.get_data(symbol, timeframe, bars=self.default_bars, source='csv')
                    if df is not None and not df.empty:
                        logger.info(f"Successfully loaded {len(df)} rows from CSV for {symbol} {timeframe}")
                except Exception as csv_error:
                    logger.error(f"CSV fallback also failed: {str(csv_error)}")
            
            if df is None or df.empty:
                await message.edit_text(f"❌ Error: No data available for {symbol} on {timeframe} timeframe. Please try another symbol or timeframe.")
                return
                    
            # Generate signals
            signals = self.signal_generator.generate_signals(symbol, df, timeframe)
            
            # Log the number of signals found
            logger.info(f"Found {len(signals)} raw signals for {symbol} on {timeframe}")
            
            # Filter signals with less strict criteria
            filtered_signals = self.signal_generator.filter_signals(signals, min_risk_reward=2.0, min_strength=60)
            logger.info(f"After filtering, {len(filtered_signals)} signals remain")
            
            # Create TradingView URL with appropriate timeframe
            tv_timeframe = self._convert_to_tv_timeframe(timeframe)
            tv_url = self._get_tradingview_url(symbol, tv_timeframe)
            
            # Create keyboard with TradingView chart button
            keyboard = [
                [InlineKeyboardButton(
                    "Open Interactive Chart", 
                    web_app=WebAppInfo(url=tv_url)
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Prepare analysis message
            if filtered_signals:
                # Sort signals by risk-reward ratio (descending)
                sorted_signals = sorted(filtered_signals, key=lambda x: x.get('risk_reward', 0), reverse=True)
                
                # Take top 3 signals
                top_signals = sorted_signals[:3]
                
                # Process each signal
                trade_setups = []
                for signal in top_signals:
                    trade_setup = self.signal_generator.get_trade_setup(signal)
                    trade_setup['timeframe'] = timeframe
                    trade_setups.append(trade_setup)
                
                # Store the best trade setup in user data
                if trade_setups:
                    context.user_data["current_trade_setup"] = trade_setups[0]
                
                # Create chart with the best trade setup
                if trade_setups:
                    chart_buffer = create_trade_chart(
                        df,
                        trade_setups[0],
                        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                else:
                    chart_buffer = None
                
                # Create keyboard with accept/reject buttons for the best trade
                keyboard = [
                    [
                        InlineKeyboardButton("Accept Trade ✅", callback_data=f"trade_accept"),
                        InlineKeyboardButton("Reject Trade ❌", callback_data=f"trade_reject")
                    ],
                    [
                        InlineKeyboardButton("Modify Trade 🔧", callback_data=f"trade_modify"),
                        InlineKeyboardButton("View Chart 📊", web_app=WebAppInfo(url=self._get_tradingview_url(symbol)))
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Format message with all trade setups
                message_text = f"📊 Analysis for {symbol} on {timeframe} timeframe\n\n"
                message_text += f"Found {len(filtered_signals)} potential trade setups. Here are the top ones:\n\n"
                
                for i, setup in enumerate(trade_setups):
                    message_text += f"*Trade Setup {i+1}:*\n"
                    message_text += self._format_trade_setup(setup)
                    message_text += "\n\n"
                
                message_text += "You can accept, reject, or modify the top trade setup."
                
                if chart_buffer:
                    # If we have a chart, send it as a photo
                    await message.delete()
                    await update.message.reply_photo(
                        photo=chart_buffer,
                        caption=message_text[:1024],  # Limit caption to 1024 chars
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    
                    # If the message is too long, send the rest as a text message
                    if len(message_text) > 1024:
                        await update.message.reply_text(
                            message_text[1024:],
                            parse_mode='Markdown'
                        )
                else:
                    # If chart creation failed, still show the trade setups with buttons
                    logger.warning(f"Failed to create chart for {symbol} trade setup, showing text only")
                    await message.edit_text(
                        message_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                return
                    
            else:
                # Send analysis with no signals
                await message.edit_text(
                    f"Analysis for {symbol} on {timeframe} timeframe.\n\n"
                    f"No trading signals found that meet the criteria (RR ≥ 2.0, Strength ≥ 60).\n\n"
                    f"Click the button below to view the chart.",
                    reply_markup=reply_markup
                )
                    
        except Exception as e:
            logger.error(f"Error in perform_analysis: {e}", exc_info=True)
            await message.edit_text(f"❌ Error analyzing {symbol} on {timeframe} timeframe: {str(e)}")


    # Add this method to ensure trades are properly recorded
    def record_trade(self, trade_data):
        """
        Record a new trade in the journal
        
        Args:
            trade_data (dict): Trade data including symbol, direction, entry_price, etc.
            
        Returns:
            str: Trade ID
        """
        # Generate a unique trade ID
        from uuid import uuid4
        trade_id = str(uuid4())
        
        # Add additional fields
        trade_data['id'] = trade_id
        trade_data['status'] = 'pending'
        trade_data['entry_time'] = datetime.now().isoformat()
        trade_data['outcome'] = None
        trade_data['exit_time'] = None
        trade_data['exit_price'] = None
        trade_data['profit_loss'] = 0
        trade_data['profit_loss_pips'] = 0
        
        # Save to database
        self._save_trade(trade_data)
        
        logger.info(f"Recorded new trade: {trade_id} - {trade_data['symbol']} {trade_data['direction']}")
        
        return trade_id
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
    
        callback_data = query.data
    
        if callback_data.startswith("pairs_"):
            # Handle pairs selection
            market = callback_data.split("_")[1]
            await self._show_pairs_for_market(query, market)
        
        elif callback_data.startswith("account_"):
            # Handle account selection
            await self._show_account_balance(query)
    
        elif callback_data.startswith("analyze_"):
            if "_" in callback_data[8:]:
                # Handle specific symbol and timeframe analysis
                _, symbol, timeframe = callback_data.split("_")
                await self.analyze_command_with_args(update, context, symbol, timeframe)
            else:
                # Handle analyze market selection
                market = callback_data.split("_")[1]
                await self._show_pairs_for_analysis(query, market)
    
        elif callback_data.startswith("chart_"):
            # Handle chart market selection
            market = callback_data.split("_")[1]
            await self._show_pairs_for_chart(query, market)
    
        elif callback_data.startswith("pair_"):
            # Handle specific pair selection
            parts = callback_data.split("_")
            symbol = parts[1]
            action = parts[2] if len(parts) > 2 else "info"
        
            if action == "analyze":
                # Show timeframe selection for analysis
                await self._show_timeframes_for_analysis(query, symbol)
            elif action == "chart":
                # Show TradingView chart
                await self._show_tradingview_chart(query.message, symbol, edit=True)
            else:
                # Show pair info
                await self._show_pair_info(query, symbol)
    
        elif callback_data.startswith("tf_"):
            # Handle timeframe selection
            parts = callback_data.split("_")
            symbol = parts[1]
            timeframe = parts[2]
        
            # Edit message to show "analyzing"
            await query.edit_message_text(f"Analyzing {symbol} on {timeframe} timeframe... ⏳")
        
            # Perform analysis
            await self.perform_analysis(update, context, symbol, timeframe, query.message)

        elif callback_data.startswith("trade_"):
            # Handle trade actions (take trade, skip, etc.)
            if len(callback_data.split("_")) > 1:
                action = callback_data.split("_")[1]
                if action == "take":
                    await self.take_trade(update, context)
                elif action == "skip":
                    await self.skip_trade(update, context)
            else:
                await self.handle_trade_decision(update, context)
            
        elif callback_data.startswith("journal"):
            if callback_data == "journal_pending":
                await self.show_pending_trades(update, context)
            elif callback_data == "journal_completed":
                await self.show_completed_trades(update, context)
            elif callback_data == "journal_performance":
                await self.show_performance(update, context)
            # In the button_callback method, add this case in the journal section:
            elif callback_data == "journal_active":
                await self.show_active_trades(update, context)

            else:
                await self.journal_command(update, context)
            
        elif callback_data.startswith("modify_"):
            await self.handle_trade_modification(update, context)
    
        else:
            await query.edit_message_text(text=f"Unknown callback: {callback_data}")   

    async def _show_pairs_for_market(self, query, market):
        """Show pairs for a specific market"""
        pairs = []
        if market == "crypto":
            pairs = self.crypto_pairs
            title = "Cryptocurrency Pairs"
        elif market == "forex":
            pairs = self.forex_pairs
            title = "Forex Pairs"
        elif market == "indices":
            pairs = self.indices_pairs
            title = "Indices"
        elif market == "metals":
            pairs = self.metals_pairs
            title = "Metals"
        
        # Create keyboard with pairs
        keyboard = []
        for pair in pairs:
            keyboard.append([InlineKeyboardButton(pair, callback_data=f"pair_{pair}_info")])
        
        # Add back button
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="pairs")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{title}:\n\nSelect a pair to view information.",
            reply_markup=reply_markup
        )
    
    async def _show_pairs_for_analysis(self, query, market):
        """Show pairs for analysis"""
        pairs = []
        if market == "crypto":
            pairs = self.crypto_pairs
            title = "Cryptocurrency Pairs"
        elif market == "forex":
            pairs = self.forex_pairs
            title = "Forex Pairs"
        elif market == "indices":
            pairs = self.indices_pairs
            title = "Indices"
        elif market == "metals":
            pairs = self.metals_pairs
            title = "Metals"
        
        # Create keyboard with pairs
        keyboard = []
        for pair in pairs:
            keyboard.append([InlineKeyboardButton(pair, callback_data=f"pair_{pair}_analyze")])
        
        # Add back button
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="analyze")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{title}:\n\nSelect a pair to analyze.",
            reply_markup=reply_markup
        )
    
    async def _show_pairs_for_chart(self, query, market):
        """Show pairs for chart viewing"""
        pairs = []
        if market == "crypto":
            pairs = self.crypto_pairs
            title = "Cryptocurrency Pairs"
        elif market == "forex":
            pairs = self.forex_pairs
            title = "Forex Pairs"
        elif market == "indices":
            pairs = self.indices_pairs
            title = "Indices"
        elif market == "metals":
            pairs = self.metals_pairs
            title = "Metals"
        
        # Create keyboard with pairs
        keyboard = []
        for pair in pairs:
            keyboard.append([InlineKeyboardButton(pair, callback_data=f"pair_{pair}_chart")])
        
        # Add back button
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="chart")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{title}:\n\nSelect a pair to view chart.",
            reply_markup=reply_markup
        )

    async def handle_trade_modification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle trade modification actions"""
            query = update.callback_query
            
            # Get modification data from callback data
            callback_data = query.data
            parts = callback_data.split("_")
            action = parts[1]  # modify or cancel
            
            # Get trade data from context
            trade_data = context.user_data.get("current_trade_setup")
            
            if not trade_data:
                await query.edit_message_text("Error: No trade setup found.")
                return
            
            if action == "cancel":
                # Show the original trade setup with accept/reject buttons
                keyboard = [
                    [
                        InlineKeyboardButton("Accept Trade ✅", callback_data=f"trade_accept"),
                        InlineKeyboardButton("Reject Trade ❌", callback_data=f"trade_reject")
                    ],
                    [
                        InlineKeyboardButton("Modify Trade 🔧", callback_data=f"trade_modify"),
                        InlineKeyboardButton("View Chart 📊", web_app=WebAppInfo(url=self._get_tradingview_url(trade_data['symbol'])))
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    self._format_trade_setup(trade_data),
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            # For modify - we need to prompt for all values at once
            message = (
                f"Please enter the new values for {trade_data['symbol']} {trade_data['direction']} in the following format:\n\n"
                "entry,sl,tp\n\n"
                "Example: 1.2345,1.2300,1.2400\n\n"
                "Current values:\n"
                f"Entry: {trade_data.get('entry', 'Not set')}\n"
                f"Stop Loss: {trade_data.get('sl', 'Not set')}\n"
                f"Take Profit: {trade_data.get('tp', 'Not set')}"
            )
            
            # Add a cancel button
            keyboard = [[InlineKeyboardButton("Cancel", callback_data="modify_cancel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Edit the message to ask for the new values
            await query.edit_message_text(
                message,
                reply_markup=reply_markup
            )
            
            # Set a flag in user data to indicate we're waiting for modification values
            context.user_data["awaiting_modification"] = True
            context.user_data["modification_type"] = "all"  # Indicates we're updating all values at once    
    
    async def _show_timeframes_for_analysis(self, query, symbol):
        """Show timeframe selection for analysis"""
        # Create keyboard with timeframes
        keyboard = [
            [
                InlineKeyboardButton("M15", callback_data=f"tf_{symbol}_M15"),
                InlineKeyboardButton("M30", callback_data=f"tf_{symbol}_M30"),
                InlineKeyboardButton("H1", callback_data=f"tf_{symbol}_H1")
            ],
            [
                InlineKeyboardButton("H4", callback_data=f"tf_{symbol}_H4"),
                InlineKeyboardButton("D1", callback_data=f"tf_{symbol}_D1"),
                InlineKeyboardButton("W1", callback_data=f"tf_{symbol}_W1")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data=f"analyze")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Select timeframe for {symbol} analysis:",
            reply_markup=reply_markup
        )
    
    async def _show_pair_info(self, query, symbol):
        """Show information about a pair"""
        # Create keyboard with actions
        keyboard = [
            [
                InlineKeyboardButton("Analyze", callback_data=f"pair_{symbol}_analyze"),
                InlineKeyboardButton("View Chart", callback_data=f"pair_{symbol}_chart")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="pairs")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Determine market type
        market_type = "Cryptocurrency"
        if symbol in self.forex_pairs:
            market_type = "Forex"
        elif symbol in self.indices_pairs:
            market_type = "Index"
        elif symbol in self.metals_pairs:
            market_type = "Metal"
        
        await query.edit_message_text(
            f"Symbol: {symbol}\n"
            f"Market: {market_type}\n\n"
            f"What would you like to do with {symbol}?",
            reply_markup=reply_markup
        )
    
    async def _show_tradingview_chart(self, message, symbol, edit=False):
        """Show TradingView chart for a symbol"""
        # Get TradingView symbol
        tv_symbol = self.tradingview_symbols.get(symbol, symbol)
        
        # Create keyboard with TradingView chart button
        keyboard = [
            [InlineKeyboardButton(
                "Open TradingView Chart", 
                web_app=WebAppInfo(url=self._get_tradingview_url(symbol))
            )]
        ]
        
        # Add back button
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="chart")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"TradingView Chart for {symbol}\n\nClick the button below to open the interactive chart."
        
        if edit:
            await message.edit_text(text, reply_markup=reply_markup)
        else:
            await message.reply_text(text, reply_markup=reply_markup)
    
    def _convert_to_tv_timeframe(self, timeframe):
        """Convert internal timeframe format to TradingView format"""
        # Map your timeframes to TradingView timeframes
        tv_timeframe_map = {
            'M1': '1',
            'M5': '5',
            'M15': '15',
            'M30': '30',
            'H1': '60',
            'H4': '240',
            'D1': 'D',
            'W1': 'W'
        }
        return tv_timeframe_map.get(timeframe, '60')  # Default to 1 hour

    def _get_tradingview_url(self, symbol, timeframe='60', include_indicators=True):
        """Get TradingView URL for a symbol and timeframe with optional indicators"""
        # Get TradingView symbol
        tv_symbol = self.tradingview_symbols.get(symbol, symbol)
        
        # Base URL
        base_url = f"https://s.tradingview.com/widgetembed/?frameElementId=tradingview_76d87&symbol={tv_symbol}&interval={timeframe}&hideideas=1&hidetrading=1&symboledit=1&saveimage=1&toolbarbg=f1f3f6"
        
        # Add indicators if requested
        if include_indicators:
            # URL-encoded studies parameter for common indicators
            # This adds: 20 EMA, 50 EMA, 200 EMA, RSI, and Volume
            studies = "%5B%7B%22id%22%3A%22MASimple%40tv-basicstudies%22%2C%22inputs%22%3A%7B%22length%22%3A20%7D%7D%2C%7B%22id%22%3A%22MASimple%40tv-basicstudies%22%2C%22inputs%22%3A%7B%22length%22%3A50%7D%7D%2C%7B%22id%22%3A%22MASimple%40tv-basicstudies%22%2C%22inputs%22%3A%7B%22length%22%3A200%7D%7D%2C%7B%22id%22%3A%22RSI%40tv-basicstudies%22%7D%2C%7B%22id%22%3A%22Volume%40tv-basicstudies%22%7D%5D"
            base_url += f"&studies={studies}"
        else:
            base_url += "&studies=%5B%5D"
        
        # Add theme
        base_url += "&theme=Light"
        
        return base_url
    
    def _format_trade_setup(self, trade_setup):
        """Format trade setup for display with improved number formatting and position sizing"""
        direction = trade_setup.get('direction', 'UNKNOWN')
        entry_price = trade_setup.get('entry_price', 0)
        stop_loss = trade_setup.get('stop_loss', 0)
        take_profit = trade_setup.get('take_profit', 0)
        risk_reward = trade_setup.get('risk_reward', 0)
        reason = trade_setup.get('reason', 'No reason provided')
        symbol = trade_setup.get('symbol', 'Unknown')
        timeframe = trade_setup.get('timeframe', 'Unknown')
        strategy = trade_setup.get('strategy', 'Unknown')
        
        # Calculate risk in pips/points
        risk_points = abs(entry_price - stop_loss)
        
        # Format numbers based on symbol type
        if 'USD' in symbol:
            # For forex pairs like EURUSD, use 5 decimal places
            if symbol in self.forex_pairs:
                price_format = "{:.5f}"
            # For gold (XAUUSD), use 2 decimal places
            elif symbol == 'XAUUSD':
                price_format = "{:.2f}"
            # For JPY, use 3 decimal places
            elif any(symbol in forex for forex in ['GBPJPY', 'USDJPY']):
                price_format = "{:.3f}"
            # For crypto, use appropriate decimal places based on price magnitude
            elif any(crypto in symbol for crypto in ['BTC', 'ETH']):
                if entry_price > 1000:
                    price_format = "{:.2f}"
                else:
                    price_format = "{:.5f}"
            # Default format for other USD pairs
            else:
                price_format = "{:.2f}"
        else:
            # Default format for other symbols
            price_format = "{:.5f}"
        
        # Get user ID from context if available
        user_id = None
        if hasattr(self, 'current_user_id'):
            user_id = self.current_user_id
        
        # Calculate position size and potential profit/loss
        position_info = {}
        potential_profit = 0
        potential_loss = 0
        
        if user_id:
            # Calculate position size based on user's account
            position_info = self.trade_journal.calculate_position_size(
                user_id=user_id,
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss
            )
            
            # Calculate potential profit and loss
            position_size = position_info.get('position_size', 0)
            
            if direction == 'BUY':
                potential_profit = position_size * (take_profit - entry_price)
                potential_loss = position_size * (entry_price - stop_loss)
            else:  # SELL
                potential_profit = position_size * (entry_price - take_profit)
                potential_loss = position_size * (stop_loss - entry_price)
        else:
            # Use default values if no user ID
            account_size = 10000.0
            risk_percentage = 1.0
            risk_amount = account_size * (risk_percentage / 100)
            
            # Calculate a simple position size (this is simplified)
            if risk_points > 0:
                position_size = risk_amount / risk_points
            else:
                position_size = 0
            
            # Calculate potential profit and loss
            if direction == 'BUY':
                potential_profit = position_size * (take_profit - entry_price)
                potential_loss = position_size * (entry_price - stop_loss)
            else:  # SELL
                potential_profit = position_size * (entry_price - take_profit)
                potential_loss = position_size * (stop_loss - entry_price)
            
            position_info = {
                'account_size': account_size,
                'risk_percentage': risk_percentage,
                'risk_amount': risk_amount,
                'position_size': position_size
            }
        
        # Format the message with properly formatted numbers
        message = (
            f"📊 *Trade Setup: {direction}*\n\n"
            f"Symbol: {symbol}\n"
            f"Timeframe: {timeframe}\n"
            f"Strategy: {strategy}\n\n"
            f"Entry: {price_format.format(entry_price)}\n"
            f"Stop Loss: {price_format.format(stop_loss)}\n"
            f"Take Profit: {price_format.format(take_profit)}\n\n"
            f"Risk: {price_format.format(risk_points)} points\n"
            f"Risk/Reward: {risk_reward:.2f}\n\n"
        )
        
        # Add position sizing information
        message += (
            f"*Position Sizing:*\n"
            f"Account Size: ${position_info.get('account_size', 10000):,.2f}\n"
            f"Risk: {position_info.get('risk_percentage', 1.0)}% (${position_info.get('risk_amount', 100):,.2f})\n"
            f"Position Size: {position_info.get('position_size', 0):,.2f} units\n\n"
            f"Potential Profit: ${potential_profit:,.2f}\n"
            f"Potential Loss: ${potential_loss:,.2f}\n\n"
        )
        
        # Add analysis reason
        message += f"*Analysis:*\n{reason}"

        return message

  
   
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        # Store the current user ID for position sizing calculations
        self.current_user_id = update.effective_user.id
        
        text = update.message.text.strip()
        
        # Check if we're waiting for a modification value
        if context.user_data.get("awaiting_modification", False):
            # Get the modification type and trade data
            mod_type = context.user_data.get("modification_type")
            trade_data = context.user_data.get("current_trade_setup")
            
            if not trade_data or not mod_type:
                await update.message.reply_text("Error: Missing trade data or modification type.")
                context.user_data.pop("awaiting_modification", None)
                context.user_data.pop("modification_type", None)
                return
            
            # Try to parse the new value
            try:
                new_value = float(text)
                
                # Update the trade data
                if mod_type == "entry":
                    trade_data["entry_price"] = new_value
                elif mod_type == "sl":
                    trade_data["stop_loss"] = new_value
                elif mod_type == "tp":
                    trade_data["take_profit"] = new_value
                
                # Recalculate risk/reward
                if trade_data["direction"] == "BUY":
                    risk = abs(trade_data["entry_price"] - trade_data["stop_loss"])
                    reward = abs(trade_data["take_profit"] - trade_data["entry_price"])
                else:  # SELL
                    risk = abs(trade_data["stop_loss"] - trade_data["entry_price"])
                    reward = abs(trade_data["entry_price"] - trade_data["take_profit"])
                
                trade_data["risk_reward"] = reward / risk if risk > 0 else 0
                
                # Clear the modification flags
                context.user_data.pop("awaiting_modification", None)
                context.user_data.pop("modification_type", None)
                
                # Show the updated trade setup
                keyboard = [
                    [
                        InlineKeyboardButton("Accept Trade ✅", callback_data=f"trade_accept"),
                        InlineKeyboardButton("Reject Trade ❌", callback_data=f"trade_reject")
                    ],
                    [
                        InlineKeyboardButton("Modify Trade 🔧", callback_data=f"trade_modify"),
                        InlineKeyboardButton("View Chart 📊", web_app=WebAppInfo(url=self._get_tradingview_url(trade_data['symbol'])))
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ Trade setup updated!\n\n" + self._format_trade_setup(trade_data),
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            except ValueError:
                await update.message.reply_text(
                    f"❌ Invalid value. Please enter a valid number."
                )
                return
            
            return
        
        # Check if the message is a symbol
        if text in self.crypto_pairs + self.forex_pairs + self.indices_pairs + self.metals_pairs:
            # Show pair info
            keyboard = [
                [
                    InlineKeyboardButton("Analyze", callback_data=f"pair_{text}_analyze"),
                    InlineKeyboardButton("View Chart", callback_data=f"pair_{text}_chart")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"Symbol: {text}\n\n"
                f"What would you like to do with {text}?",
                reply_markup=reply_markup
            )
            return
        
        # Check if the message is a symbol and timeframe
        parts = text.split()
        if len(parts) == 2:
            symbol = parts[0].upper()
            timeframe = parts[1].upper()
            
            if symbol in self.crypto_pairs + self.forex_pairs + self.indices_pairs + self.metals_pairs:
                if timeframe in ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"]:
                    # Send "analyzing" message
                    message = await update.message.reply_text(
                        f"Analyzing {symbol} on {timeframe} timeframe... ⏳"
                    )
                    
                    # Perform analysis
                    await self.perform_analysis(update, context, symbol, timeframe, message)
                    return
        
        # Default response for unrecognized messages
        await update.message.reply_text(
            "I didn't understand that. Use /help to see available commands."
        )        
   
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in the Telegram bot"""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
        
        # Send a message to the user
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Sorry, an error occurred while processing your request. Please try again later."
            )

    async def run_async(self):
        """Run the Telegram bot asynchronously"""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Telegram bot started successfully")
