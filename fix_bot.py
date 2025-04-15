#!/usr/bin/env python3

import os
import re

# Path to the bot.py file
bot_file = 'trading_bot/bot.py'

# Read the file
with open(bot_file, 'r') as f:
    content = f.read()

# Fix the _ask_risk_percentage function
fixed_content = re.sub(
    r'async def _ask_risk_percentage\(self, message\):.*?await message\.edit_text\(',
    'async def _ask_risk_percentage(self, message):\n    """Ask user for risk percentage"""\n    user_id = message.chat.id\n    self.user_data[user_id][\'setup_state\'] = \'risk_percentage\'\n    \n    keyboard = [\n        [\n            InlineKeyboardButton("0.5%", callback_data="setup_risk_0.5"),\n            InlineKeyboardButton("1%", callback_data="setup_risk_1"),\n            InlineKeyboardButton("2%", callback_data="setup_risk_2")\n        ],\n        [\n            InlineKeyboardButton("3%", callback_data="setup_risk_3"),\n            InlineKeyboardButton("5%", callback_data="setup_risk_5"),\n            InlineKeyboardButton("Custom", callback_data="setup_risk_custom")\n        ]\n    ]\n    \n    reply_markup = InlineKeyboardMarkup(keyboard)\n    \n    await message.reply_text(',
    content,
    flags=re.DOTALL
)

# Fix the _ask_preferred_markets function
fixed_content = re.sub(
    r'async def _ask_preferred_markets\(self, message\):.*?await self\._update_market_selection\(message, \[\]\)',
    'async def _ask_preferred_markets(self, message):\n    """Ask user for preferred markets"""\n    user_id = message.chat.id\n    self.user_data[user_id][\'setup_state\'] = \'markets\'\n    \n    # Initialize empty markets list\n    if \'markets\' not in self.user_data[user_id][\'setup_data\']:\n        self.user_data[user_id][\'setup_data\'][\'markets\'] = []\n    \n    await self._update_market_selection(message, [])',
    fixed_content,
    flags=re.DOTALL
)

# Fix the _update_market_selection function
fixed_content = re.sub(
    r'async def _update_market_selection\(self, message, selected_markets\):.*?await message\.edit_text\(',
    'async def _update_market_selection(self, message, selected_markets):\n    """Update market selection message"""\n    # Create keyboard with current selections\n    keyboard = [\n        [\n            InlineKeyboardButton(\n                "✅ Forex" if "forex" in selected_markets else "Forex",\n                callback_data="setup_market_forex"\n            ),\n            InlineKeyboardButton(\n                "✅ Crypto" if "crypto" in selected_markets else "Crypto",\n                callback_data="setup_market_crypto"\n            )\n        ],\n        [\n            InlineKeyboardButton(\n                "✅ Indices" if "indices" in selected_markets else "Indices",\n                callback_data="setup_market_indices"\n            ),\n            InlineKeyboardButton(\n                "✅ Commodities" if "commodities" in selected_markets else "Commodities",\n                callback_data="setup_market_commodities"\n            )\n        ],\n        [\n            InlineKeyboardButton("Done", callback_data="setup_market_done")\n        ]\n    ]\n    \n    reply_markup = InlineKeyboardMarkup(keyboard)\n    \n    await message.reply_text(',
    fixed_content,
    flags=re.DOTALL
)

# Write the fixed content back to the file
with open(bot_file, 'w') as f:
    f.write(fixed_content)

print("Fixed the bot.py file. The bot should now handle custom account size input correctly.")
