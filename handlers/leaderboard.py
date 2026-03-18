import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import query
from state import check_cooldown

TOTAL_SPECIES = 898

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    rows = query(
        "SELECT p.first_name, COUNT(c.id) as total, "
        "SUM(CASE WHEN c.is_legendary THEN 1 ELSE 0 END) as legendary, "
        "SUM(CASE WHEN c.is_shiny THEN 1 ELSE 0 END) as shiny, "
        "(SELECT COUNT(DISTINCT pokemon_id) FROM collection WHERE user_id = p.user_id) as unique_count "
        "FROM players p LEFT JOIN collection c ON p.user_id = c.user_id "
        "GROUP BY p.user_id, p.first_name ORDER BY total DESC LIMIT 10"
    )
    if not rows:
        await update.message.reply_text("No trainers yet! Be the first! 🎯")
        return

    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text = "╔═══════════════════════╗\n         🏆 *TOP 10 TRAINERS* 🏆\n╚═══════════════════════╝\n\n"

    for i, row in enumerate(rows):
        unique = int(row['unique_count'] or 0)
        percent = round((unique / TOTAL_SPECIES) * 100)
        filled = round((percent / 100) * 10)
        bar = "█" * filled + "░" * (10 - filled)
        text += f"{medals[i]}  *{row['first_name']}*\n┣ 📦 {row['total'] or 0} caught  👑 {row['legendary'] or 0}  ✨ {row['shiny'] or 0}\n┗ 📚 {unique}/{TOTAL_SPECIES}  {bar}  {percent}%\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def groupstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Use this command in a group!")
        return

    text, kb = _build_groupstats(chat.id)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

def _build_groupstats(chat_id):
    now = int(time.time())
    rows = query(
        "SELECT p.first_name, COUNT(c.id) as total, "
        "SUM(CASE WHEN c.is_legendary THEN 1 ELSE 0 END) as legendary, "
        "SUM(CASE WHEN c.is_shiny THEN 1 ELSE 0 END) as shiny, "
        "p.coins, COALESCE(p.streak,0) as streak "
        "FROM players p LEFT JOIN collection c ON p.user_id = c.user_id "
        "GROUP BY p.user_id, p.first_name, p.coins, p.streak ORDER BY total DESC LIMIT 5"
    )
    spawn_rows = query("SELECT name, is_shiny, is_legendary, spawned_at FROM active_spawn WHERE chat_id = %s", [chat_id])
    spawn_info = "🌿 No Pokémon spawned right now"
    if spawn_rows:
        sp = spawn_rows[0]
        tl = 120 - (now - int(sp['spawned_at']))
        if tl > 0:
            tag = "👑" if sp['is_legendary'] else "✨" if sp['is_shiny'] else "🌿"
            spawn_info = f"{tag} *{sp['name'].capitalize()}* is here! ⏱️ {tl}s left!"

    medals = ["🥇","🥈","🥉","4️⃣","5️⃣"]
    text = f"╔═══════════════════╗\n    📊 *GROUP STATS*\n╚═══════════════════╝\n\n🎯 *Active Spawn:*\n{spawn_info}\n\n━━━━━━━━━━━━━━\n🏆 *TOP TRAINERS*\n━━━━━━━━━━━━━━\n\n"
    for i, row in enumerate(rows):
        text += f"{medals[i]} *{row['first_name']}*\n┣ 📦 {row['total'] or 0} caught\n┣ 👑 {row['legendary'] or 0} legendary\n┣ ✨ {row['shiny'] or 0} shiny\n┣ 💰 {row['coins']} coins\n┗ 🔥 {row['streak']} day streak\n\n"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data=f"groupstats_{chat_id}")]])
    return text, kb

async def pokedex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    rows = query("SELECT COUNT(DISTINCT pokemon_id) as unique_count FROM collection WHERE user_id = %s", [user.id])
    unique = int(rows[0]['unique_count']) if rows else 0
    percent = round((unique / TOTAL_SPECIES) * 100)
    filled = round((percent / 100) * 20)
    bar = "█" * filled + "░" * (20 - filled)

    await update.message.reply_text(
        f"╔═══════════════════╗\n    📚 *YOUR POKÉDEX*\n╚═══════════════════╝\n\n"
        f"┣ Unique Species: *{unique}/{TOTAL_SPECIES}*\n"
        f"┗ Completion: *{percent}%*\n\n"
        f"━━━━━━━━━━━━━━\n`{bar}`\n━━━━━━━━━━━━━━\n\n"
        f"{'🏆 *POKÉDEX COMPLETE!*' if percent == 100 else '💡 Keep catching to complete your Pokédex!'}",
        parse_mode="Markdown"
    )
