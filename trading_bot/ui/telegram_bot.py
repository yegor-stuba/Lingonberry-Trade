"""
Telegram bot interface for the trading bot
"""

import logging
import asyncio
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
        self.dashboard_url = dashboard_url if dashboard_url else DASHBOARD_URL
        
        # Register handlers
        self.register_handlers()
        
    def register_handlers(self):
        """Register command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
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
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        await update.message.reply_text(
            "Welcome to the Trading Bot! 📈\n\n"
            "This bot analyzes markets using Smart Money Concepts and ICT methodologies.\n\n"
            "Use /help to see available commands."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        help_text = (
            "Available commands:\n\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/analyze - Analyze a trading pair\n"
            "/pairs - Show available trading pairs\n"
            "/timeframes - Show available timeframes\n"
            "/chart - View interactive TradingView chart\n\n"
            "/journal - View trading journal\n\n"
            "Examples:\n"
            "/analyze BTCUSDT H1\n"
            "/analyze EURUSD H4\n"
            "/chart XAUUSD\n"
        )
        await update.message.reply_text(help_text)
    
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
        # Get recent trades
        closed_trades = self.trade_journal.get_closed_trades()
        active_trades = self.trade_journal.get_active_trades()
        pending_trades = self.trade_journal.get_pending_trades()
        
        # Calculate performance metrics
        metrics = self.trade_journal.calculate_performance_metrics()
        
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
                outcome_emoji = "✅" if trade["outcome"] == "win" else "❌"
                message += (
                    f"{outcome_emoji} {trade['symbol']} {trade['direction']} "
                    f"({trade['profit_loss']:.2f})\n"
                )
        else:
            message += "*No closed trades yet.*\n"
        
        if active_trades:
            message += "\n*Active Trades:*\n"
            for trade in active_trades[-3:]:  # Show last 3 active trades
                message += (
                    f"⏳ {trade['symbol']} {trade['direction']} "
                    f"Entry: {trade['entry_price']:.5f}\n"
                )
        
        if pending_trades:
            message += "\n*Pending Trades:*\n"
            for trade in pending_trades[-3:]:  # Show last 3 pending trades
                message += (
                    f"⏱️ {trade['symbol']} {trade['direction']} "
                    f"Entry: {trade['entry_price']:.5f}\n"
                )
        
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
        
        # Add Telegram Web App button for journal - make sure URL is properly formatted
        journal_url = f"{self.dashboard_url}/telegram_journal"
        # Remove any trailing slashes from dashboard_url before adding the path
        if self.dashboard_url.endswith('/'):
            journal_url = f"{self.dashboard_url[:-1]}/telegram_journal"
        
        # Add parameters to bypass ngrok warning
        if "ngrok" in journal_url:
            journal_url += "?ngrok-skip-browser-warning=true"
        
        # Only add the web app button if we have a valid URL (not localhost)
        if not "localhost" in self.dashboard_url and not "127.0.0.1" in self.dashboard_url:
            keyboard.append([
                InlineKeyboardButton("Open Journal 📊", web_app=WebAppInfo(url=journal_url))
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
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
            # Record the trade
            trade_id = self.trade_journal.record_trade(trade_data)
            
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
                
            # Get data
            df = await self.data_processor.get_data(symbol, timeframe, bars=self.default_bars, source=source)
            
            if df is None or df.empty:
                await message.edit_text(f"❌ Error: No data available for {symbol} on {timeframe} timeframe.")
                return
                
            # Generate signals
            signals = self.signal_generator.generate_signals(symbol, df, timeframe)
            
            # Filter signals
            filtered_signals = self.signal_generator.filter_signals(signals)
            
            # Get the best signal
            best_signal = self.signal_generator.get_best_signal(filtered_signals)
            
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
            if best_signal:
                # Get trade setup
                trade_setup = self.signal_generator.get_trade_setup(best_signal)
                
                # Add timeframe to trade setup
                trade_setup['timeframe'] = timeframe

                # Store in user data for later reference
                context.user_data["current_trade_setup"] = trade_setup
                
                # Create chart with trade setup
                chart_buffer = create_trade_chart(
                    df,
                    trade_setup,
                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                
                # Create keyboard with accept/reject buttons
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
                
                if chart_buffer:
                    # If we have a chart, send it as a photo
                    await message.delete()
                    await update.message.reply_photo(
                        photo=chart_buffer,
                        caption=self._format_trade_setup(trade_setup),
                        reply_markup=reply_markup
                    )
                else:
                    # If chart creation failed, still show the trade setup with buttons
                    logger.warning(f"Failed to create chart for {symbol} trade setup, showing text only")
                    await message.edit_text(
                        self._format_trade_setup(trade_setup) + 
                        "\n\nNo chart available, but you can still decide on this trade:",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                return
                
            elif filtered_signals:
                # Send analysis with signals info
                await message.edit_text(
                    f"Analysis for {symbol} on {timeframe} timeframe.\n\n"
                    f"Found {len(filtered_signals)} potential signals, but none meet the criteria for a trade setup.\n\n"
                    f"Click the button below to view the chart.",
                    reply_markup=reply_markup
                )
            else:
                # Send analysis with no signals
                await message.edit_text(
                    f"Analysis for {symbol} on {timeframe} timeframe.\n\n"
                    f"No trading signals found at this time.\n\n"
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
        
        elif callback_data.startswith("analyze_"):
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

        # Handle trade decisions
        elif callback_data.startswith("trade_"):
            await self.handle_trade_decision(update, context)
        elif callback_data == "journal":
            # For callback queries, we need to send a new message instead of replying
            # to the original message (which doesn't exist in this context)
            await self.journal_command(update, context)
        elif callback_data.startswith("modify_"):
            await self.handle_trade_modification(update, context)
    
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
            action = parts[1]  # entry, sl, tp, or cancel
            
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
            
            # For entry, sl, tp - we need to prompt for a new value
            # Store the current modification type in user data
            context.user_data["modification_type"] = action
            
            # Create a message asking for the new value
            if action == "entry":
                message = f"Please enter the new entry price for {trade_data['symbol']} {trade_data['direction']}:"
            elif action == "sl":
                message = f"Please enter the new stop loss price for {trade_data['symbol']} {trade_data['direction']}:"
            elif action == "tp":
                message = f"Please enter the new take profit price for {trade_data['symbol']} {trade_data['direction']}:"
            
            # Add a cancel button
            keyboard = [[InlineKeyboardButton("Cancel", callback_data="modify_cancel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Edit the message to ask for the new value
            await query.edit_message_text(
                message,
                reply_markup=reply_markup
            )
            
            # Set a flag in user data to indicate we're waiting for a modification value
            context.user_data["awaiting_modification"] = True
    
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
        """Format trade setup for display with improved number formatting"""
        direction = trade_setup.get('direction', 'UNKNOWN')
        entry_price = trade_setup.get('entry_price', 0)
        stop_loss = trade_setup.get('stop_loss', 0)
        take_profit = trade_setup.get('take_profit', 0)
        risk_reward = trade_setup.get('risk_reward', 0)
        reason = trade_setup.get('reason', 'No reason provided')
        symbol = trade_setup.get('symbol', 'Unknown')
        timeframe = trade_setup.get('timeframe', 'Unknown')
        
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
        
        # Format the message with properly formatted numbers
        message = (
            f"📊 *Trade Setup: {direction}*\n\n"
            f"Symbol: {symbol}\n"
            f"Timeframe: {timeframe}\n\n"
            f"Entry: {price_format.format(entry_price)}\n"
            f"Stop Loss: {price_format.format(stop_loss)}\n"
            f"Take Profit: {price_format.format(take_profit)}\n\n"
            f"Risk: {price_format.format(risk_points)} points\n"
            f"Risk/Reward: {risk_reward:.2f}\n\n"
            f"Analysis:\n{reason}"
        )
        

        return message    
   
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
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
    
    def run(self):
        """Run the bot"""
        logger.info("Starting Telegram bot...")
        self.application.run_polling()


