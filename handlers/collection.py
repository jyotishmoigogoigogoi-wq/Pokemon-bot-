import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import query
from poke_helper import get_official_image
from state import check_cooldown, is_col_loading, set_col_loading, get_col_last_used, set_col_last_used

COOLDOWN = 300

async def collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    now_sec = int(time.time())

    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    # 5 min cooldown check
    last_used = get_col_last_used(user.id)
    if last_used:
        tl = COOLDOWN - (now_sec - last_used)
        if tl > 0:
            mins, secs = tl // 60, tl % 60
            await update.message.reply_text(
                f"⏳ *Collection Cooldown!*\n\nHey [{user.first_name}](tg://user?id={user.id}) come back in *{mins}m {secs}s*!\n\n_(You will be notified when ready!)_",
                parse_mode="Markdown"
            )
            return

    if is_col_loading(user.id):
        await update.message.reply_text("⏳ Your collection is already loading!\n\nPlease wait for it to finish!")
        return

    filter_type = context.args[0].lower() if context.args else ""

    if not filter_type:
        await update.message.reply_text(
            "╔═══════════════════╗\n    📦 *YOUR COLLECTION*\n╚═══════════════════╝\n\nChoose a filter:\n\n📦 /collection all\n👑 /collection legendary\n🔮 /collection pseudo\n✨ /collection shiny\n🟢 /collection normal",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 All", callback_data="col_all"), InlineKeyboardButton("👑 Legendary", callback_data="col_legendary")],
                [InlineKeyboardButton("✨ Shiny", callback_data="col_shiny"), InlineKeyboardButton("🔮 Pseudo", callback_data="col_pseudo")],
                [InlineKeyboardButton("🟢 Normal", callback_data="col_normal")]
            ])
        )
        return

    await send_collection(context, user, filter_type, update.effective_chat.id)

async def send_collection(context, user, filter_type, chat_id):
    user_id = user.id
    now_sec = int(time.time())

    where = "WHERE user_id = %s"
    label = "📦 All"
    params = [user_id]

    if filter_type == "legendary":
        where += " AND is_legendary = true"; label = "👑 Legendary"
    elif filter_type == "pseudo":
        where += " AND is_pseudo = true"; label = "🔮 Pseudo Legendary"
    elif filter_type == "shiny":
        where += " AND is_shiny = true"; label = "✨ Shiny"
    elif filter_type == "normal":
        where += " AND is_legendary = false AND is_pseudo = false AND is_shiny = false"; label = "🟢 Normal"
    elif filter_type != "all":
        await context.bot.send_message(chat_id=chat_id, text="❌ Invalid filter!")
        return

    count = query(f"SELECT COUNT(*) as total FROM collection {where}", params)
    total = int(count[0]['total']) if count else 0

    if total == 0:
        await context.bot.send_message(chat_id=chat_id, text=f"📦 No *{filter_type}* Pokémon in your collection!\n\nGo catch some! 🎯", parse_mode="Markdown")
        return

    rows = query(f"SELECT name, is_shiny, is_legendary, is_pseudo, gender, image_url, pokemon_id FROM collection {where} ORDER BY caught_at DESC", params)

    set_col_loading(user_id, True)
    set_col_last_used(user_id, now_sec)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"╔═══════════════════╗\n    📦 *YOUR COLLECTION*\n╚═══════════════════╝\n\n{label} | Total: *{total}* Pokémon\n\n⏳ Sending all now...",
        parse_mode="Markdown"
    )

    for i, pk in enumerate(rows):
        tags = (" ✨" if pk['is_shiny'] else "") + (" 👑" if pk['is_legendary'] else "") + (" 🔮" if pk['is_pseudo'] else "")
        tl = "👑 Legendary" if pk['is_legendary'] else "🔮 Pseudo Legendary" if pk['is_pseudo'] else "✨ Shiny" if pk['is_shiny'] else "🟢 Normal"
        img = pk['image_url'] or get_official_image(pk['pokemon_id'])
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=img,
            caption=f"✦ *#{i+1} — {pk['name'].capitalize()}*{tags}\n━━━━━━━━━━━━━━\n⚧ Gender: *{pk['gender']}*\n🏷️ Rarity: *{tl}*",
            parse_mode="Markdown"
        )
        await asyncio.sleep(0.2)

    await context.bot.send_message(chat_id=chat_id, text=f"✅ *All {total} Pokémon sent!*\n\n⏳ Collection locked for *5 minutes*!", parse_mode="Markdown")
    set_col_loading(user_id, False)

    async def notify():
        await asyncio.sleep(300)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎉 Hey [{user.first_name}](tg://user?id={user_id})!\n\n✅ *Collection cooldown is over!*\n\nYou can now use /collection again! 📦",
                parse_mode="Markdown"
            )
        except: pass
    asyncio.create_task(notify())
