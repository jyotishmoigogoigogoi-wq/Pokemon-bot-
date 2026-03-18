import time
from telegram import Update
from telegram.ext import ContextTypes
from db import query
from poke_helper import normalize_name, get_official_image
from state import check_cooldown

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    now = int(time.time())

    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    if not context.args:
        await update.message.reply_text("❌ Tell me the Pokémon name!\n\nExample: */guess pikachu*", parse_mode="Markdown")
        return

    guess_name = normalize_name(" ".join(context.args))
    if len(guess_name) < 2:
        await update.message.reply_text("❌ Invalid name!\n\nExample: */guess pikachu*", parse_mode="Markdown")
        return

    if chat.type == "private":
        await _guess_private(update, context, user, guess_name, now)
    elif chat.type in ["group", "supergroup"]:
        await _guess_group(update, context, user, chat, guess_name, now)

async def _guess_private(update, context, user, guess_name, now):
    player = query("SELECT * FROM players WHERE user_id = %s", [user.id])
    if not player:
        await update.message.reply_text("❌ You are not registered!\n\n👉 Start the bot in private first!")
        return
    player = player[0]

    walk = query("SELECT * FROM walk_spawns WHERE user_id = %s", [user.id])
    if not walk:
        await update.message.reply_text("🌿 No Pokémon waiting for you!\n\nUse */walk* in a group to find one! 🚶", parse_mode="Markdown")
        return
    spawn = walk[0]

    if now - int(spawn['spawned_at']) > 120:
        query("DELETE FROM walk_spawns WHERE user_id = %s", [user.id])
        await update.message.reply_text(f"🌫️ *Too late! The wild {spawn['name'].capitalize()} already fled!*\n\nUse /walk again! 💨", parse_mode="Markdown")
        return

    if guess_name != spawn['name'].lower():
        await _wrong_guess_private(update, user, spawn)
        return

    await _catch(update, context, spawn, player, user.id, private=True)
    query("DELETE FROM walk_spawns WHERE user_id = %s", [user.id])

async def _guess_group(update, context, user, chat, guess_name, now):
    spawn_rows = query("SELECT * FROM active_spawn WHERE chat_id = %s", [chat.id])
    if not spawn_rows:
        await update.message.reply_text("🌿 No Pokémon spawned right now!\n\nKeep chatting — one appears every 50 messages!\nOr use */walk* for a personal encounter! 🚶", parse_mode="Markdown")
        return
    spawn = spawn_rows[0]

    if now - int(spawn['spawned_at']) > 120:
        query("DELETE FROM active_spawn WHERE chat_id = %s", [chat.id])
        await update.message.reply_text(f"🌫️ *Too late! The wild {spawn['name'].capitalize()} already fled!*\n\nBe faster next time! 💨", parse_mode="Markdown")
        return

    player = query("SELECT * FROM players WHERE user_id = %s", [user.id])
    if not player:
        await update.message.reply_text(f"⚡ *{user.first_name}* you are not registered!\n\n👉 Start the bot in private first!", parse_mode="Markdown")
        return
    player = player[0]

    if guess_name != spawn['name'].lower():
        await _wrong_guess_group(update, chat, user, spawn)
        return

    await _catch(update, context, spawn, player, user.id, private=False)
    query("DELETE FROM active_spawn WHERE chat_id = %s", [chat.id])

async def _wrong_guess_private(update, user, spawn):
    if not spawn['is_legendary']:
        new_tries = int(spawn['tries_left']) - 1
        if new_tries <= 0:
            query("DELETE FROM walk_spawns WHERE user_id = %s", [user.id])
            await update.message.reply_text(f"🌫️ *Wrong! The wild {spawn['name'].capitalize()} fled!*\n\n_(The Pokémon's name was *{spawn['name'].capitalize()}*)_", parse_mode="Markdown")
        else:
            query("UPDATE walk_spawns SET tries_left = %s WHERE user_id = %s", [new_tries, user.id])
            await update.message.reply_text(f"❌ *Wrong guess!*\n\n┗ 💡 *{new_tries} tries remaining!*", parse_mode="Markdown")
    else:
        query("DELETE FROM walk_spawns WHERE user_id = %s", [user.id])
        await update.message.reply_text(f"👑 *Wrong!* The legendary *{spawn['name']}* fled!\n\n💨 Only 1 try for legendaries!", parse_mode="Markdown")

