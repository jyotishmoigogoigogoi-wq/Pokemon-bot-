from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import query
from poke_helper import normalize_name
from state import check_cooldown

async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Use this command in a group!")
        return

    if not context.args:
        await update.message.reply_text("❌ Tell me which Pokémon to release!\n\nExample: */release pikachu*\n\n💡 Check your Pokémon with /collection", parse_mode="Markdown")
        return

    if not query("SELECT user_id FROM players WHERE user_id = %s", [user.id]):
        await update.message.reply_text("❌ You are not registered!\n\n👉 Start the bot in private first!")
        return

    poke_name = normalize_name(" ".join(context.args))
    poke_rows = query("SELECT id, name, is_shiny, is_legendary, is_pseudo, image_url FROM collection WHERE user_id = %s AND name = %s LIMIT 1", [user.id, poke_name])

    if not poke_rows:
        await update.message.reply_text(f"❌ You don't have *{poke_name}* in your collection!\n\nCheck /collection first!", parse_mode="Markdown")
        return

    poke = poke_rows[0]
    cname = poke['name'].capitalize()

    if poke['is_legendary']: coin_reward, rarity = 1500, "👑 Legendary"
    elif poke['is_shiny']: coin_reward, rarity = 400, "✨ Shiny"
    elif poke['is_pseudo']: coin_reward, rarity = 150, "🔮 Pseudo Legendary"
    else: coin_reward, rarity = 30, "🟢 Normal"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yes Release!", callback_data=f"release_confirm_{user.id}_{poke['id']}_{coin_reward}"),
        InlineKeyboardButton("❌ No Cancel!", callback_data=f"release_cancel_{user.id}")
    ]])

    await update.message.reply_photo(
        photo=poke['image_url'],
        caption=f"╔═══════════════════╗\n    ⚠️ *RELEASE POKÉMON*\n╚═══════════════════╝\n\nAre you sure you want to release\n*{cname}*?\n\n━━━━━━━━━━━━━━\n┣ Rarity: *{rarity}*\n┗ You will get: *💰 {coin_reward} Pokédollars*\n━━━━━━━━━━━━━━\n\n⚠️ *This cannot be undone!*",
        parse_mode="Markdown", reply_markup=kb
    )
