from setuptools import setup, find_packages

setup(
    name="trading_bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot",
        "pandas",
        "numpy",
        "matplotlib",
        "mplfinance",
        "python-dotenv",
        "pytz",
        "ccxt",
        "yfinance",
        "ctrader-open-api",
        "websocket-client",
        "aiohttp",
        "twisted",
        "scikit-learn",
        "transformers",
    ],
    author="Yegor",
    author_email="your.email@example.com",
    description="A trading bot using SMC and ICT methodologies",
)
