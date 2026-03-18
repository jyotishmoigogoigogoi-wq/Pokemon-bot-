import random
import time
from telegram import Update
from telegram.ext import ContextTypes
from db import query
from poke_helper import get_random_pokemon, get_spawn_type, get_gender, is_legendary, is_pseudo, get_official_image, get_shiny_image, normalize_name
from config import OWNER_ID

async def addpromo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🖕 Owner only!")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Usage: /addpromo CODE AMOUNT [MAX_USES]\nExample: /addpromo PIKACHU2025 500 10")
        return
    code = args[0].upper()
    try:
        amount = int(args[1])
        max_uses = int(args[2]) if len(args) >= 3 else 10
    except:
        await update.message.reply_text("❌ Invalid numbers!")
        return
    try:
        query("INSERT INTO promo_codes (code, amount, max_uses, created_at) VALUES (%s,%s,%s,%s)", [code, amount, max_uses, int(time.time())])
        await update.message.reply_text(f"✅ Promo code *{code}* created!\n💰 Amount: {amount}\n👥 Max uses: {max_uses}", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Code already exists or database error.")

async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if user.id != OWNER_ID:
        await update.message.reply_text("🖕 Owner only!")
        return
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Use this command in a group!")
        return
    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text("❌ Reply to a user and provide Pokémon name!\n\nExample: /give pikachu (while replying)")
        return

    target = update.message.reply_to_message.from_user
    poke_name = normalize_name(" ".join(context.args))

    import aiohttp
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://pokeapi.co/api/v2/pokemon/{poke_name}") as r:
            if r.status != 200:
                await update.message.reply_text(f"❌ Pokémon *{poke_name}* not found!", parse_mode="Markdown")
                return
            poke = await r.json()

    poke_id = poke['id']
    image_url = get_official_image(poke_id)
    legend = is_legendary(poke_id)
    pseudo = is_pseudo(poke_id)
    gender = "genderless" if legend else ("male" if random.random() < 0.5 else "female")

    query("INSERT INTO players (user_id, username, first_name) VALUES (%s,%s,%s) ON CONFLICT (user_id) DO NOTHING", [target.id, '', 'Trainer'])
    query("INSERT INTO collection (user_id, pokemon_id, name, is_shiny, is_legendary, is_pseudo, gender, image_url) VALUES (%s,%s,%s,false,%s,%s,%s,%s)",
          [target.id, poke_id, poke['name'], legend, pseudo, gender, image_url])

    cname = poke['name'].capitalize()
    await update.message.reply_text(f"✅ Gave *{cname}* to *{target.first_name}!* 🎁", parse_mode="Markdown")
    try:
        await context.bot.send_photo(
            chat_id=target.id,
            photo=image_url,
            caption=f"🎁 *You received a gift!*\n\n━━━━━━━━━━━━━━\n👑 The bot owner gave you\n*{cname}!*\n━━━━━━━━━━━━━━\n\nCheck your /collection!",
            parse_mode="Markdown"
        )
    except: pass

async def addcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🖕 Owner only!")
        return
    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text("❌ Reply to a user and provide amount!")
        return
    target = update.message.reply_to_message.from_user
    try: amount = int(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid amount!")
        return
    rows = query("UPDATE players SET coins = coins + %s WHERE user_id = %s RETURNING coins", [amount, target.id])
    if not rows:
        await update.message.reply_text(f"❌ *{target.first_name}* is not registered yet!", parse_mode="Markdown")
        return
    new_balance = rows[0]['coins']
    await update.message.reply_text(f"✅ Added *{amount}* Pokédollars to *{target.first_name}!*\n🏦 New Balance: *{new_balance}*", parse_mode="Markdown")
    try:
        await context.bot.send_message(
            chat_id=target.id,
            text=f"💰 *You received {amount} Pokédollars!*\n\n👑 Gift from the bot owner!\n🏦 New Balance: *{new_balance}* Pokédollars",
            parse_mode="Markdown"
        )
    except: pass

async def removecoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🖕 Owner only!")
        return
    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text("❌ Reply to a user and provide amount!")
        return
    target = update.message.reply_to_message.from_user
    try: amount = int(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid amount!")
        return
    rows = query("UPDATE players SET coins = GREATEST(coins - %s, 0) WHERE user_id = %s RETURNING coins", [amount, target.id])
    if not rows:
        await update.message.reply_text("❌ User not found!")
        return
    await update.message.reply_text(f"✅ Removed *{amount}* Pokédollars!\n🏦 New Balance: *{rows[0]['coins']}*", parse_mode="Markdown")

async def spawn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    now = int(time.time())

    if user.id != OWNER_ID:
        await update.message.reply_text("🖕 Owner only!")
        return
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Use this in a group!")
        return

    arg = context.args[0].lower() if context.args else ""
    if arg not in ["legendary", "normal", "shiny"]:
        await update.message.reply_text("╔═══════════════════╗\n     👑 *FORCE SPAWN*\n╚═══════════════════╝\n\nUsage:\n┣ /spawn legendary\n┣ /spawn shiny\n┗ /spawn normal", parse_mode="Markdown")
        return

    is_shiny = arg == "shiny"
    is_legend = arg == "legendary"
    poke = await get_random_pokemon("legendary" if is_legend else "normal")
    if not poke:
        await update.message.reply_text("❌ Failed! Try again.")
        return

    poke_id = poke['id']
    poke_name = poke['name']
    gender = get_gender(is_legend)
    is_ps = is_pseudo(poke_id)
    image_url = get_shiny_image(poke_id) if is_shiny else get_official_image(poke_id)
    tries_left = 1 if is_legend else 3

    query("INSERT INTO active_spawn (chat_id, pokemon_id, name, is_shiny, is_legendary, is_pseudo, gender, image_url, tries_left, spawned_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (chat_id) DO UPDATE SET pokemon_id=%s,name=%s,is_shiny=%s,is_legendary=%s,is_pseudo=%s,gender=%s,image_url=%s,tries_left=%s,spawned_at=%s",
          [chat.id,poke_id,poke_name,is_shiny,is_legend,is_ps,gender,image_url,tries_left,now,
           poke_id,poke_name,is_shiny,is_legend,is_ps,gender,image_url,tries_left,now])

    if is_legend:
        caption = "👑 *A LEGENDARY POKÉMON APPEARED!*\n\n━━━━━━━━━━━━━━\n❓ Who is this legendary?\n━━━━━━━━━━━━━━\n\n⚠️ Need a *Master Ball* to catch it!\n🎯 Use */guess [name]* — Only *1 try!*\n⏱️ Flees in *2 minutes!*"
    elif is_shiny:
        caption = f"✨ *A SHINY POKÉMON APPEARED!*\n\n━━━━━━━━━━━━━━\n❓ Who is this Pokémon?\n━━━━━━━━━━━━━━\n\n🎯 Use */guess [name]* to catch it!\n💡 {tries_left} tries | ⏱️ Flees in *2 minutes!*"
    else:
        caption = f"🌿 *A wild Pokémon appeared!*\n\n━━━━━━━━━━━━━━\n❓ Who is this Pokémon?\n━━━━━━━━━━━━━━\n\n🎯 Use */guess [name]* to catch it!\n💡 {tries_left} tries | ⏱️ Flees in *2 minutes!*"

    await update.message.reply_photo(photo=image_url, caption=caption, parse_mode="Markdown")
