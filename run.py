from trading_bot.ui.telegram_bot import TelegramBot

# Initialize and run the bot
bot = TelegramBot()
bot.application.run_polling()
