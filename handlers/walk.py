import time
from telegram import Update
from telegram.ext import ContextTypes
from db import query
from poke_helper import get_random_pokemon, get_spawn_type, get_gender, is_pseudo, get_official_image, get_shiny_image
from state import check_cooldown

async def walk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    now = int(time.time())

    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Use this command in a group!")
        return

    if not query("SELECT user_id FROM players WHERE user_id = %s", [user.id]):
        await update.message.reply_text("❌ You are not registered!\n\n👉 Start the bot in private first!")
        return

    existing = query("SELECT * FROM walk_spawns WHERE user_id = %s", [user.id])
    if existing:
        w = existing[0]
        tl = 120 - (now - int(w['spawned_at']))
        if tl > 0:
            await update.message.reply_text(f"⚠️ You already have a Pokémon waiting!\n\n🎯 Check your DMs and use */guess [name]*\n⏱️ *{tl}* seconds left!", parse_mode="Markdown")
            return
        query("DELETE FROM walk_spawns WHERE user_id = %s", [user.id])

    spawn_type = get_spawn_type()
    is_shiny = spawn_type == "shiny"
    is_legend = spawn_type == "legendary"

    poke = await get_random_pokemon("legendary" if is_legend else "normal")
    if not poke:
        await update.message.reply_text("❌ Something went wrong! Try again.")
        return

    poke_id = poke['id']
    poke_name = poke['name']
    gender = get_gender(is_legend)
    is_ps = is_pseudo(poke_id)
    image_url = get_shiny_image(poke_id) if is_shiny else get_official_image(poke_id)
    tries_left = 1 if is_legend else 3

    query("INSERT INTO walk_spawns (user_id, pokemon_id, name, is_shiny, is_legendary, is_pseudo, gender, image_url, tries_left, spawned_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET pokemon_id=%s,name=%s,is_shiny=%s,is_legendary=%s,is_pseudo=%s,gender=%s,image_url=%s,tries_left=%s,spawned_at=%s",
          [user.id,poke_id,poke_name,is_shiny,is_legend,is_ps,gender,image_url,tries_left,now,
           poke_id,poke_name,is_shiny,is_legend,is_ps,gender,image_url,tries_left,now])

    await update.message.reply_text(f"🚶 *{user.first_name}* went for a walk!\n\n📩 Check your DMs — a Pokémon appeared!", parse_mode="Markdown")

    try:
        if is_legend:
            caption = f"╔═══════════════════╗\n   👑 *LEGENDARY APPEARED!*\n╚═══════════════════╝\n\n❓ Who is this legendary?\n\n⚠️ You need a *Master Ball!*\n🎯 Use */guess [name]* — Only *1 try!*\n⏱️ Flees in *2 minutes!*"
        elif is_shiny:
            caption = f"╔═══════════════════╗\n    ✨ *SHINY APPEARED!*\n╚═══════════════════╝\n\n❓ Who is this Pokémon?\n\n🎯 Use */guess [name]* to catch!\n💡 {tries_left} tries | ⏱️ Flees in *2 minutes!*"
        else:
            caption = f"╔═══════════════════╗\n  🚶 *WILD ENCOUNTER!*\n╚═══════════════════╝\n\n❓ Who is this Pokémon?\n\n🎯 Use */guess [name]* to catch!\n💡 {tries_left} tries | ⏱️ Flees in *2 minutes!*"
        await context.bot.send_photo(chat_id=user.id, photo=image_url, caption=caption, parse_mode="Markdown")
    except:
        query("DELETE FROM walk_spawns WHERE user_id = %s", [user.id])
        await update.message.reply_text(f"❌ Couldn't DM *{user.first_name}*!\n\nStart the bot in private first! 👉 @{context.bot.username}", parse_mode="Markdown")
