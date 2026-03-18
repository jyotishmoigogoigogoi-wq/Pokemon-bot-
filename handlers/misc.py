import time
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import query
from poke_helper import get_official_image
from state import check_cooldown, get_state, set_state, del_state
from config import OWNER_ID, CHANNEL_ID

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("👉 Use commands in a group!\n\nAdd me to a group to start playing!")
        return

    showcase = [249,250,384,483,484,643,644,716,717,800,889,890]
    titles = ["☠️ *SHADOW POKÉDEX* ☠️","⚡ *POKÉTELEGRAM* ⚡","🌑 *DARK TRAINER GUILD* 🌑","💀 *CATCH OR BE CAUGHT* 💀","🔥 *ELITE TRAINER HUB* 🔥","👑 *LEGENDARY HUNTERS* 👑","✨ *SHINY OBSESSED* ✨"]
    title = random.choice(titles)
    pic = get_official_image(random.choice(showcase))

    await update.message.reply_photo(
        photo=pic,
        caption=f"╔═══════════════════╗\n   {title}\n╚═══════════════════╝\n\n✦ ─────────────────── ✦\n   📖 *COMPLETE TRAINER GUIDE*\n✦ ─────────────────── ✦",
        parse_mode="Markdown"
    )
    await update.message.reply_text(
        "👤 *TRAINER COMMANDS*\n┣ /profile — Trainer card\n┣ /collection — Your Pokémon\n┣ /daily — Free Pokédollars\n┣ /promo — Redeem promo code 🎁\n┗ /changename — Change your name\n\n"
        "⚔️ *GAME COMMANDS*\n┣ /guess [name] — Catch a Pokémon\n┣ /walk — Solo encounter 🚶\n┣ /search [name] — Full Pokédex\n┣ /pokedex — Your progress 📚\n┣ /release [name] — Release for coins\n┗ /trade — Trade with trainer\n\n"
        "🛒 *SHOP*\n┣ /shop — View prices\n┣ /buy pokeball — 🔴 50\n┣ /buy greatball — 🔵 150\n┣ /buy ultraball — 🟡 300\n┗ /buy masterball — ⚫ 5000\n\n"
        "🏆 *RANKINGS*\n┣ /leaderboard — Top 10\n┗ /groupstats — Group stats\n\n"
        "━━━━━━━━━━━━━━━━━━━\n✦ *THE GRIND* ✦\n━━━━━━━━━━━━━━━━━━━\n"
        "┣ 💬 Chat → +5 coins/msg\n┣ 🌿 Spawn every 50 msgs\n┣ 🎯 Type /guess to catch!\n┣ ⏱️ 2 min or it flees!\n┣ 👑 Legendary = Master Ball only\n┣ ✨ Shiny = 1 in 20 chance\n┗ 🎲 Legendary = 1 in 100 chance\n\n"
        "━━━━━━━━━━━━━━━━━━━\n💰 *COIN EARNINGS*\n━━━━━━━━━━━━━━━━━━━\n"
        "┣ 💬 +5 per message\n┣ 🟢 Normal catch: +50\n┣ ✨ Shiny catch: +500\n┣ 👑 Legendary catch: +2000\n┣ 📅 Daily: +100\n┣ 🎁 Promo: varies\n┣ ⚡ 3 day streak: +150\n┣ 🔥 7 day streak: +300\n┣ 💎 14 day streak: +500\n┗ 👑 30 day streak: +1000\n\n"
        "━━━━━━━━━━━━━━━━━━━\n☠️ *RELEASE REWARDS*\n━━━━━━━━━━━━━━━━━━━\n"
        "┣ 🟢 Normal: +30\n┣ 🔮 Pseudo: +150\n┣ ✨ Shiny: +400\n┗ 👑 Legendary: +1500\n\n"
        "━━━━━━━━━━━━━━━━━━━\n🔰 *NEW HERE?*\n━━━━━━━━━━━━━━━━━━━\n"
        "DM me /start to register!\nChoose your starter & begin! 🚀\n\n✦ *Good luck Trainer!* ☠️",
        parse_mode="Markdown"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = time.time() * 1000
    msg = await update.message.reply_text("🏓 Pinging...")
    latency = int(time.time() * 1000 - start)
    emoji = "🟢" if latency < 500 else "🟡" if latency < 1000 else "🟠" if latency < 3000 else "🔴"
    status = "Excellent" if latency < 500 else "Good" if latency < 1000 else "Slow" if latency < 3000 else "Very Slow"
    await msg.edit_text(f"🏓 *PONG!*\n\n╔═══════════════════╗\n    📡 *LATENCY CHECK*\n╚═══════════════════╝\n\n{emoji} Status: *{status}*\n⚡ Latency: *{latency}ms*\n\n🤖 Bot: *Online* ✅\n🗄️ Server: *Render.com*", parse_mode="Markdown")

async def changename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ Use this in private chat!\n\n👉 DM me to change your name!")
        return
    rows = query("SELECT first_name FROM players WHERE user_id = %s", [user.id])
    if not rows:
        await update.message.reply_text("❌ You are not registered!\n\n👉 Send /start first.")
        return
    set_state(user.id, "reg_step", "changename")
    await update.message.reply_text(f"✏️ *Change Trainer Name*\n\n━━━━━━━━━━━━━━\nCurrent name: *{rows[0]['first_name']}*\n━━━━━━━━━━━━━━\n\nType your new trainer name below:\n_(or send /cancel to cancel)_", parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    had = False
    for key in ["promo_step", "promo_attempts", "broadcast_step", "broadcast_code", "broadcast_amount", "reg_step", "reg_name"]:
        if get_state(user.id, key) is not None:
            del_state(user.id, key)
            had = True
    if had:
        await update.message.reply_text("╔═══════════════════════════════╗\n        ✅ *CANCELLED* ✅\n╚═══════════════════════════════╝\n\nYour ongoing operation has been cancelled.\nYou're free to start something new! ✨", parse_mode="Markdown")
    else:
        await update.message.reply_text("🌟 Nothing to cancel!\n\nYou don't have any active operations.", parse_mode="Markdown")

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ Use this command in private chat!")
        return
    if not query("SELECT user_id FROM players WHERE user_id = %s", [user.id]):
        await update.message.reply_text("❌ You are not registered! Use /start first.")
        return
    set_state(user.id, "promo_step", "awaiting_code")
    set_state(user.id, "promo_attempts", 0)
    await update.message.reply_text(
        "╔═══════════════════════════════╗\n     💎 *ＰＲＯＭＯ ＣＯＤＥ* 💎\n╚═══════════════════════════════╝\n\n✦ ───────────────────────── ✦\n   ⌨️ *ENTER YOUR CODE* ⌨️\n✦ ───────────────────────── ✦\n\n📝 Type your promo code below\n\n❌ Send /cancel to abort",
        parse_mode="Markdown"
    )

async def handle_promo_code(update, context, text):
    user = update.effective_user
    code = text.strip().upper()
    now = int(time.time())
    promo_rows = query("SELECT * FROM promo_codes WHERE code = %s", [code])
    if not promo_rows:
        attempts = int(get_state(user.id, "promo_attempts") or 0) + 1
        set_state(user.id, "promo_attempts", attempts)
        if attempts >= 3:
            del_state(user.id, "promo_step")
            del_state(user.id, "promo_attempts")
            await update.message.reply_text("❌ *Too many invalid attempts!*\n\nPromo entry cancelled. Try again later.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ *Invalid promo code!*\n\nTry again ({attempts}/3) or send /cancel to abort.", parse_mode="Markdown")
        return
    p = promo_rows[0]
    if int(p['uses_so_far']) >= int(p['max_uses']):
        del_state(user.id, "promo_step")
        await update.message.reply_text("❌ This promo code has expired (max uses reached).")
        return
    if query("SELECT * FROM promo_redemptions WHERE promo_id = %s AND user_id = %s", [p['id'], user.id]):
        del_state(user.id, "promo_step")
        await update.message.reply_text("❌ You have already used this promo code!")
        return
    query("UPDATE players SET coins = coins + %s WHERE user_id = %s", [p['amount'], user.id])
    query("UPDATE promo_codes SET uses_so_far = uses_so_far + 1 WHERE id = %s", [p['id']])
    query("INSERT INTO promo_redemptions (promo_id, user_id, redeemed_at) VALUES (%s,%s,%s)", [p['id'], user.id, now])
    del_state(user.id, "promo_step")
    del_state(user.id, "promo_attempts")
    await update.message.reply_text(f"╔═══════════════════════════════╗\n     ✅ *PROMO REDEEMED!* ✅\n╚═══════════════════════════════╝\n\n💰 You received *{p['amount']}* Pokédollars!\n\nCheck your balance with /profile", parse_mode="Markdown")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text("🖕 Owner only!")
        return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ Use in private chat!")
        return
    set_state(user.id, "broadcast_step", "ask_code")
    await update.message.reply_text("╔═══════════════════╗\n   📢 *BROADCAST WIZARD*\n╚═══════════════════╝\n\n📝 *Step 1 of 3*\n\nEnter the *Promo Code* name:\n\n_(Example: SHADOW100)_\n\n❌ Send /cancel to abort", parse_mode="Markdown")

async def handle_broadcast(update, context, text, step):
    user = update.effective_user
    if step == "ask_code":
        code = text.strip().upper()
        set_state(user.id, "broadcast_code", code)
        set_state(user.id, "broadcast_step", "ask_amount")
        await update.message.reply_text(f"╔═══════════════════╗\n   📢 *BROADCAST WIZARD*\n╚═══════════════════╝\n\n✅ Code: *{code}*\n\n💰 *Step 2 of 3*\n\nEnter the *reward amount* in Pokédollars:\n\n❌ Send /cancel to abort", parse_mode="Markdown")
    elif step == "ask_amount":
        try: amount = int(text.strip())
        except:
            await update.message.reply_text("❌ Please enter a positive number!")
            return
        set_state(user.id, "broadcast_amount", amount)
        set_state(user.id, "broadcast_step", "ask_max")
        code = get_state(user.id, "broadcast_code")
        await update.message.reply_text(f"╔═══════════════════╗\n   📢 *BROADCAST WIZARD*\n╚═══════════════════╝\n\n✅ Code: *{code}*\n✅ Amount: *{amount}* Pokédollars\n\n👥 *Step 3 of 3*\n\nEnter *max users* who can claim:\n\n❌ Send /cancel to abort", parse_mode="Markdown")
    elif step == "ask_max":
        try: max_uses = int(text.strip())
        except:
            await update.message.reply_text("❌ Please enter a positive number!")
            return
        code = get_state(user.id, "broadcast_code")
        amount = int(get_state(user.id, "broadcast_amount"))
        now = int(time.time())
        query("INSERT INTO promo_codes (code, amount, max_uses, created_at) VALUES (%s,%s,%s,%s)", [code, amount, max_uses, now])

        bot_username = (await context.bot.get_me()).username
        deep_link = f"https://t.me/{bot_username}?start=promo"
        channel_msg = (
            "╔═══════════════════════════════╗\n     🎁 *NEW PROMO CODE!* 🎁\n╚═══════════════════════════════╝\n\n"
            f"💰 *Reward:* {amount} Pokédollars\n👥 *Limited to:* {max_uses} trainers only!\n⏳ *First come, first served!*\n\n"
            f"📋 *Code:* `{code}`\n\n"
            "👇 *How to redeem:*\n1️⃣ Start the bot in private\n2️⃣ Send */promo*\n3️⃣ Enter the code above!\n\n"
            f"⚡ *@{bot_username}*"
        )
        await update.message.reply_text(f"╔═══════════════════╗\n   ✅ *READY TO SEND!*\n╚═══════════════════╝\n\n📋 Code: *{code}*\n💰 Amount: *{amount}* Pokédollars\n👥 Max uses: *{max_uses}*\n\n⏳ Sending in *10 seconds...*", parse_mode="Markdown")
        await asyncio.sleep(10)
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=channel_msg, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Play & Redeem", url=deep_link)]]),
                disable_web_page_preview=True)
            await update.message.reply_text(f"✅ *Broadcast sent!*\n\n📢 Code *{code}* is now live!", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ *Failed!*\n\nError: {e}", parse_mode="Markdown")
        del_state(user.id, "broadcast_step")
        del_state(user.id, "broadcast_code")
        del_state(user.id, "broadcast_amount")
