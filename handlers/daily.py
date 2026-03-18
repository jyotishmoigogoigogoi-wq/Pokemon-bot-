import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import query

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    now = int(time.time())
    ONE_DAY, TWO_DAYS = 86400, 172800

    rows = query("SELECT coins, daily_last_claimed, COALESCE(streak,0) as streak, COALESCE(streak_last_day,0) as streak_last_day FROM players WHERE user_id = %s", [user.id])
    if not rows:
        await update.message.reply_text("❌ You are not registered!\n\n👉 Start the bot in private first!", parse_mode="Markdown")
        return

    p = rows[0]
    last_claimed = int(p['daily_last_claimed'] or 0)
    diff = now - last_claimed

    if diff < ONE_DAY:
        remaining = ONE_DAY - diff
        hrs, mins, secs = remaining//3600, (remaining%3600)//60, remaining%60
        await update.message.reply_text(
            f"╔═══════════════════╗\n      ⏳ *DAILY REWARD*\n╚═══════════════════╝\n\n❌ Already claimed today!\n\n┣ ⏰ Come back in:\n┗ *{hrs}h {mins}m {secs}s*\n\n🔥 Current Streak: *{p['streak']} days*",
            parse_mode="Markdown"
        )
        return

    streak = int(p['streak'] or 0)
    last_day = int(p['streak_last_day'] or 0)
    new_streak = streak + 1 if last_day > 0 and (now - last_day) < TWO_DAYS else 1

    if new_streak >= 30: bonus, bonus_text = 1000, "🏆 *30 DAY STREAK BONUS!* +1000"
    elif new_streak >= 14: bonus, bonus_text = 500, "💎 *14 DAY STREAK BONUS!* +500"
    elif new_streak >= 7: bonus, bonus_text = 300, "🔥 *7 DAY STREAK BONUS!* +300"
    elif new_streak >= 3: bonus, bonus_text = 150, "⚡ *3 DAY STREAK BONUS!* +150"
    else: bonus, bonus_text = 100, "💰 *Daily Reward* +100"

    query("UPDATE players SET coins = coins + %s, daily_last_claimed = %s, streak = %s, streak_last_day = %s WHERE user_id = %s",
          [bonus, now, new_streak, now, user.id])

    new_balance = int(p['coins']) + bonus
    streak_emoji = "👑" if new_streak >= 30 else "💎" if new_streak >= 14 else "🔥" if new_streak >= 7 else "⚡" if new_streak >= 3 else "🌱"

    if new_streak < 3: next_m = f"⚡ {3-new_streak} days to 3-day bonus!"
    elif new_streak < 7: next_m = f"🔥 {7-new_streak} days to 7-day bonus!"
    elif new_streak < 14: next_m = f"💎 {14-new_streak} days to 14-day bonus!"
    elif new_streak < 30: next_m = f"👑 {30-new_streak} days to 30-day bonus!"
    else: next_m = "👑 MAX STREAK ACHIEVED!"

    broken = f"💔 *Streak reset!* Was {streak} days\n\n" if new_streak == 1 and streak > 1 else ""

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💰 Check Profile", callback_data="check_profile"), InlineKeyboardButton("🛒 Go Shop", callback_data="open_shop")]])
    await update.message.reply_text(
        f"╔═══════════════════╗\n    ✅ *DAILY CLAIMED!*\n╚═══════════════════╝\n\n{broken}{bonus_text}\n\n━━━━━━━━━━━━━━\n{streak_emoji} Streak: *{new_streak} days*\n💰 Balance: *{new_balance}* Pokédollars\n━━━━━━━━━━━━━━\n\n📈 {next_m}",
        parse_mode="Markdown", reply_markup=kb
    )
