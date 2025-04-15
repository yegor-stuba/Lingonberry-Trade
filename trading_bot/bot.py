"""
Main Telegram bot implementation
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta, time
import pandas as pd
import io
import pytz

from trading_bot.config import settings, credentials
from trading_bot.data.crypto_data import CryptoDataProvider
from trading_bot.data.forex_data import ForexDataProvider
from trading_bot.analysis.smc import SMCAnalyzer
from trading_bot.analysis.technical import TechnicalAnalyzer
from trading_bot.journal.trade_journal import TradeJournal
from trading_bot.journal.analytics import JournalAnalytics
from trading_bot.risk.management import RiskManager
from trading_bot.utils import helpers, visualization
from trading_bot.services.trade_suggestion import TradeSuggestionService  # Import the new service

logger = logging.getLogger(__name__)

class TradingBot:
    """Main trading bot class"""
    
    def __init__(self):
        """Initialize the trading bot"""
        self.crypto_data = CryptoDataProvider()
        self.forex_data = ForexDataProvider()
        self.smc_analyzer = SMCAnalyzer()
        self.technical_analyzer = TechnicalAnalyzer()
        self.journal = TradeJournal()
        self.analytics = JournalAnalytics(self.journal)
        self.risk_manager = RiskManager(self.journal)
        self.suggestion_service = TradeSuggestionService()  # Add the new service
        
        # User session data
        self.user_data = {}
        
        # Initialize the bot
        self.app = Application.builder().token(credentials.TELEGRAM_TOKEN).build()
        self._setup_handlers()
        
        logger.info("Trading bot initialized")
    
    def _setup_handlers(self):
        """Set up command and callback handlers"""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("setup", self.cmd_setup))
        self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
        self.app.add_handler(CommandHandler("journal", self.cmd_journal))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("scan", self.cmd_scan))
        self.app.add_handler(CommandHandler("backtest", self.cmd_backtest))
        self.app.add_handler(CommandHandler("update_trades", self.cmd_update_trades))

        # Callback query handlers
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started the bot")
        
        # Check if user is already set up
        user_prefs = self.journal.get_user_preferences(user.id)
        
        if user_prefs:
            # User already set up
            await update.message.reply_text(
                f"Welcome back, {user.first_name}! 👋\n\n"
                f"Your account is already set up with:\n"
                f"• Account size: ${user_prefs.get('account_size', 0):,.2f}\n"
                f"• Risk per trade: {user_prefs.get('risk_percentage', 0)}%\n"
                f"• Preferred markets: {', '.join(user_prefs.get('markets', []))}\n\n"
                f"What would you like to do today?\n\n"
                f"• /analyze <symbol> - Analyze a trading pair\n"
                f"• /scan - Scan markets for opportunities\n"
                f"• /journal - View your trade journal\n"
                f"• /stats - View your trading statistics\n"
                f"• /setup - Change your settings\n"
                f"• /help - Show all commands"
            )
        else:
            # New user, start setup
            await update.message.reply_text(
                f"Welcome, {user.first_name}! 👋\n\n"
                f"I'm your Smart Money Concepts trading assistant. I'll help you find high-probability trading setups "
                f"and keep track of your trading performance.\n\n"
                f"Let's start by setting up your account preferences.\n\n"
                f"Please use the /setup command to begin."
            )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🤖 *Trading Bot Commands* 🤖\n\n"
            "*Basic Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/setup - Configure your account settings\n\n"
            
            "*Analysis Commands:*\n"
            "/analyze <symbol> - Analyze a trading pair (e.g., /analyze EURUSD)\n"
            "/scan - Scan markets for trading opportunities\n\n"
            
            "*Journal Commands:*\n"
            "/journal - View your trade journal\n"
            "/stats - View your trading statistics\n\n"
            
            "*Advanced Commands:*\n"
            "/backtest <symbol> - Backtest a strategy on historical data\n\n"
            
            "For more detailed help, visit our documentation or contact support."
        )
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def cmd_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setup command"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started setup")
        
        # Initialize setup state
        self.user_data[user.id] = {
            'setup_state': 'account_size',
            'setup_data': {}
        }
        
        # Ask for account size
        keyboard = [
            [
                InlineKeyboardButton("$1,000", callback_data="setup_account_1000"),
                InlineKeyboardButton("$5,000", callback_data="setup_account_5000"),
                InlineKeyboardButton("$10,000", callback_data="setup_account_10000")
            ],
            [
                InlineKeyboardButton("$25,000", callback_data="setup_account_25000"),
                InlineKeyboardButton("$50,000", callback_data="setup_account_50000"),
                InlineKeyboardButton("$100,000", callback_data="setup_account_100000")
            ],
            [
                InlineKeyboardButton("Custom amount", callback_data="setup_account_custom")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Let's set up your trading preferences.\n\n"
            "First, what is your account size?",
            reply_markup=reply_markup
        )
    
    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) requested analysis")
        
        # Check if symbol was provided
        if not context.args:
            await update.message.reply_text(
                "Please provide a symbol to analyze.\n"
                "Example: /analyze EURUSD"
            )
            return
        
        symbol = context.args[0].upper()
        
        # Check if symbol is supported
        if symbol not in settings.TRADING_PAIRS:
            await update.message.reply_text(
                f"Symbol {symbol} is not supported.\n"
                f"Supported pairs include: {', '.join(settings.TRADING_PAIRS[:10])}..."
            )
            return
        
        # Send loading message
        message = await update.message.reply_text(f"Analyzing {symbol}... This may take a moment.")
        
        try:
            # Determine market type
            market_type = 'crypto' if symbol.endswith('USDT') else 'forex'
            if symbol in settings.INDICES:
                market_type = 'indices'
            elif symbol in settings.METALS:
                market_type = 'metals'
            
            # Get user preferences
            user_prefs = self.journal.get_user_preferences(user.id)
            account_size = user_prefs.get('account_size', settings.DEFAULT_ACCOUNT_SIZE) if user_prefs else settings.DEFAULT_ACCOUNT_SIZE
            risk_percentage = user_prefs.get('risk_percentage', settings.DEFAULT_RISK_PERCENTAGE) if user_prefs else settings.DEFAULT_RISK_PERCENTAGE
            
            # Get current timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Use the trade suggestion service
            suggestion_result = await self.suggestion_service.get_trade_suggestions(
                market_type=market_type,
                symbol=symbol,
                timeframes=settings.ANALYSIS_TIMEFRAMES,
                user_id=user.id,
                account_size=account_size,
                risk_percentage=risk_percentage
            )
            
            if not suggestion_result['success']:
                await message.edit_text(f"Error analyzing {symbol}: {suggestion_result.get('message', 'Unknown error')}")
                return
            
            # Get data for chart creation
            if market_type == 'crypto':
                df = await self.crypto_data.get_ohlcv(symbol, settings.FINAL_TIMEFRAME, 100)
            else:
                df = await self.forex_data.get_ohlcv(symbol, settings.FINAL_TIMEFRAME, 100)
            
            if df is None or df.empty:
                await message.edit_text(f"Could not retrieve data for {symbol}. Please try again later.")
                return
            
            # Get the suggestion
            suggestion = suggestion_result.get('suggestion')
            
            if not suggestion:
                await message.edit_text(f"No trade setup found for {symbol} at this time.")
                return
            
            # Store the suggestion for later use
            if user.id not in self.user_data:
                self.user_data[user.id] = {}
            
            self.user_data[user.id]['current_trade'] = suggestion
            
            # Create chart with trade levels
            chart_buffer = visualization.create_trade_chart(
                df, 
                {
                    'symbol': symbol,
                    'direction': suggestion.get('direction'),
                    'entry_price': suggestion.get('entry_price'),
                    'stop_loss': suggestion.get('stop_loss'),
                    'take_profit': suggestion.get('take_profit')
                },
                timestamp=current_time  # Add timestamp to chart
            )
            
            if not chart_buffer:
                await message.edit_text(f"Error creating chart for {symbol}. Please try again later.")
                return
            
            # Create caption with trade details
            caption = (
                f"📊 *{symbol} Analysis* (as of {current_time})\n\n"
                f"*Trade Setup:* {suggestion.get('setup_type', 'N/A')}\n"
                f"*Direction:* {suggestion.get('direction', 'N/A')}\n"
                f"*Entry:* {suggestion.get('entry_price', 0):.5f}\n"
                f"*Stop Loss:* {suggestion.get('stop_loss', 0):.5f}\n"
                f"*Take Profit:* {suggestion.get('take_profit', 0):.5f}\n"
                f"*Risk-Reward:* {suggestion.get('risk_reward', 0):.2f}\n\n"
                f"*Position Size:* {suggestion.get('position_size', 0):.5f}\n"
                f"*Risk Amount:* ${suggestion.get('risk_amount', 0):.2f} ({suggestion.get('risk_percentage', 0):.2f}%)\n\n"
                f"*Reason:* {suggestion.get('reason', 'N/A')}\n\n"
                f"Would you like to take this trade?"
            )
            
            # Create keyboard for trade actions
            keyboard = [
                [
                    InlineKeyboardButton("✅ Take Trade", callback_data=f"trade_take_{symbol}"),
                    InlineKeyboardButton("❌ Skip", callback_data=f"trade_skip_{symbol}")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Delete loading message
            await message.delete()
            
            # Send chart with caption
            await update.message.reply_photo(
                photo=chart_buffer,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            await message.edit_text(f"Error analyzing {symbol}: {str(e)}")

    
    async def cmd_journal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /journal command"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) requested journal")
        
        # Get recent trades
        trades = self.journal.get_recent_trades(user.id, limit=10)
        
        if not trades:
            await update.message.reply_text(
                "You don't have any recorded trades yet.\n\n"
                "Use /analyze to find and record your first trade!"
            )
            return
        
        # Create journal summary
        journal_text = "📒 *Your Recent Trades*\n\n"
        
        for i, trade in enumerate(trades, 1):
            status = trade.get('status', 'OPEN')
            result = ""
            
            if status == 'WIN':
                result = f"✅ +{trade.get('profit_percentage', 0):.2f}%"
            elif status == 'LOSS':
                result = f"❌ {trade.get('profit_percentage', 0):.2f}%"
            elif status == 'OPEN':
                result = "⏳ OPEN"
            
            journal_text += (
                f"*{i}. {trade.get('symbol')} {trade.get('direction')}*\n"
                f"Entry: {trade.get('entry_price'):.5f} | SL: {trade.get('stop_loss'):.5f} | TP: {trade.get('take_profit'):.5f}\n"
                f"Date: {trade.get('timestamp', '').split('T')[0]} | {result}\n\n"
            )
        
        # Add export options
        keyboard = [
            [
                InlineKeyboardButton("📊 View Statistics", callback_data="journal_stats"),
                InlineKeyboardButton("📥 Export Journal", callback_data="journal_export")
            ],
            [
                InlineKeyboardButton("📝 Add Note to Trade", callback_data="journal_add_note"),
                InlineKeyboardButton("🔍 View Details", callback_data="journal_details")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            journal_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) requested stats")
        
        # Get user statistics
        stats = self.analytics.get_user_statistics(user.id)
        
        if not stats or stats.get('total_trades', 0) == 0:
            await update.message.reply_text(
                "You don't have any completed trades yet.\n\n"
                "Use /analyze to find and record your first trade!"
            )
            return
        
        # Create statistics message
        stats_text = (
            "📊 *Your Trading Statistics*\n\n"
            f"*Overall Performance:*\n"
            f"• Total Trades: {stats.get('total_trades', 0)}\n"
            f"• Win Rate: {stats.get('win_rate', 0):.2f}%\n"
            f"• Profit Factor: {stats.get('profit_factor', 0):.2f}\n"
            f"• Average RR: {stats.get('average_rr', 0):.2f}\n"
            f"• Net Profit: {stats.get('net_profit_percentage', 0):.2f}%\n\n"
            
            f"*Best Trade:*\n"
            f"• {stats.get('best_trade', {}).get('symbol', 'N/A')} {stats.get('best_trade', {}).get('direction', '')}\n"
            f"• Profit: {stats.get('best_trade', {}).get('profit_percentage', 0):.2f}%\n\n"
            
            f"*Worst Trade:*\n"
            f"• {stats.get('worst_trade', {}).get('symbol', 'N/A')} {stats.get('worst_trade', {}).get('direction', '')}\n"
            f"• Loss: {stats.get('worst_trade', {}).get('profit_percentage', 0):.2f}%\n\n"
            
            f"*Current Streak:* {stats.get('current_streak', 0)} {'wins' if stats.get('current_streak', 0) > 0 else 'losses'}\n"
            f"*Best Streak:* {stats.get('best_streak', 0)} wins\n"
            f"*Worst Streak:* {stats.get('worst_streak', 0)} losses\n\n"
            
            f"*Top Pairs:*\n"
        )
        
        # Add top pairs
        top_pairs = stats.get('top_pairs', [])
        for pair in top_pairs[:3]:
            stats_text += f"• {pair['symbol']}: {pair['win_rate']:.2f}% win rate ({pair['count']} trades)\n"
        
        # Create performance chart
        chart_buffer = self.analytics.create_performance_chart(user.id)
        
        # Add export options
        keyboard = [
            [
                InlineKeyboardButton("📈 Detailed Report", callback_data="stats_detailed"),
                InlineKeyboardButton("📅 Weekly Analysis", callback_data="stats_weekly")
            ],
            [
                InlineKeyboardButton("📊 Performance Chart", callback_data="stats_chart"),
                InlineKeyboardButton("📥 Export Statistics", callback_data="stats_export")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send statistics
        await update.message.reply_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Send performance chart if available
        if chart_buffer:
            await update.message.reply_photo(
                photo=chart_buffer,
                caption="📈 Your Trading Performance"
            )
    
    async def cmd_scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /scan command"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) requested market scan")
        
        # Get user preferences
        user_prefs = self.journal.get_user_preferences(user.id)
        
        if not user_prefs:
            await update.message.reply_text(
                "Please set up your account first using the /setup command."
            )
            return
        
        # Get preferred markets
        preferred_markets = user_prefs.get('markets', [])
        
        if not preferred_markets:
            # Default to all markets
            preferred_markets = ['forex', 'crypto', 'indices', 'commodities']
        
        # Send loading message
        message = await update.message.reply_text("Scanning markets for trading opportunities... This may take a moment.")
        
        try:
            # Get pairs to scan based on preferred markets
            pairs_to_scan = []
            
            if 'forex' in preferred_markets:
                pairs_to_scan.extend([p for p in settings.TRADING_PAIRS if any(p.startswith(c) for c in ['EUR', 'GBP', 'USD', 'AUD', 'NZD', 'CAD', 'JPY', 'CHF'])])
            
            if 'crypto' in preferred_markets:
                pairs_to_scan.extend([p for p in settings.TRADING_PAIRS if p.endswith('USDT')])
            
            if 'indices' in preferred_markets:
                pairs_to_scan.extend(['US30', 'SPX500', 'NASDAQ', 'UK100', 'GER40', 'JPN225'])
            
            if 'commodities' in preferred_markets:
                pairs_to_scan.extend(['XAUUSD', 'XAGUSD', 'USOIL', 'UKOIL'])
            
            # Limit to a reasonable number for scanning
            pairs_to_scan = pairs_to_scan[:15]
            
            # Scan for opportunities
            opportunities = []
            
            for symbol in pairs_to_scan:
                try:
                    # Get data
                    if symbol.endswith("USDT"):  # Crypto
                        df = await self.crypto_data.get_ohlcv(symbol, '1h')
                    else:  # Forex or other
                        df = await self.forex_data.get_ohlcv(symbol, '1h')
                    
                    if df is not None and not df.empty:
                        # Perform SMC analysis
                        smc_analysis = self.smc_analyzer.analyze_chart(df, symbol)
                        
                        # Check for trade setups
                        trade_setups = smc_analysis.get('trade_setups', [])
                        
                        if trade_setups:
                            # Get the best setup
                            best_setup = trade_setups[0]
                            
                            # Add to opportunities
                            opportunities.append({
                                'symbol': symbol,
                                'direction': best_setup['type'],
                                'entry_price': best_setup['entry'],
                                'stop_loss': best_setup['stop_loss'],
                                'take_profit': best_setup['take_profit'],
                                'risk_reward': best_setup['risk_reward'],
                                'strength': best_setup['strength'],
                                'reason': best_setup['reason']
                            })
                
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")
                    continue
            
            # Sort opportunities by strength and RR
            opportunities.sort(key=lambda x: (x['strength'], x['risk_reward']), reverse=True)
            
            if opportunities:
                # Create scan results message
                scan_text = "🔍 *Market Scan Results*\n\n"
                
                for i, opp in enumerate(opportunities[:5], 1):
                    scan_text += (
                        f"*{i}. {opp['symbol']} {opp['direction']}*\n"
                        f"Entry: {opp['entry_price']:.5f} | SL: {opp['stop_loss']:.5f} | TP: {opp['take_profit']:.5f}\n"
                        f"RR: {opp['risk_reward']:.2f} | Strength: {opp['strength']:.0f}/100\n\n"
                    )
                
                # Create keyboard for opportunities
                keyboard = []
                
                for i, opp in enumerate(opportunities[:5], 1):
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{i}. Analyze {opp['symbol']} {opp['direction']}",
                            callback_data=f"scan_analyze_{opp['symbol']}"
                        )
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send scan results
                await message.edit_text(
                    scan_text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await message.edit_text(
                    "No high-probability trade setups found at this time.\n\n"
                    "Try again later or use /analyze to check specific pairs."
                )
        
        except Exception as e:
            logger.error(f"Error scanning markets: {e}")
            await message.edit_text(f"Error scanning markets: {str(e)}")
    
    async def cmd_backtest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /backtest command"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) requested backtest")
        
        # Check if symbol was provided
        if not context.args:
            await update.message.reply_text(
                "Please provide a symbol to backtest.\n"
                "Example: /backtest EURUSD"
            )
            return
        
        symbol = context.args[0].upper()
        
        # Check if symbol is supported
        if symbol not in settings.TRADING_PAIRS:
            await update.message.reply_text(
                f"Symbol {symbol} is not supported.\n"
                f"Supported pairs include: {', '.join(settings.TRADING_PAIRS[:10])}..."
            )
            return
        
        # Send loading message
        message = await update.message.reply_text(f"Setting up backtest for {symbol}... This may take a moment.")
        
        # Create keyboard for backtest configuration
        keyboard = [
            [
                InlineKeyboardButton("1 Month", callback_data=f"backtest_period_{symbol}_1m"),
                InlineKeyboardButton("3 Months", callback_data=f"backtest_period_{symbol}_3m"),
                InlineKeyboardButton("6 Months", callback_data=f"backtest_period_{symbol}_6m")
            ],
            [
                InlineKeyboardButton("1 Year", callback_data=f"backtest_period_{symbol}_1y"),
                InlineKeyboardButton("2 Years", callback_data=f"backtest_period_{symbol}_2y"),
                InlineKeyboardButton("Custom", callback_data=f"backtest_period_{symbol}_custom")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.edit_text(
            f"Backtest SMC strategy on {symbol}\n\n"
            f"Please select the backtest period:",
            reply_markup=reply_markup
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        user = query.from_user
        callback_data = query.data
        
        logger.info(f"User {user.id} ({user.username}) callback: {callback_data}")
        
        # Acknowledge the callback query
        await query.answer()
        
        try:
            # Handle setup callbacks
            if callback_data.startswith("setup_account_"):
                await self._handle_setup_account(query, callback_data)
            
            # Handle risk percentage callbacks
            elif callback_data.startswith("setup_risk_"):
                await self._handle_setup_risk(query, callback_data)
            
            # Handle markets callbacks
            elif callback_data.startswith("setup_market_"):
                await self._handle_setup_market(query, callback_data)
            
            # Handle trade callbacks
            elif callback_data.startswith("trade_"):
                await self._handle_trade_action(query, callback_data)
            
            # Handle journal callbacks
            elif callback_data.startswith("journal_"):
                await self._handle_journal_action(query, callback_data)
            
            # Handle stats callbacks
            elif callback_data.startswith("stats_"):
                await self._handle_stats_action(query, callback_data)
            
            # Handle scan callbacks
            elif callback_data.startswith("scan_"):
                await self._handle_scan_action(query, callback_data)
            
            # Handle backtest callbacks
            elif callback_data.startswith("backtest_"):
                await self._handle_backtest_action(query, callback_data)
            
        except Exception as e:
            logger.error(f"Error handling callback {callback_data}: {e}")
            await query.message.reply_text(f"Error processing your request: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user = update.effective_user
        message_text = update.message.text
        
        logger.info(f"User {user.id} ({user.username}) message: {message_text}")
        
        # Check if user is in a specific state
        if user.id in self.user_data:
            user_state = self.user_data[user.id].get('setup_state')
            
            # Handle custom account size input
            if user_state == 'custom_account_size':
                try:
                    # Try to parse the account size
                    account_size = float(message_text.replace('$', '').replace(',', ''))
                    
                    if account_size <= 0:
                        await update.message.reply_text("Please enter a positive number for your account size.")
                        return
                    
                    # Store the account size
                    self.user_data[user.id]['setup_data']['account_size'] = account_size
                    
                    # Move to next step (risk percentage)
                    await self._ask_risk_percentage(update.message)
                    
                except ValueError:
                    await update.message.reply_text(
                        "Invalid account size. Please enter a number (e.g., 10000)."
                    )
            
            # Handle custom risk percentage input
            elif user_state == 'custom_risk_percentage':
                try:
                    # Try to parse the risk percentage
                    risk_percentage = float(message_text.replace('%', ''))
                    
                    if risk_percentage <= 0 or risk_percentage > settings.MAX_RISK_PER_TRADE:
                        await update.message.reply_text(
                            f"Please enter a risk percentage between 0.1% and {settings.MAX_RISK_PER_TRADE}%."
                        )
                        return
                    
                    # Store the risk percentage
                    self.user_data[user.id]['setup_data']['risk_percentage'] = risk_percentage
                    
                    # Move to next step (markets)
                    await self._ask_preferred_markets(update.message)
                    
                except ValueError:
                    await update.message.reply_text(
                        "Invalid risk percentage. Please enter a number (e.g., 1.5)."
                    )
            
            # Handle trade note input
            elif user_state == 'adding_trade_note':
                trade_id = self.user_data[user.id].get('current_trade_id')
                
                if trade_id:
                    # Add note to the trade
                    success = self.journal.add_note_to_trade(user.id, trade_id, message_text)
                    
                    if success:
                        await update.message.reply_text(
                            "✅ Note added to your trade successfully!"
                        )
                    else:
                        await update.message.reply_text(
                            "❌ Failed to add note to your trade. Please try again."
                        )
                    
                    # Clear the state
                    self.user_data[user.id].pop('setup_state', None)
                    self.user_data[user.id].pop('current_trade_id', None)
                else:
                    await update.message.reply_text(
                        "❌ Could not identify which trade to add the note to. Please try again."
                    )
        else:
            # General message handling
            if message_text.lower().startswith(('analyze ', 'check ')):
                # Extract symbol
                parts = message_text.split()
                if len(parts) > 1:
                    symbol = parts[1].upper()
                    
                    # Create context with args
                    context.args = [symbol]
                    
                    # Call analyze command
                    await self.cmd_analyze(update, context)
                else:
                    await update.message.reply_text(
                        "Please specify a symbol to analyze.\n"
                        "Example: analyze EURUSD"
                    )
            else:
                # Default response
                await update.message.reply_text(
                    "I'm not sure what you're asking. Here are some commands you can use:\n\n"
                    "/analyze <symbol> - Analyze a trading pair\n"
                    "/scan - Scan markets for opportunities\n"
                    "/journal - View your trade journal\n"
                    "/stats - View your trading statistics\n"
                    "/help - Show all commands"
                )
    
    async def _handle_setup_account(self, query, callback_data):
        """Handle account size setup callbacks"""
        user = query.from_user
        
        if callback_data == "setup_account_custom":
            # User wants to enter custom account size
            self.user_data[user.id]['setup_state'] = 'custom_account_size'
            
            await query.message.reply_text(
                "Please enter your account size in USD (e.g., 10000):"
            )
        else:
            # Parse the account size from callback data
            account_size = float(callback_data.split('_')[-1])
            
            # Store the account size
            self.user_data[user.id]['setup_data']['account_size'] = account_size
            
            # Move to next step (risk percentage)
            await self._ask_risk_percentage(query.message)
    
    async def _handle_setup_risk(self, query, callback_data):
        """Handle risk percentage setup callbacks"""
        user = query.from_user
        
        if callback_data == "setup_risk_custom":
            # User wants to enter custom risk percentage
            self.user_data[user.id]['setup_state'] = 'custom_risk_percentage'
            
            await query.message.reply_text(
                f"Please enter your risk percentage per trade (0.1-{settings.MAX_RISK_PER_TRADE}%):"
            )
        else:
            # Parse the risk percentage from callback data
            risk_percentage = float(callback_data.split('_')[-1])
            
            # Store the risk percentage
            self.user_data[user.id]['setup_data']['risk_percentage'] = risk_percentage
            
            # Move to next step (markets)
            await self._ask_preferred_markets(query.message)
    
    async def _handle_setup_market(self, query, callback_data):
        """Handle market selection setup callbacks"""
        user = query.from_user
        
        if callback_data == "setup_market_done":
            # User is done selecting markets
            setup_data = self.user_data[user.id]['setup_data']
            
            # Get selected markets
            selected_markets = setup_data.get('markets', ['forex', 'crypto'])
            
            # Create a list of pairs based on selected markets
            pairs = []
            if 'forex' in selected_markets:
                pairs.extend(settings.FOREX_PAIRS)
            if 'crypto' in selected_markets:
                pairs.extend(settings.CRYPTO_PAIRS)
            if 'indices' in selected_markets:
                pairs.extend(settings.INDICES)
            if 'commodities' in selected_markets or 'metals' in selected_markets:
                pairs.extend(settings.METALS)
            
            # Create preferences dictionary
            preferences = {
                'account_size': setup_data.get('account_size', settings.DEFAULT_ACCOUNT_SIZE),
                'risk_percentage': setup_data.get('risk_percentage', settings.DEFAULT_RISK_PERCENTAGE),
                'markets': selected_markets,
                'pairs': pairs[:10] if pairs else []  # Limit to first 10 pairs if any
            }
            
            # Save user preferences
            success = self.journal.save_user_preferences(
                user_id=user.id,
                preferences=preferences
            )
            
            if success:
                await query.message.reply_text(
                    "✅ Setup completed successfully!\n\n"
                    f"• Account size: ${setup_data.get('account_size', 0):,.2f}\n"
                    f"• Risk per trade: {setup_data.get('risk_percentage', 0)}%\n"
                    f"• Preferred markets: {', '.join(selected_markets)}\n\n"
                    f"You're all set to start trading! Use /analyze <symbol> to analyze a trading pair or /scan to find opportunities."
                )
                # Clear setup state
                self.user_data.pop(user.id, None)
            else:
                await query.message.reply_text("❌ Failed to save your preferences. Please try again with /setup.")
        else:
            # Parse the market from callback data
            market = callback_data.split('_')[-1]
            
            # Initialize markets list if not exists
            if 'markets' not in self.user_data[user.id]['setup_data']:
                self.user_data[user.id]['setup_data']['markets'] = []
            
            # Toggle market selection
            markets = self.user_data[user.id]['setup_data']['markets']
            if market in markets:
                markets.remove(market)
            else:
                markets.append(market)
            
            # Delete the previous message to avoid editing it
            await query.message.delete()
            
            # Send a new message with current selections
            await self._update_market_selection(query.message, markets)

    async def _handle_trade_action(self, query, callback_data):
        """Handle trade action callbacks"""
        user = query.from_user
        
        if callback_data.startswith("trade_take_"):
            # User wants to take the trade
            symbol = callback_data.split('_')[-1]
            
            if user.id in self.user_data and 'current_trade' in self.user_data[user.id]:
                trade_data = self.user_data[user.id]['current_trade']
                
                # Add trade to journal
                trade_id = self.journal.add_trade(
                    symbol=trade_data.get('symbol'),
                    direction=trade_data.get('direction'),
                    entry_price=trade_data.get('entry_price'),
                    stop_loss=trade_data.get('stop_loss'),
                    take_profit=trade_data.get('take_profit'),
                    risk_reward=trade_data.get('risk_reward'),
                    position_size=trade_data.get('position_size'),
                    risk_amount=trade_data.get('risk_amount'),
                    risk_percentage=trade_data.get('risk_percentage'),
                    reason=trade_data.get('reason'),
                    user_id=user.id
                )
                
                if trade_id:
                    await query.message.edit_caption(
                        caption=f"✅ Trade recorded for {symbol}!\n\n"
                        f"Direction: {trade_data.get('direction')}\n"
                        f"Entry: {trade_data.get('entry_price'):.5f}\n"
                        f"Stop Loss: {trade_data.get('stop_loss'):.5f}\n"
                        f"Take Profit: {trade_data.get('take_profit'):.5f}\n\n"
                        f"The trade has been added to your journal. You can view it with /journal.",
                        reply_markup=None
                    )
                    
                    # Clear current trade
                    self.user_data[user.id].pop('current_trade', None)
                else:
                    await query.message.edit_caption(
                        caption=f"❌ Failed to record trade for {symbol}. Please try again.",
                        reply_markup=None
                    )
            else:
                await query.message.edit_caption(
                    caption="❌ Trade data not found. Please try analyzing the pair again.",
                    reply_markup=None
                )
        
        elif callback_data.startswith("trade_skip_"):
            # User wants to skip the trade
            symbol = callback_data.split('_')[-1]
            
            await query.message.edit_caption(
                caption=f"Trade for {symbol} skipped. Use /analyze or /scan to find other opportunities.",
                reply_markup=None
            )
            
            # Clear current trade
            if user.id in self.user_data:
                self.user_data[user.id].pop('current_trade', None)
    
    async def _handle_journal_action(self, query, callback_data):
        """Handle journal action callbacks"""
        user = query.from_user
        
        if callback_data == "journal_stats":
            # User wants to view statistics
            await query.message.delete()
            
            # Create context for stats command
            context = ContextTypes.DEFAULT_TYPE.context
            update = Update(0, query.message)
            update.message = query.message
            update.effective_user = user
            
            # Call stats command
            await self.cmd_stats(update, context)
        
        elif callback_data == "journal_export":
            # User wants to export journal
            trades = self.journal.get_all_trades(user.id)
            
            if not trades:
                await query.message.reply_text(
                    "You don't have any recorded trades to export."
                )
                return
            
            # Create CSV export
            csv_buffer = io.StringIO()
            csv_writer = pd.DataFrame(trades).to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            
            # Create document
            document = io.BytesIO(csv_buffer.getvalue().encode())
            document.name = f"trade_journal_{user.id}_{datetime.now().strftime('%Y%m%d')}.csv"
            
            await query.message.reply_document(
                document=document,
                caption="📥 Here's your exported trade journal."
            )
        
        elif callback_data == "journal_add_note":
            # User wants to add a note to a trade
            trades = self.journal.get_recent_trades(user.id, limit=5)
            
            if not trades:
                await query.message.reply_text(
                    "You don't have any recent trades to add notes to."
                )
                return
            
            # Create keyboard for trade selection
            keyboard = []
            
            for i, trade in enumerate(trades, 1):
                status = trade.get('status', 'OPEN')
                result = ""
                
                if status == 'WIN':
                    result = f"✅ +{trade.get('profit_percentage', 0):.2f}%"
                elif status == 'LOSS':
                    result = f"❌ {trade.get('profit_percentage', 0):.2f}%"
                elif status == 'OPEN':
                    result = "⏳ OPEN"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{i}. {trade.get('symbol')} {trade.get('direction')} - {result}",
                        callback_data=f"journal_note_trade_{trade.get('id')}"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                "Select a trade to add a note to:",
                reply_markup=reply_markup
            )
        
        elif callback_data.startswith("journal_note_trade_"):
            # User selected a trade to add a note to
            trade_id = callback_data.split('_')[-1]
            
            # Set state for adding note
            self.user_data[user.id] = {
                'setup_state': 'adding_trade_note',
                'current_trade_id': trade_id
            }
            
            await query.message.edit_text(
                "Please enter your note for this trade:"
            )
        
        elif callback_data == "journal_details":
            # User wants to view detailed journal
            trades = self.journal.get_all_trades(user.id)
            
            if not trades:
                await query.message.reply_text(
                    "You don't have any recorded trades to view."
                )
                return
            
            # Create detailed journal view
            # This would typically be a more comprehensive view with pagination
            # For simplicity, we'll just show a message
            
            await query.message.reply_text(
                "Detailed journal view is coming soon!\n\n"
                "In the meantime, you can export your journal with the 'Export Journal' button."
            )
    
    async def handle_trade_notes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle trade notes from user"""
            user = update.effective_user
            message = update.message
            
            # Check if we're awaiting notes from this user
            if not self.user_data.get(user.id, {}).get('awaiting_notes'):
                return
            
            # Get the current trade and symbol
            current_trade = self.user_data[user.id].get('current_trade')
            symbol = self.user_data[user.id].get('trade_symbol')
            
            if not current_trade or not symbol:
                await message.reply_text("Trade data not found. Please try analyzing again.")
                return
            
            # Get the notes
            notes = message.text
            
            if notes.lower() == 'skip':
                notes = "No notes provided"
            
            # Process the trade acceptance
            success = await self.suggestion_service.process_trade_decision(
                user_id=user.id,
                suggestion=current_trade,
                decision='accept',
                notes=notes
            )
            
            if success:
                # Trade recorded successfully
                await message.reply_text(
                    f"✅ Your {current_trade['direction']} trade on {symbol} has been recorded in your journal.\n\n"
                    f"Entry: {current_trade['entry']:.5f}\n"
                    f"Stop Loss: {current_trade['stop_loss']:.5f}\n"
                    f"Take Profit: {current_trade['take_profit']:.5f}\n"
                    f"Risk-Reward: {current_trade['risk_reward']:.2f}\n\n"
                    f"Use /journal to view your trades."
                )
            else:
                # Error recording trade
                await message.reply_text(
                    f"❌ There was an error recording your trade. Please try again later."
                )
            
            # Clear user data
            if user.id in self.user_data:
                self.user_data.pop(user.id)

    async def _handle_stats_action(self, query, callback_data):
        """Handle statistics action callbacks"""
        user = query.from_user
        
        if callback_data == "stats_detailed":
            # User wants detailed statistics
            stats = self.analytics.get_detailed_statistics(user.id)
            
            if not stats:
                await query.message.reply_text(
                    "Not enough trade data for detailed statistics."
                )
                return
            
            # Create detailed stats message
            detailed_text = (
                "📊 *Detailed Trading Statistics*\n\n"
                
                f"*Performance by Market:*\n"
            )
            
            # Add market performance
            for market in stats.get('markets', []):
                detailed_text += (
                    f"• {market['name']}: {market['win_rate']:.2f}% win rate, "
                    f"{market['profit_percentage']:.2f}% profit\n"
                )
            
            detailed_text += f"\n*Performance by Day:*\n"
            
            # Add day performance
            for day in stats.get('days', []):
                detailed_text += (
                    f"• {day['name']}: {day['win_rate']:.2f}% win rate, "
                    f"{day['profit_percentage']:.2f}% profit\n"
                )
            
            detailed_text += f"\n*Performance by Setup Type:*\n"
            
            # Add setup performance
            for setup in stats.get('setups', []):
                detailed_text += (
                    f"• {setup['name']}: {setup['win_rate']:.2f}% win rate, "
                    f"{setup['profit_percentage']:.2f}% profit\n"
                )
            
            detailed_text += f"\n*Risk Management:*\n"
            detailed_text += (
                f"• Average risk per trade: {stats.get('avg_risk_percentage', 0):.2f}%\n"
                f"• Average reward: {stats.get('avg_reward_percentage', 0):.2f}%\n"
                f"• Average RR ratio: {stats.get('avg_rr', 0):.2f}\n"
                f"• Max drawdown: {stats.get('max_drawdown', 0):.2f}%\n"
            )
            
            await query.message.reply_text(
                detailed_text,
                parse_mode="Markdown"
            )
        
        elif callback_data == "stats_weekly":
            # User wants weekly analysis
            weekly_stats = self.analytics.get_weekly_statistics(user.id)
            
            if not weekly_stats:
                await query.message.reply_text(
                    "Not enough trade data for weekly analysis."
                )
                return
            
            # Create weekly stats message
            weekly_text = "📅 *Weekly Trading Analysis*\n\n"
            
            for week in weekly_stats:
                weekly_text += (
                    f"*Week of {week['start_date']} to {week['end_date']}:*\n"
                    f"• Trades: {week['total_trades']}\n"
                    f"• Win Rate: {week['win_rate']:.2f}%\n"
                    f"• Profit: {week['profit_percentage']:.2f}%\n"
                    f"• Best Trade: {week['best_trade']['symbol']} ({week['best_trade']['profit_percentage']:.2f}%)\n\n"
                )
            
            await query.message.reply_text(
                weekly_text,
                parse_mode="Markdown"
            )
        
        elif callback_data == "stats_chart":
            # User wants performance chart
            chart_buffer = self.analytics.create_performance_chart(user.id)
            
            if chart_buffer:
                await query.message.reply_photo(
                    photo=chart_buffer,
                    caption="📈 Your Trading Performance"
                )
            else:
                await query.message.reply_text(
                    "Could not generate performance chart. Not enough trade data."
                )
        
        elif callback_data == "stats_export":
            # User wants to export statistics
            stats = self.analytics.get_user_statistics(user.id)
            detailed_stats = self.analytics.get_detailed_statistics(user.id)
            
            if not stats:
                await query.message.reply_text(
                    "You don't have enough completed trades for statistics export."
                )
                return
            
            # Combine stats
            all_stats = {**stats}
            if detailed_stats:
                all_stats.update(detailed_stats)
            
            # Create JSON export
            json_buffer = io.StringIO()
            pd.Series(all_stats).to_json(json_buffer)
            json_buffer.seek(0)
            
            # Create document
            document = io.BytesIO(json_buffer.getvalue().encode())
            document.name = f"trading_stats_{user.id}_{datetime.now().strftime('%Y%m%d')}.json"
            
            await query.message.reply_document(
                document=document,
                caption="📊 Here are your exported trading statistics."
            )
    
    async def _handle_scan_action(self, query, callback_data):
        """Handle scan action callbacks"""
        user = query.from_user
        
        if callback_data.startswith("scan_analyze_"):
            # User wants to analyze a pair from scan results
            symbol = callback_data.split('_')[-1]
            
            # Create context for analyze command
            context = ContextTypes.DEFAULT_TYPE.context
            context.args = [symbol]
            
            update = Update(0, query.message)
            update.message = query.message
            update.effective_user = user
            
            # Call analyze command
            await self.cmd_analyze(update, context)
        
    async def _handle_backtest_action(self, query, callback_data):
        """Handle backtest action callbacks"""
        user = query.from_user
        
        if callback_data.startswith("backtest_period_"):
            # Parse symbol and period
            parts = callback_data.split('_')
            symbol = parts[2]
            period = parts[3]
            
            if period == "custom":
                # User wants to enter custom period
                # This would typically open a dialog for date selection
                # For simplicity, we'll just use a default period
                await query.message.edit_text("Custom period selection is coming soon!\n\n"
                                            "In the meantime, we'll use the default 1-year period.")
                # Set period to default
                period = "1y"
            
            # Send loading message
            await query.message.edit_text(f"Running backtest for {symbol} over {period} period... This may take a while.")
            
            try:
                # Get current timestamp
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Get historical data
                if symbol.endswith("USDT"):  # Crypto
                    df = await self.crypto_data.get_historical_data(symbol, period)
                else:  # Forex or other
                    df = await self.forex_data.get_historical_data(symbol, period)
                
                if df is None or df.empty:
                    await query.message.edit_text(f"Could not retrieve historical data for {symbol}. Please try again later.")
                    return
                
                # Run backtest
                backtest_results = self.smc_analyzer.backtest(df, symbol)
                
                if not backtest_results:
                    await query.message.edit_text(f"No valid backtest results for {symbol}. Try a different period or symbol.")
                    return
                
                # Create backtest summary
                summary_text = (
                    f"📊 *Backtest Results: {symbol} ({period})* - Run at {current_time}\n\n"
                    f"*Performance:*\n"
                    f"• Total Trades: {backtest_results.get('total_trades', 0)}\n"
                    f"• Win Rate: {backtest_results.get('win_rate', 0):.2f}%\n"
                    f"• Profit Factor: {backtest_results.get('profit_factor', 0):.2f}\n"
                    f"• Net Profit: {backtest_results.get('net_profit_percentage', 0):.2f}%\n"
                    f"• Max Drawdown: {backtest_results.get('max_drawdown', 0):.2f}%\n\n"
                    f"*Trade Breakdown:*\n"
                    f"• Long Trades: {backtest_results.get('long_trades', 0)} "
                    f"({backtest_results.get('long_win_rate', 0):.2f}% win rate)\n"
                    f"• Short Trades: {backtest_results.get('short_trades', 0)} "
                    f"({backtest_results.get('short_win_rate', 0):.2f}% win rate)\n\n"
                    f"*Best Trade:* {backtest_results.get('best_trade', {}).get('profit_percentage', 0):.2f}%\n"
                    f"*Worst Trade:* {backtest_results.get('worst_trade', {}).get('profit_percentage', 0):.2f}%\n"
                )
                
                # Create equity curve chart
                chart_buffer = visualization.create_equity_curve(
                    backtest_results.get('equity_curve', []),
                    symbol,
                    period,
                    timestamp=current_time  # Add timestamp to chart
                )
                
                # Send backtest results
                await query.message.edit_text(summary_text, parse_mode="Markdown")
                
                if chart_buffer:
                    await query.message.reply_photo(
                        photo=chart_buffer,
                        caption=f"📈 Equity Curve: {symbol} ({period}) - {current_time}"
                    )
                
                # Create trade distribution chart
                trade_chart = visualization.create_trade_distribution(
                    backtest_results.get('trades', []),
                    symbol,
                    timestamp=current_time  # Add timestamp to chart
                )
                
                if trade_chart:
                    await query.message.reply_photo(
                        photo=trade_chart,
                        caption=f"📊 Trade Distribution: {symbol} ({period}) - {current_time}"
                    )
                
                # Offer to save the strategy
                keyboard = [
                    [
                        InlineKeyboardButton("💾 Save Strategy", callback_data=f"backtest_save_{symbol}"),
                        InlineKeyboardButton("📋 View Trades", callback_data=f"backtest_trades_{symbol}")
                    ],
                    [
                        InlineKeyboardButton("🔄 Try Different Period", callback_data=f"backtest_retry_{symbol}"),
                        InlineKeyboardButton("📤 Export Results", callback_data=f"backtest_export_{symbol}")
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(
                    "What would you like to do with these backtest results?",
                    reply_markup=reply_markup
                )
                
            except Exception as e:
                logger.error(f"Error running backtest for {symbol}: {e}")
                await query.message.edit_text(f"Error running backtest for {symbol}: {str(e)}")


    
    async def _ask_risk_percentage(self, message):
        """Ask user for risk percentage"""
        user_id = message.chat.id
        self.user_data[user_id]['setup_state'] = 'risk_percentage'
        
        keyboard = [
            [
                InlineKeyboardButton("0.5%", callback_data="setup_risk_0.5"),
                InlineKeyboardButton("1%", callback_data="setup_risk_1"),
                InlineKeyboardButton("2%", callback_data="setup_risk_2")
            ],
            [
                InlineKeyboardButton("3%", callback_data="setup_risk_3"),
                InlineKeyboardButton("5%", callback_data="setup_risk_5"),
                InlineKeyboardButton("Custom", callback_data="setup_risk_custom")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "What percentage of your account would you like to risk per trade?",
            reply_markup=reply_markup
        )
    
    async def _ask_preferred_markets(self, message):
        """Ask user for preferred markets"""
        user_id = message.chat.id
        self.user_data[user_id]['setup_state'] = 'markets'
        
        # Initialize empty markets list
        if 'markets' not in self.user_data[user_id]['setup_data']:
            self.user_data[user_id]['setup_data']['markets'] = []
        
        await self._update_market_selection(message, [])
    
    async def _update_market_selection(self, message, selected_markets):
        """Update market selection message"""
        # Create keyboard with current selections
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Forex" if "forex" in selected_markets else "Forex",
                    callback_data="setup_market_forex"
                ),
                InlineKeyboardButton(
                    "✅ Crypto" if "crypto" in selected_markets else "Crypto",
                    callback_data="setup_market_crypto"
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Indices" if "indices" in selected_markets else "Indices",
                    callback_data="setup_market_indices"
                ),
                InlineKeyboardButton(
                    "✅ Commodities" if "commodities" in selected_markets else "Commodities",
                    callback_data="setup_market_commodities"
                )
            ],
            [
                InlineKeyboardButton("Done", callback_data="setup_market_done")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "Which markets would you like to trade? (Select all that apply)",
            reply_markup=reply_markup
        )
    
    def _schedule_daily_updates(self):
        """Schedule daily trade status updates"""
        # Parse the update time from settings
        update_time_str = settings.JOURNAL_UPDATE_TIME
        try:
            update_hour, update_minute = map(int, update_time_str.split(':'))
            
            # Create a job to run daily at the specified time
            job_queue = self.app.job_queue
            
            # Set timezone to GMT+1
            target_tz = pytz.timezone('Europe/London')
            
            # Schedule the job
            job_queue.run_daily(
                self._run_daily_trade_updates,
                time=time(hour=update_hour, minute=update_minute),
                days=(0, 1, 2, 3, 4, 5, 6),  # Run every day
                timezone=target_tz
            )
            
            logger.info(f"Scheduled daily trade updates for {update_time_str} GMT+1")
            
        except Exception as e:
            logger.error(f"Error scheduling daily updates: {e}")
    
    async def _run_daily_trade_updates(self, context: ContextTypes.DEFAULT_TYPE):
        """Run daily trade status updates"""
        logger.info("Running daily trade status updates")
        
        try:
            # Update trade statuses
            result = await self.suggestion_service.update_trade_statuses()
            
            if result['success']:
                logger.info(f"Daily trade update completed: {result['message']}")
                
                # If trades were updated, notify admin
                if result['updated'] > 0:
                    admin_id = settings.ADMIN_USER_ID
                    if admin_id:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=f"📊 *Daily Trade Update*\n\n"
                                 f"• Updated: {result['updated']} trades\n"
                                 f"• Errors: {result['errors']}\n\n"
                                 f"Use /journal to view your updated trades.",
                            parse_mode="Markdown"
                        )
                
                # Notify users with updated trades
                updated_trades = self.journal.get_recently_updated_trades()
                user_notifications = {}
                
                for trade in updated_trades:
                    user_id = trade.get('user_id')
                    if user_id not in user_notifications:
                        user_notifications[user_id] = []
                    
                    user_notifications[user_id].append(trade)
                
                # Send notifications to each user
                for user_id, trades in user_notifications.items():
                    try:
                        # Create notification message
                        message = "🔄 *Trade Updates*\n\n"
                        
                        for trade in trades:
                            symbol = trade.get('symbol', '')
                            direction = trade.get('direction', '')
                            status = trade.get('status', '')
                            profit = trade.get('profit_percentage', 0)
                            
                            status_emoji = "✅" if status == "WIN" else "❌" if status == "LOSS" else "⏳"
                            profit_text = f"+{profit:.2f}%" if profit > 0 else f"{profit:.2f}%"
                            
                            message += f"{status_emoji} {symbol} {direction}: {status} ({profit_text})\n"
                        
                        message += "\nUse /journal to view your complete trade history."
                        
                        # Send message to user
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode="Markdown"
                        )
                        
                    except Exception as e:
                        logger.error(f"Error sending notification to user {user_id}: {e}")
            
            else:
                logger.error(f"Daily trade update failed: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in daily trade updates: {e}")
    
    async def cmd_update_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /update_trades command (admin only)"""
        user = update.effective_user
        
        # Check if user is admin
        if user.id != settings.ADMIN_USER_ID:
            await update.message.reply_text("This command is only available to administrators.")
            return
        
        # Send loading message
        message = await update.message.reply_text("Updating trade statuses... This may take a moment.")
        
        try:
            # Update trade statuses
            result = await self.suggestion_service.update_trade_statuses()
            
            if result['success']:
                await message.edit_text(
                    f"✅ Trade update completed!\n\n"
                    f"• Updated: {result['updated']} trades\n"
                    f"• Errors: {result['errors']}\n\n"
                    f"{result['message']}"
                )
            else:
                await message.edit_text(
                    f"❌ Trade update failed: {result['message']}"
                )
                
        except Exception as e:
            logger.error(f"Error updating trades: {e}")
            await message.edit_text(f"Error updating trades: {str(e)}")

    async def error_handler(self, update, context):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        # Send error message to user
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "An error occurred while processing your request. Please try again later."
            )
    
    def run(self):
        """Run the bot"""
        logger.info("Starting the trading bot")
        self.app.run_polling()


if __name__ == "__main__":
    bot = TradingBot()
    bot.run()



