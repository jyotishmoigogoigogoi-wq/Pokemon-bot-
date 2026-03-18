import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from db import query
from poke_helper import get_official_image
from state import get_state, set_state, del_state
import asyncio

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type != "private":
        await update.message.reply_text(f"👋 Hey {user.first_name}!\n\nPlease start me in private first!\n👉 @{context.bot.username}")
        return

    rows = query("SELECT user_id, coins, first_name FROM players WHERE user_id = %s", [user.id])

    if rows:
        p = rows[0]
        del_state(user.id, "reg_step")
        del_state(user.id, "reg_name")
        showcase = [25, 26, 133, 196, 197, 471, 700]
        kb = ReplyKeyboardMarkup(
            [["📅 Daily Reward", "🎁 Promo Code"], ["📦 My Collection", "👤 My Profile"]],
            resize_keyboard=True
        )
        await context.bot.send_photo(
            chat_id=user.id,
            photo=get_official_image(random.choice(showcase)),
            caption=f"⚡ *Welcome back, {p['first_name']}!*\n\n━━━━━━━━━━━━━━\n💰 Balance: *{p['coins']}* Pokédollars\n━━━━━━━━━━━━━━\n\n📖 /help — See all commands\n✏️ /changename — Change your name\n📦 /collection — Your Pokémon\n🎮 Have fun catching! 🌟",
            parse_mode="Markdown",
            reply_markup=kb
        )
        return

    set_state(user.id, "reg_step", "name")
    await context.bot.send_photo(
        chat_id=user.id,
        photo=get_official_image(384),
        caption=f"╔═══════════════════╗\n   🌟 *POKÉTELEGRAM* 🌟\n╚═══════════════════╝\n\n✦ ─────────────────── ✦\n   *A NEW JOURNEY AWAITS!*\n✦ ─────────────────── ✦\n\n🌍 Welcome, *{user.first_name}*!\n\nYou are about to become a\n⚡ *Pokémon Trainer* ⚡",
        parse_mode="Markdown"
    )
    await asyncio.sleep(1)
    await context.bot.send_photo(
        chat_id=user.id,
        photo=get_official_image(133),
        caption="╔═══════════════════╗\n   📋 *TRAINER SETUP* 📋\n╚═══════════════════╝\n\n📝 *Step 1 of 2*\n\n🧑 What is your *Trainer Name?*\n\n_(Type your name below)_",
        parse_mode="Markdown"
    )

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, step: str):
    user = update.effective_user
    from poke_helper import get_official_image

    if step == "changename":
        if len(text.strip()) < 2:
            await update.message.reply_text("❌ Name too short! Try again.")
            return
        query("UPDATE players SET first_name = %s WHERE user_id = %s", [text.strip(), user.id])
        del_state(user.id, "reg_step")
        await update.message.reply_text(f"✅ Trainer name changed to *{text.strip()}*!\n\nUse /profile to see your updated card! 🎮", parse_mode="Markdown")
        return

    if step == "name":
        if len(text.strip()) < 2:
            await update.message.reply_text("❌ Name too short! Please enter a proper trainer name.")
            return
        set_state(user.id, "reg_name", text.strip())
        set_state(user.id, "reg_step", "starter")
        await update.message.reply_photo(
            photo="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/175.png",
            caption=f"✅ Great name, *{text.strip()}!*\n\n━━━━━━━━━━━━━━\n📝 *Step 2 of 2*\n\nChoose your *Starter Pokémon!*\n\n🌿 Type *bulbasaur*\n🔥 Type *charmander*\n💧 Type *squirtle*\n━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
        return

    if step == "starter":
        starters = {
            "bulbasaur": {"id": 1, "emoji": "🌿"},
            "charmander": {"id": 4, "emoji": "🔥"},
            "squirtle": {"id": 7, "emoji": "💧"}
        }
        choice = text.lower().strip()
        if choice not in starters:
            await update.message.reply_text("❌ Invalid choice!\n\nPlease type:\n🌿 bulbasaur\n🔥 charmander\n💧 squirtle")
            return

        s = starters[choice]
        trainer_name = get_state(user.id, "reg_name") or user.first_name
        image_url = get_official_image(s['id'])

        query("INSERT INTO players (user_id, username, first_name, coins, pokeball, greatball, ultraball, masterball) VALUES (%s,%s,%s,200,5,2,1,0) ON CONFLICT (user_id) DO NOTHING",
              [user.id, user.username or "", trainer_name])
        query("INSERT INTO collection (user_id, pokemon_id, name, is_shiny, is_legendary, is_pseudo, gender, image_url) VALUES (%s,%s,%s,false,false,false,'male',%s)",
              [user.id, s['id'], choice, image_url])

        del_state(user.id, "reg_step")
        del_state(user.id, "reg_name")

        await update.message.reply_photo(
            photo=image_url,
            caption=f"🎉 *Registration Complete!*\n\n━━━━━━━━━━━━━━\n👤 Trainer: *{trainer_name}*\n{s['emoji']} Starter: *{choice.capitalize()}*\n━━━━━━━━━━━━━━\n\n🎒 *Starter Pack:*\n💰 200 Pokédollars\n🔴 5 Poké Balls\n🔵 2 Great Balls\n🟡 1 Ultra Ball\n\nAdd me to a group and start your journey!\nPokémon spawn every 50 messages! 🌟",
            parse_mode="Markdown"
        )