async def _wrong_guess_group(update, chat, user, spawn):
    if not spawn['is_legendary']:
        new_tries = int(spawn['tries_left']) - 1
        if new_tries <= 0:
            query("DELETE FROM active_spawn WHERE chat_id = %s", [chat.id])
            await update.message.reply_text(f"🌫️ *Wrong! The wild {spawn['name'].capitalize()} fled!*\n\n_(The Pokémon's name was *{spawn['name'].capitalize()}*)_", parse_mode="Markdown")
        else:
            query("UPDATE active_spawn SET tries_left = %s WHERE chat_id = %s", [new_tries, chat.id])
            await update.message.reply_text(f"❌ *Wrong guess, {user.first_name}!*\n\n┗ 💡 *{new_tries} tries remaining!*", parse_mode="Markdown")
    else:
        query("DELETE FROM active_spawn WHERE chat_id = %s", [chat.id])
        await update.message.reply_text(f"👑 *Wrong!* The legendary *{spawn['name']}* fled!\n\n💨 Only 1 try for legendaries!", parse_mode="Markdown")

async def _catch(update, context, spawn, player, user_id, private=False):
    user = update.effective_user
    chat = update.effective_chat

    if spawn['is_legendary']:
        if int(player['masterball']) < 1:
            if not private:
                query("DELETE FROM active_spawn WHERE chat_id = %s", [chat.id])
            await update.message.reply_text(f"👑 {'You' if private else '*' + user.first_name + '*'} knew it was *{spawn['name']}* but {'have' if private else 'has'} no *Master Ball!* 😭\n\nBuy one with /shop!", parse_mode="Markdown")
            return
        query("UPDATE players SET masterball = masterball - 1, coins = coins + 2000 WHERE user_id = %s", [user_id])
    else:
        total_balls = int(player['pokeball']) + int(player['greatball']) + int(player['ultraball'])
        if total_balls < 1:
            await update.message.reply_text("🎯 Right name but NO Poké Balls!\n\nBuy some at /shop!")
            return
        ball_col = "pokeball" if int(player['pokeball']) > 0 else "greatball" if int(player['greatball']) > 0 else "ultraball"
        coin_reward = 500 if spawn['is_shiny'] else 50
        query(f"UPDATE players SET {ball_col} = {ball_col} - 1, coins = coins + %s WHERE user_id = %s", [coin_reward, user_id])

    query("INSERT INTO collection (user_id, pokemon_id, name, is_shiny, is_legendary, is_pseudo, gender, image_url) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
          [user_id, spawn['pokemon_id'], spawn['name'], spawn['is_shiny'], spawn['is_legendary'], spawn['is_pseudo'], spawn['gender'], spawn['image_url']])

    cname = spawn['name'].capitalize()
    who = "You" if private else f"*{user.first_name}*"

    if spawn['is_legendary']:
        msg = f"╔═══════════════════╗\n   👑 *LEGENDARY CAUGHT!*\n╚═══════════════════╝\n\n🎉 {who} caught *{cname}!*\n\n┣ ⚫ Used: Master Ball\n┗ 💰 +2000 Pokédollars!"
    elif spawn['is_shiny']:
        msg = f"╔═══════════════════╗\n    ✨ *SHINY CAUGHT!*\n╚═══════════════════╝\n\n🎉 {who} caught *{cname}!*\n\n┗ 💰 +500 Pokédollars!"
    else:
        msg = f"╔═══════════════════╗\n      🟢 *CAUGHT!*\n╚═══════════════════╝\n\n🎉 {who} caught *{cname}!*\n\n┗ 💰 +50 Pokédollars!"

    await update.message.reply_text(msg, parse_mode="Markdown")
