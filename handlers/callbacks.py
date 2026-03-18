import aiohttp
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from db import query
from poke_helper import get_official_image, get_shiny_image
from handlers.shop import SHOP
from handlers.collection import send_collection
from handlers.trade import handle_trade_callbacks
from handlers.leaderboard import _build_groupstats

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qcb = update.callback_query
    await qcb.answer()
    data = qcb.data
    user_id = qcb.from_user.id
    chat_id = qcb.message.chat_id

    # Profile
    if data == "check_profile":
        rows = query("SELECT * FROM players WHERE user_id = %s", [user_id])
        if not rows: return
        p = rows[0]
        stats = query("SELECT COUNT(*) as total, SUM(CASE WHEN is_legendary THEN 1 ELSE 0 END) as legendary, SUM(CASE WHEN is_shiny THEN 1 ELSE 0 END) as shiny FROM collection WHERE user_id = %s", [user_id])
        s = stats[0] if stats else {}
        await qcb.edit_message_text(
            f"╔═══════════════════╗\n      🎮 *TRAINER CARD*\n╚═══════════════════╝\n\n👤 *{p['first_name']}*\n\n💰 Coins: *{p['coins']}*\n🔥 Streak: *{p.get('streak',0)} days*\n\n🎒 *Balls*\n┣ 🔴 {p['pokeball']}  🔵 {p['greatball']}\n┣ 🟡 {p['ultraball']}  ⚫ {p['masterball']}\n\n📦 *Caught*\n┣ Total: *{s.get('total',0)}*\n┣ 👑 Legendary: *{s.get('legendary',0)}*\n┗ ✨ Shiny: *{s.get('shiny',0)}*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="check_profile")]])
        )
        return

    # Shop
    if data == "open_shop":
        rows = query("SELECT coins FROM players WHERE user_id = %s", [user_id])
        coins = rows[0]['coins'] if rows else 0
        await qcb.edit_message_text(
            f"╔═══════════════════╗\n       🛒 *POKÉ SHOP*\n╚═══════════════════╝\n\n💰 Balance: *{coins}* Pokédollars\n\nSelect a ball to buy:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 Poké Ball — 50", callback_data="buy_pokeball"), InlineKeyboardButton("🔵 Great Ball — 150", callback_data="buy_greatball")],
                [InlineKeyboardButton("🟡 Ultra Ball — 300", callback_data="buy_ultraball"), InlineKeyboardButton("⚫ Master Ball — 5000", callback_data="buy_masterball")],
                [InlineKeyboardButton("🔙 Back", callback_data="check_profile")]
            ])
        )
        return

    # Buy
    if data.startswith("buy_"):
        item = data.replace("buy_","")
        if item not in SHOP: return
        it = SHOP[item]
        rows = query("SELECT coins FROM players WHERE user_id = %s", [user_id])
        if not rows: return
        coins = int(rows[0]['coins'])
        if coins < it['price']:
            await qcb.answer(f"❌ Not enough coins! Need {it['price']} but you have {coins}", show_alert=True)
            return
        query(f"UPDATE players SET coins = coins - %s, {it['col']} = {it['col']} + 1 WHERE user_id = %s", [it['price'], user_id])
        new_coins = query("SELECT coins FROM players WHERE user_id = %s", [user_id])[0]['coins']
        await qcb.edit_message_text(
            f"╔═══════════════════╗\n       🛒 *POKÉ SHOP*\n╚═══════════════════╝\n\n✅ Bought *{it['emoji']} {it['name']}*!\n\n💰 Balance: *{new_coins}* Pokédollars\n\nBuy more:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 Poké Ball — 50", callback_data="buy_pokeball"), InlineKeyboardButton("🔵 Great Ball — 150", callback_data="buy_greatball")],
                [InlineKeyboardButton("🟡 Ultra Ball — 300", callback_data="buy_ultraball"), InlineKeyboardButton("⚫ Master Ball — 5000", callback_data="buy_masterball")],
                [InlineKeyboardButton("🔙 Back", callback_data="check_profile")]
            ])
        )
        return

    # Shiny
    if data.startswith("shiny_"):
        poke_id = data.replace("shiny_","")
        shiny_url = get_shiny_image(poke_id)
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://pokeapi.co/api/v2/pokemon/{poke_id}") as r:
                poke = await r.json() if r.status == 200 else None
        name = poke['name'].capitalize() if poke else "Pokémon"
        await qcb.edit_message_media(
            media=InputMediaPhoto(media=shiny_url, caption=f"✨ *{name}* — Shiny Form!", parse_mode="Markdown"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Normal Form", callback_data=f"normal_{poke_id}")]])
        )
        return

    # Normal
    if data.startswith("normal_"):
        poke_id = data.replace("normal_","")
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://pokeapi.co/api/v2/pokemon/{poke_id}") as r:
                poke = await r.json() if r.status == 200 else None
        name = poke['name'].capitalize() if poke else "Pokémon"
        await qcb.edit_message_media(
            media=InputMediaPhoto(media=get_official_image(poke_id), caption=f"🎨 *{name}* — Normal Form!", parse_mode="Markdown"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✨ Shiny Form", callback_data=f"shiny_{poke_id}")]])
        )
        return

    # Evolution
    if data.startswith("evo_") and not data.startswith("evo_stage_"):
        poke_name = data.replace("evo_","")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://pokeapi.co/api/v2/pokemon-species/{poke_name}") as r:
                if r.status != 200: return
                species = await r.json()
            evo_url = species.get('evolution_chain', {}).get('url')
            if not evo_url: return
            async with session.get(evo_url) as r:
                if r.status != 200: return
                evo_data = await r.json()
            async with session.get(f"https://pokeapi.co/api/v2/pokemon/{poke_name}") as r:
                poke = await r.json() if r.status == 200 else None
        poke_id = poke['id'] if poke else ""
        chain = _parse_chain(evo_data['chain'])

        if len(chain) == 1:
            await qcb.edit_message_caption(
                caption=f"╔═══════════════════╗\n    🔄 *EVOLUTION CHAIN*\n╚═══════════════════╝\n\n⚠️ *{chain[0]['name']}* does not evolve!\n\nIt is already in its final form! 💪",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✨ Shiny Form", callback_data=f"shiny_{poke_id}"), InlineKeyboardButton("🔙 Back", callback_data=f"back_search_{poke_id}")]])
            )
            return

        chain_text = "╔═══════════════════╗\n    🔄 *EVOLUTION CHAIN*\n╚═══════════════════╝\n\n"
        for i, p in enumerate(chain):
            prefix = "🥚" if i == 0 else "⭐" if i == len(chain)-1 else "➡️"
            chain_text += f"{prefix} *{p['name']}*"
            if i < len(chain)-1: chain_text += "\n      ⬇️\n"
        chain_text += "\n\n💡 Tap a stage to see its image!"

        stage_buttons = [InlineKeyboardButton(("🥚" if i==0 else "⭐" if i==len(chain)-1 else "➡️") + " " + p['name'], callback_data=f"evo_stage_{p['id']}_{poke_id}") for i,p in enumerate(chain)]
        rows_kb = [stage_buttons[i:i+3] for i in range(0, len(stage_buttons), 3)]
        rows_kb.append([InlineKeyboardButton("✨ Shiny", callback_data=f"shiny_{poke_id}"), InlineKeyboardButton("🔙 Back", callback_data=f"back_search_{poke_id}")])

        await qcb.edit_message_media(
            media=InputMediaPhoto(media=get_official_image(chain[0]['id']), caption=chain_text, parse_mode="Markdown"),
            reply_markup=InlineKeyboardMarkup(rows_kb)
        )
        return

    # Evo stage
    if data.startswith("evo_stage_"):
        parts = data.replace("evo_stage_","").split("_")
        stage_id, original_id = parts[0], parts[1]
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://pokeapi.co/api/v2/pokemon/{stage_id}") as r:
                if r.status != 200: return
                stage_poke = await r.json()
            async with session.get(f"https://pokeapi.co/api/v2/pokemon-species/{original_id}") as r:
                if r.status != 200: return
                species = await r.json()
            evo_url = species.get('evolution_chain', {}).get('url')
            if not evo_url: return
            async with session.get(evo_url) as r:
                if r.status != 200: return
                evo_data = await r.json()

        stage_name = stage_poke['name'].capitalize()
        types = " / ".join(t['type']['name'].capitalize() for t in stage_poke['types'])
        stats = {s['stat']['name']: s['base_stat'] for s in stage_poke['stats']}
        chain = _parse_chain(evo_data['chain'])

        stage_buttons = [InlineKeyboardButton(("🥚" if i==0 else "⭐" if i==len(chain)-1 else "➡️") + " " + p['name'], callback_data=f"evo_stage_{p['id']}_{original_id}") for i,p in enumerate(chain)]
        rows_kb = [stage_buttons[i:i+3] for i in range(0, len(stage_buttons), 3)]
        rows_kb.append([InlineKeyboardButton("✨ Shiny", callback_data=f"shiny_{stage_id}"), InlineKeyboardButton("🔙 Back", callback_data=f"back_search_{original_id}")])

        await qcb.edit_message_media(
            media=InputMediaPhoto(
                media=get_official_image(stage_id),
                caption=f"╔═══════════════════╗\n    🔄 *EVOLUTION STAGE*\n╚═══════════════════╝\n\n✦ *{stage_name}*\n\n━━━━━━━━━━━━━━\n📊 *STATS*\n┣ ❤️ HP: *{stats.get('hp','?')}*\n┣ ⚔️ ATK: *{stats.get('attack','?')}*\n┣ 🛡️ DEF: *{stats.get('defense','?')}*\n┣ ⚡ SPD: *{stats.get('speed','?')}*\n\n🏷️ Type: *{types}*",
                parse_mode="Markdown"
            ),
            reply_markup=InlineKeyboardMarkup(rows_kb)
        )
        return

    # Back to search
    if data.startswith("back_search_"):
        poke_id = data.replace("back_search_","")
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://pokeapi.co/api/v2/pokemon/{poke_id}") as r:
                if r.status != 200: return
                poke = await r.json()
        name = poke['name'].capitalize()
        stats = {s['stat']['name']: s['base_stat'] for s in poke['stats']}
        types = " / ".join(t['type']['name'].capitalize() for t in poke['types'])
        await qcb.edit_message_media(
            media=InputMediaPhoto(
                media=get_official_image(poke_id),
                caption=f"✦ *{name}*\n\n━━━━━━━━━━━━━━\n📊 *STATS*\n┣ ❤️ HP: *{stats.get('hp','?')}*\n┣ ⚔️ ATK: *{stats.get('attack','?')}*\n┣ ⚡ SPD: *{stats.get('speed','?')}*\n\n🏷️ Type: *{types}*",
                parse_mode="Markdown"
            ),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✨ Shiny Form", callback_data=f"shiny_{poke_id}"), InlineKeyboardButton("🔄 Evolution", callback_data=f"evo_{poke['name']}")]])
        )
        return

    # Collection buttons
    if data.startswith("col_"):
        filter_type = data.replace("col_","")
        await send_collection(context, qcb.from_user, filter_type, chat_id)
        return

    # Release confirm
    if data.startswith("release_confirm_"):
        parts = data.replace("release_confirm_","").split("_")
        owner_id, col_id, coin_reward = int(parts[0]), int(parts[1]), int(parts[2])
        if user_id != owner_id:
            await qcb.answer("🖕 Mind your own business! This ain't your Pokémon!", show_alert=True)
            return
        del_rows = query("DELETE FROM collection WHERE id = %s AND user_id = %s RETURNING name", [col_id, user_id])
        if not del_rows:
            await qcb.answer("❌ Pokemon not found!", show_alert=True)
            return
        query("UPDATE players SET coins = coins + %s WHERE user_id = %s", [coin_reward, user_id])
        cname = del_rows[0]['name'].capitalize()
        await qcb.edit_message_caption(caption=f"╔═══════════════════╗\n    👋 *POKÉMON RELEASED*\n╚═══════════════════╝\n\nYou released *{cname}*\n\n┗ 💰 +{coin_reward} Pokédollars added!\n\n_Goodbye {cname}! 🌿_", parse_mode="Markdown")
        return

    # Release cancel
    if data.startswith("release_cancel_"):
        owner_id = int(data.replace("release_cancel_",""))
        if user_id != owner_id:
            await qcb.answer("🖕 Back off! Who asked you?", show_alert=True)
            return
        await qcb.edit_message_caption(caption="✅ *Release cancelled!*\n\nYour Pokémon is safe! 🛡️", parse_mode="Markdown")
        return

    # Groupstats refresh
    if data.startswith("groupstats_"):
        group_chat_id = data.replace("groupstats_","")
        text, kb = _build_groupstats(group_chat_id)
        await qcb.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
        return

    # Trade callbacks
    if data.startswith("tpick_") or data.startswith("tconfirm_") or data.startswith("trade_decline_"):
        await handle_trade_callbacks(qcb, context, data, user_id)
        return

def _parse_chain(chain_node):
    chain = []
    queue = [chain_node]
    while queue:
        current = queue.pop(0)
        spec_id = current['species']['url'].rstrip('/').split('/')[-1]
        chain.append({"name": current['species']['name'].capitalize(), "id": spec_id})
        if current.get('evolves_to'):
            queue.extend(current['evolves_to'])
    return chain
