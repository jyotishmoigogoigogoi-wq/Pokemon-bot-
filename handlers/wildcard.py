import time
from telegram import Update
from telegram.ext import ContextTypes
from db import query
from poke_helper import get_random_pokemon, get_spawn_type, get_gender, is_pseudo, get_official_image, get_shiny_image
from state import get_state, set_state
from handlers.start import handle_registration
from handlers.misc import handle_promo_code, handle_broadcast, promo
from handlers.daily import daily
from handlers.collection import collection
from handlers.profile import profile

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text
    now = int(time.time())

    # Keyboard buttons
    if text == "📅 Daily Reward":
        await daily(update, context)
        return
    if text == "🎁 Promo Code":
        await promo(update, context)
        return
    if text == "📦 My Collection":
        context.args = ["all"]
        await collection(update, context)
        return
    if text == "👤 My Profile":
        await profile(update, context)
        return

    # Private chat state handlers
    if chat.type == "private":
        if get_state(user.id, "promo_step") == "awaiting_code":
            await handle_promo_code(update, context, text)
            return

        broadcast_step = get_state(user.id, "broadcast_step")
        if broadcast_step:
            await handle_broadcast(update, context, text, broadcast_step)
            return

        reg_step = get_state(user.id, "reg_step")
        if reg_step:
            await handle_registration(update, context, text, reg_step)
            return
        return

    # Group chat only below
    if chat.type not in ["group", "supergroup"]:
        return

    # Rate limit per user
    last_time = get_state(user.id, "last_msg") or 0
    if now - last_time < 5:
        return
    set_state(user.id, "last_msg", now)

    # Combined coins + counter
    try:
        result = query(
            "WITH coin_update AS ("
            "  UPDATE players SET coins = coins + 5 WHERE user_id = %s RETURNING user_id"
            "), counter_update AS ("
            "  INSERT INTO msg_counter (chat_id, count) VALUES (%s, 1)"
            "  ON CONFLICT (chat_id) DO UPDATE SET count = msg_counter.count + 1"
            "  RETURNING count"
            ") SELECT "
            "  (SELECT user_id FROM coin_update) as updated_user,"
            "  (SELECT count FROM counter_update) as msg_count",
            [user.id, chat.id]
        )
        count = int(result[0]['msg_count']) if result and result[0]['msg_count'] else 0
    except Exception as e:
        print(f"Combined query error: {e}")
        return

    # Spawn every 50 messages
    if count > 0 and count % 50 == 0:
        query("UPDATE msg_counter SET count = 0 WHERE chat_id = %s", [chat.id])
        await _spawn_pokemon(context, chat.id)
        return

    # Check expired spawns
    spawn_rows = query("SELECT * FROM active_spawn WHERE chat_id = %s", [chat.id])
    if spawn_rows:
        spawn = spawn_rows[0]
        if now - int(spawn['spawned_at']) > 120:
            query("DELETE FROM active_spawn WHERE chat_id = %s", [chat.id])
            flee_name = spawn['name'].capitalize()
            await context.bot.send_message(
                chat_id=chat.id,
                text=f"🌫️ *The wild {flee_name} fled!*\n\nBe faster next time! 💨",
                parse_mode="Markdown"
            )

async def _spawn_pokemon(context, chat_id):
    now = int(time.time())
    spawn_type = get_spawn_type()
    is_shiny = spawn_type == "shiny"
    is_legend = spawn_type == "legendary"

    poke = await get_random_pokemon("legendary" if is_legend else "normal")
    if not poke:
        return

    poke_id = poke['id']
    poke_name = poke['name']
    gender = get_gender(is_legend)
    is_ps = is_pseudo(poke_id)
    image_url = get_shiny_image(poke_id) if is_shiny else get_official_image(poke_id)
    tries_left = 1 if is_legend else 3

    query(
        "INSERT INTO active_spawn (chat_id, pokemon_id, name, is_shiny, is_legendary, is_pseudo, gender, image_url, tries_left, spawned_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (chat_id) DO UPDATE SET pokemon_id=%s,name=%s,is_shiny=%s,is_legendary=%s,is_pseudo=%s,gender=%s,image_url=%s,tries_left=%s,spawned_at=%s",
        [chat_id,poke_id,poke_name,is_shiny,is_legend,is_ps,gender,image_url,tries_left,now,
         poke_id,poke_name,is_shiny,is_legend,is_ps,gender,image_url,tries_left,now]
    )

    if is_legend:
        caption = "👑 *A LEGENDARY POKÉMON APPEARED!*\n\n━━━━━━━━━━━━━━\n❓ Who is this legendary?\n━━━━━━━━━━━━━━\n\n⚠️ Need a *Master Ball* to catch it!\n🎯 Use */guess [name]* — Only *1 try!*\n⏱️ Flees in *2 minutes!*"
    elif is_shiny:
        caption = f"✨ *A SHINY POKÉMON APPEARED!*\n\n━━━━━━━━━━━━━━\n❓ Who is this Pokémon?\n━━━━━━━━━━━━━━\n\n🎯 Use */guess [name]* to catch it!\n💡 {tries_left} tries | ⏱️ Flees in *2 minutes!*"
    else:
        caption = f"🌿 *A wild Pokémon appeared!*\n\n━━━━━━━━━━━━━━\n❓ Who is this Pokémon?\n━━━━━━━━━━━━━━\n\n🎯 Use */guess [name]* to catch it!\n💡 {tries_left} tries | ⏱️ Flees in *2 minutes!*"

    await context.bot.send_photo(chat_id=chat_id, photo=image_url, caption=caption, parse_mode="Markdown")
