import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)
from config import BOT_TOKEN

from handlers.start import start
from handlers.profile import profile
from handlers.daily import daily
from handlers.shop import shop, buy
from handlers.guess import guess
from handlers.walk import walk
from handlers.collection import collection
from handlers.search import search
from handlers.release import release
from handlers.trade import trade
from handlers.leaderboard import leaderboard, groupstats, pokedex
from handlers.misc import help_cmd, ping, changename, cancel, promo, broadcast
from handlers.admin import addpromo, give, addcoins, removecoins, spawn_cmd
from handlers.callbacks import callback_handler
from handlers.wildcard import message_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ── User Commands ──
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("guess", guess))
    app.add_handler(CommandHandler("walk", walk))
    app.add_handler(CommandHandler("collection", collection))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("release", release))
    app.add_handler(CommandHandler("trade", trade))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("groupstats", groupstats))
    app.add_handler(CommandHandler("pokedex", pokedex))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("changename", changename))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("promo", promo))

    # ── Owner Commands ──
    app.add_handler(CommandHandler("addpromo", addpromo))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("give", give))
    app.add_handler(CommandHandler("addcoins", addcoins))
    app.add_handler(CommandHandler("removecoins", removecoins))
    app.add_handler(CommandHandler("spawn", spawn_cmd))

    # ── Callbacks + Messages ──
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("🚀 ShadowDex Bot starting on Render...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
