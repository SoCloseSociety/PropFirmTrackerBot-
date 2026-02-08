#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  PropFirmTracker Bot v1.0
  Real-time prop firm monitoring for traders
═══════════════════════════════════════════════════════════════
  
  Monitors 10+ prop firms for:
  • Rule changes (drawdown, profit targets, scaling)
  • Pricing updates
  • Promo codes & discounts
  • Scam warnings & Trustpilot score drops
  • Reddit community sentiment
  
  Revenue model:
  • Free channel (24h delay) → Premium ($14.99/mo)
  • Referral program (3 friends = 7 days free)
  • Affiliate commissions from prop firm links
  
═══════════════════════════════════════════════════════════════
"""

import asyncio
import sys
import os
import signal

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TELEGRAM_BOT_TOKEN, LOG_LEVEL, LOG_FILE
from utils.logger import setup_logger, log_info, log_error
from database import init_database
from bot import create_bot
from scheduler import Scheduler


# ASCII Art Banner
BANNER = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗ ██████╗  ██████╗ ██████╗     ███████╗██╗██████╗ ║
║   ██╔══██╗██╔══██╗██╔═══██╗██╔══██╗    ██╔════╝██║██╔══██╗║
║   ██████╔╝██████╔╝██║   ██║██████╔╝    █████╗  ██║██████╔╝║
║   ██╔═══╝ ██╔══██╗██║   ██║██╔═══╝     ██╔══╝  ██║██╔══██╗║
║   ██║     ██║  ██║╚██████╔╝██║         ██║     ██║██║  ██║║
║   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝         ╚═╝     ╚═╝╚═╝  ╚═╝║
║          ████████╗██████╗  █████╗  ██████╗██╗  ██╗        ║
║          ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝        ║
║             ██║   ██████╔╝███████║██║     █████╔╝         ║
║             ██║   ██╔══██╗██╔══██║██║     ██╔═██╗         ║
║             ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗        ║
║             ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝        ║
║                                                           ║
║              PropFirmTracker Bot v1.0                      ║
║              Monitoring prop firms 24/7                    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""


def main():
    """Main entry point."""
    print(BANNER)

    # Setup logger
    logger = setup_logger("PropFirmTracker", LOG_LEVEL, LOG_FILE)
    log_info("Starting PropFirmTracker Bot...", tag="STARTUP")

    # Validate config
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log_error("❌ TELEGRAM_BOT_TOKEN not configured!", tag="STARTUP")
        log_error("   1. Create a bot via @BotFather on Telegram", tag="STARTUP")
        log_error("   2. Set TELEGRAM_BOT_TOKEN in .env file", tag="STARTUP")
        sys.exit(1)

    # Initialize database
    log_info("Setting up database...", tag="STARTUP")
    init_database()

    # Create bot
    log_info("Setting up Telegram bot...", tag="STARTUP")
    app = create_bot()

    # Create scheduler
    scheduler = Scheduler(app)

    # Store original post_init from bot.py (registers commands)
    original_post_init = app.post_init

    # Setup scheduler to run alongside bot
    async def on_startup(application):
        """Called when bot starts — register commands + launch scheduler."""
        # Call original post_init first (registers bot commands)
        if original_post_init:
            await original_post_init(application)
        
        scheduler.set_bot(application.bot)
        scheduler.start()
        log_info("═══════════════════════════════════════", tag="STARTUP")
        log_info("🚀 PropFirmTracker Bot is LIVE!", tag="STARTUP")
        log_info("═══════════════════════════════════════", tag="STARTUP")

    async def on_shutdown(application):
        """Called when bot stops — cleanup."""
        scheduler.stop()
        log_info("Bot shutting down...", tag="STARTUP")

    app.post_init = on_startup
    app.post_shutdown = on_shutdown

    # Run the bot
    log_info("Starting polling...", tag="STARTUP")
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
