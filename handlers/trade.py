import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import query
from state import check_cooldown

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    wait = check_cooldown(user.id)
    if wait:
        await update.message.reply_text(f"⏳ Slow down! Wait *{wait}* seconds!", parse_mode="Markdown")
        return

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Use this command in a group!")
        return

    if not update.message.reply_to_message or not update.message.reply_to_message.from_user:
        await update.message.reply_text("❌ *How to trade:*\n\nReply to someone's message and type:\n`/trade`\n\n_(You'll pick your Pokémon from buttons!)_", parse_mode="Markdown")
        return

    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("😂 You can't trade with yourself!")
        return
    if target.is_bot:
        await update.message.reply_text("🤖 You can't trade with a bot!")
        return

    both = query("SELECT user_id FROM players WHERE user_id = %s OR user_id = %s", [user.id, target.id])
    if len(both) < 2:
        await update.message.reply_text(f"❌ Both players need to be registered!\n\nMake sure *{target.first_name}* has started the bot in private!", parse_mode="Markdown")
        return

    existing = query("SELECT id FROM trades WHERE (sender_id = %s OR receiver_id = %s) AND status NOT IN ('completed','cancelled','expired')", [user.id, user.id])
    if existing:
        await update.message.reply_text("⚠️ You already have a pending trade!\n\nCancel it first!", parse_mode="Markdown")
        return

    col_rows = query("SELECT id, name, is_shiny, is_legendary FROM collection WHERE user_id = %s ORDER BY caught_at DESC LIMIT 8", [user.id])
    if not col_rows:
        await update.message.reply_text("❌ You have no Pokémon to trade!\n\nCatch some first!")
        return

    now = int(time.time())
    trade_rows = query("INSERT INTO trades (sender_id, receiver_id, group_chat_id, status, expires_at, created_at) VALUES (%s,%s,%s,'selecting_sender',%s,%s) RETURNING id",
                       [user.id, target.id, chat.id, now + 300, now])
    trade_id = trade_rows[0]['id']

    buttons = _make_pokemon_buttons(col_rows, f"tpick_s_{trade_id}")
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"trade_decline_{trade_id}")])

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"╔═══════════════════╗\n    🔄 *TRADE REQUEST*\n╚═══════════════════╝\n\nYou want to trade with *{target.first_name}*\n\n━━━━━━━━━━━━━━\n👇 *Pick a Pokémon to offer:*\n━━━━━━━━━━━━━━",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await update.message.reply_text(f"📩 *{user.first_name}*, check your DMs to pick your Pokémon!", parse_mode="Markdown")
    except:
        query("UPDATE trades SET status = 'cancelled' WHERE id = %s", [trade_id])
        await update.message.reply_text(f"❌ Couldn't DM *{user.first_name}*!\n\nStart the bot in private first: @{context.bot.username}", parse_mode="Markdown")

def _make_pokemon_buttons(col_rows, prefix):
    buttons = []
    for i in range(0, len(col_rows), 2):
        row = []
        pk1 = col_rows[i]
        t1 = "✨" if pk1['is_shiny'] else "👑" if pk1['is_legendary'] else "🟢"
        row.append(InlineKeyboardButton(f"{t1} {pk1['name'].capitalize()}", callback_data=f"{prefix}_{pk1['id']}_{pk1['name']}"))
        if i+1 < len(col_rows):
            pk2 = col_rows[i+1]
            t2 = "✨" if pk2['is_shiny'] else "👑" if pk2['is_legendary'] else "🟢"
            row.append(InlineKeyboardButton(f"{t2} {pk2['name'].capitalize()}", callback_data=f"{prefix}_{pk2['id']}_{pk2['name']}"))
        buttons.append(row)
    return buttons

