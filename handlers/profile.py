from telegram import Update
from telegram.ext import ContextTypes
from db import query
from state import check_cooldown

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    rows = query("SELECT * FROM players WHERE user_id = %s", [user.id])
    if not rows:
        await update.message.reply_text(f"❌ *{user.first_name}* you are not registered yet!\n\n👉 Start the bot in private first!", parse_mode="Markdown")
        return

    p = rows[0]
    stats = query(
        "SELECT COUNT(*) as total, "
        "SUM(CASE WHEN is_legendary THEN 1 ELSE 0 END) as legendary, "
        "SUM(CASE WHEN is_pseudo THEN 1 ELSE 0 END) as pseudo, "
        "SUM(CASE WHEN is_shiny THEN 1 ELSE 0 END) as shiny, "
        "SUM(CASE WHEN NOT is_legendary AND NOT is_pseudo AND NOT is_shiny THEN 1 ELSE 0 END) as normal "
        "FROM collection WHERE user_id = %s", [user.id]
    )
    s = stats[0] if stats else {}

    await update.message.reply_text(
        f"╔═══════════════════╗\n      🎮 *TRAINER CARD*\n╚═══════════════════╝\n\n"
        f"👤 *{p['first_name']}*\n🆔 ID: `{user.id}`\n\n"
        f"━━━━━━━━━━━━━━\n💰 *ECONOMY*\n┗ Pokédollars: *{p['coins']}*\n\n"
        f"🎒 *BALLS INVENTORY*\n"
        f"┣ 🔴 Poké Ball: *{p['pokeball']}*\n"
        f"┣ 🔵 Great Ball: *{p['greatball']}*\n"
        f"┣ 🟡 Ultra Ball: *{p['ultraball']}*\n"
        f"┗ ⚫ Master Ball: *{p['masterball']}*\n\n"
        f"━━━━━━━━━━━━━━\n📦 *POKÉMON CAUGHT*\n"
        f"┣ Total: *{s.get('total',0)}*\n"
        f"┣ 👑 Legendary: *{s.get('legendary',0)}*\n"
        f"┣ 🔮 Pseudo: *{s.get('pseudo',0)}*\n"
        f"┣ ✨ Shiny: *{s.get('shiny',0)}*\n"
        f"┗ 🟢 Normal: *{s.get('normal',0)}*",
        parse_mode="Markdown"
    )
