from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import query
from state import check_cooldown

SHOP = {
    "pokeball":   {"price": 50,   "col": "pokeball",   "emoji": "🔴", "name": "Poké Ball",   "img": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png"},
    "greatball":  {"price": 150,  "col": "greatball",  "emoji": "🔵", "name": "Great Ball",  "img": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/great-ball.png"},
    "ultraball":  {"price": 300,  "col": "ultraball",  "emoji": "🟡", "name": "Ultra Ball",  "img": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/ultra-ball.png"},
    "masterball": {"price": 5000, "col": "masterball", "emoji": "⚫", "name": "Master Ball", "img": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/master-ball.png"},
}

def shop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 Poké Ball — 50", callback_data="buy_pokeball"), InlineKeyboardButton("🔵 Great Ball — 150", callback_data="buy_greatball")],
        [InlineKeyboardButton("🟡 Ultra Ball — 300", callback_data="buy_ultraball"), InlineKeyboardButton("⚫ Master Ball — 5000", callback_data="buy_masterball")]
    ])

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    rows = query("SELECT coins FROM players WHERE user_id = %s", [user.id])
    if not rows:
        await update.message.reply_text("❌ You are not registered!\n\n👉 Start the bot in private first!")
        return

    await update.message.reply_text(
        f"╔═══════════════════╗\n       🛒 *POKÉ SHOP*\n╚═══════════════════╝\n\n💰 Balance: *{rows[0]['coins']}* Pokédollars\n\nSelect a ball to buy:",
        parse_mode="Markdown", reply_markup=shop_keyboard()
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Use this command in a group!")
        return

    item = context.args[0].lower() if context.args else ""
    if not item or item not in SHOP:
        await update.message.reply_text("❌ Invalid item!\n\nUse:\n🔴 /buy pokeball\n🔵 /buy greatball\n🟡 /buy ultraball\n⚫ /buy masterball")
        return

    it = SHOP[item]
    rows = query("SELECT coins FROM players WHERE user_id = %s", [user.id])
    if not rows:
        await update.message.reply_text(f"❌ *{user.first_name}* you are not registered yet!\n\n👉 Start the bot in private first!", parse_mode="Markdown")
        return

    coins = int(rows[0]['coins'])
    if coins < it['price']:
        await update.message.reply_text(f"❌ *Not enough Pokédollars!*\n\n┣ Need: *{it['price']}* coins\n┗ You have: *{coins}* coins\n\n💡 Chat more or use /daily!", parse_mode="Markdown")
        return

    query(f"UPDATE players SET coins = coins - %s, {it['col']} = {it['col']} + 1 WHERE user_id = %s", [it['price'], user.id])

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buy More", callback_data="open_shop"), InlineKeyboardButton("🎒 My Profile", callback_data="check_profile")]])
    await update.message.reply_photo(
        photo=it['img'],
        caption=f"╔═══════════════════╗\n     ✅ *PURCHASE SUCCESS*\n╚═══════════════════╝\n\n{it['emoji']} *{it['name']}* added to bag!\n\n┣ 💸 Spent: *{it['price']}* coins\n┗ 💰 Balance: *{coins - it['price']}* coins\n\nCheck your bag with /profile! 🎒",
        parse_mode="Markdown", reply_markup=kb
    )