# ── Trade Callbacks ──
async def handle_trade_callbacks(query_cb, context, data, user_id):
    now = int(time.time())

    def expired(t):
        if t.get('expires_at') and now > int(t['expires_at']):
            query("UPDATE trades SET status = 'expired' WHERE id = %s", [t['id']])
            return True
        return False

    if data.startswith("tpick_s_"):
        parts = data.replace("tpick_s_","").split("_")
        trade_id, col_id, poke_name = int(parts[0]), int(parts[1]), parts[2]
        rows = query("SELECT * FROM trades WHERE id = %s AND status = 'selecting_sender'", [trade_id])
        if not rows: return
        t = rows[0]
        if expired(t): await query_cb.answer("⏰ Trade expired!", show_alert=True); return
        if user_id != int(t['sender_id']): return

        query("UPDATE trades SET sender_pokemon_col_id = %s, sender_pokemon_name = %s, status = 'waiting_receiver' WHERE id = %s", [col_id, poke_name, trade_id])

        poke_rows = query("SELECT image_url, is_shiny, is_legendary FROM collection WHERE id = %s", [col_id])
        poke_img = poke_rows[0]['image_url'] if poke_rows else ""
        is_shiny = poke_rows[0]['is_shiny'] if poke_rows else False
        is_legend = poke_rows[0]['is_legendary'] if poke_rows else False
        tag = "✨" if is_shiny else "👑" if is_legend else "🟢"
        pname = poke_name.capitalize()
        sender_name = (query("SELECT first_name FROM players WHERE user_id = %s", [user_id]) or [{"first_name":"Trainer"}])[0]['first_name']

        await query_cb.edit_message_text(f"✅ You offered *{tag} {pname}*\n\n⏳ Waiting for response...", parse_mode="Markdown")

        try:
            await context.bot.send_photo(
                chat_id=t['receiver_id'], photo=poke_img,
                caption=f"╔═══════════════════╗\n   🔄 *INCOMING TRADE!*\n╚═══════════════════╝\n\n👤 *{sender_name}* offers:\n┗ *{tag} {pname}*\n\nDo you accept?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Accept", callback_data=f"tpick_r_start_{trade_id}"), InlineKeyboardButton("❌ Decline", callback_data=f"trade_decline_{trade_id}")]])
            )
        except:
            query("UPDATE trades SET status = 'cancelled' WHERE id = %s", [trade_id])
        return

    if data.startswith("tpick_r_start_"):
        trade_id = int(data.replace("tpick_r_start_",""))
        rows = query("SELECT * FROM trades WHERE id = %s AND status = 'waiting_receiver'", [trade_id])
        if not rows: return
        t = rows[0]
        if expired(t): await query_cb.answer("⏰ Trade expired!", show_alert=True); return
        if user_id != int(t['receiver_id']): return

        col_rows = query("SELECT id, name, is_shiny, is_legendary FROM collection WHERE user_id = %s ORDER BY caught_at DESC LIMIT 8", [user_id])
        if not col_rows: return

        buttons = _make_pokemon_buttons(col_rows, f"tpick_r_{trade_id}")
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"trade_decline_{trade_id}")])
        await query_cb.edit_message_caption(caption="👇 *Pick a Pokémon to offer back:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("tpick_r_") and not data.startswith("tpick_r_start_"):
        parts = data.replace("tpick_r_","").split("_")
        trade_id, col_id, poke_name = int(parts[0]), int(parts[1]), parts[2]
        rows = query("SELECT * FROM trades WHERE id = %s AND status = 'waiting_receiver'", [trade_id])
        if not rows: return
        t = rows[0]
        if expired(t): await query_cb.answer("⏰ Trade expired!", show_alert=True); return
        if user_id != int(t['receiver_id']): return

        query("UPDATE trades SET receiver_pokemon_col_id = %s, receiver_pokemon_name = %s, status = 'confirming' WHERE id = %s", [col_id, poke_name, trade_id])

        sname = t['sender_pokemon_name'].capitalize()
        rname = poke_name.capitalize()
        sender_name = (query("SELECT first_name FROM players WHERE user_id = %s", [t['sender_id']]) or [{"first_name":"Trainer"}])[0]['first_name']
        receiver_name = (query("SELECT first_name FROM players WHERE user_id = %s", [t['receiver_id']]) or [{"first_name":"Trainer"}])[0]['first_name']

        confirm_text = f"╔═══════════════════╗\n   ⚠️ *CONFIRM TRADE*\n╚═══════════════════╝\n\n┣ *{sender_name}* gives: *{sname}*\n┗ *{receiver_name}* gives: *{rname}*\n\n⚠️ Cannot be undone!"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm!", callback_data=f"tconfirm_{trade_id}"), InlineKeyboardButton("❌ Cancel", callback_data=f"trade_decline_{trade_id}")]])

        await context.bot.send_message(chat_id=t['sender_id'], text=confirm_text, parse_mode="Markdown", reply_markup=kb)
        await context.bot.send_message(chat_id=t['receiver_id'], text=confirm_text, parse_mode="Markdown", reply_markup=kb)
        return

    if data.startswith("tconfirm_"):
        trade_id = int(data.replace("tconfirm_",""))
        rows = query("SELECT * FROM trades WHERE id = %s AND status = 'confirming'", [trade_id])
        if not rows: return
        t = rows[0]
        if expired(t): await query_cb.answer("⏰ Trade expired!", show_alert=True); return
        if user_id not in [int(t['sender_id']), int(t['receiver_id'])]: return

        query("UPDATE collection SET user_id = %s WHERE id = %s", [t['receiver_id'], t['sender_pokemon_col_id']])
        query("UPDATE collection SET user_id = %s WHERE id = %s", [t['sender_id'], t['receiver_pokemon_col_id']])
        query("UPDATE trades SET status = 'completed' WHERE id = %s", [trade_id])

        sname = t['sender_pokemon_name'].capitalize()
        rname = t['receiver_pokemon_name'].capitalize()
        sender_name = (query("SELECT first_name FROM players WHERE user_id = %s", [t['sender_id']]) or [{"first_name":"Trainer"}])[0]['first_name']
        receiver_name = (query("SELECT first_name FROM players WHERE user_id = %s", [t['receiver_id']]) or [{"first_name":"Trainer"}])[0]['first_name']

        done = f"🎉 *Trade Complete!*\n\n┣ *{sender_name}* got: *{rname}*\n┗ *{receiver_name}* got: *{sname}*"
        await context.bot.send_message(chat_id=t['sender_id'], text=done, parse_mode="Markdown")
        await context.bot.send_message(chat_id=t['receiver_id'], text=done, parse_mode="Markdown")
        try: await context.bot.send_message(chat_id=t['group_chat_id'], text=done, parse_mode="Markdown")
        except: pass
        await query_cb.answer("🎉 Trade Complete!", show_alert=True)
        return

    if data.startswith("trade_decline_"):
        trade_id = int(data.replace("trade_decline_",""))
        rows = query("SELECT * FROM trades WHERE id = %s AND status NOT IN ('completed','cancelled')", [trade_id])
        if not rows: return
        t = rows[0]
        query("UPDATE trades SET status = 'cancelled' WHERE id = %s", [trade_id])
        try:
            await context.bot.send_message(chat_id=t['sender_id'], text="❌ Trade cancelled!")
            await context.bot.send_message(chat_id=t['receiver_id'], text="❌ Trade cancelled!")
        except: pass
