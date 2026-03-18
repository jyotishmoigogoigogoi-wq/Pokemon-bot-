import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from poke_helper import get_official_image, normalize_name, is_legendary
from state import check_cooldown

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text("❌ Please provide a Pokémon name!\n\nExample: /search pikachu")
        return

    poke_name = normalize_name(" ".join(context.args))

    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pokeapi.co/api/v2/pokemon/{poke_name}") as r:
            if r.status != 200:
                await update.message.reply_text(f"❌ Pokémon *{poke_name}* not found!\n\nCheck spelling and try again!", parse_mode="Markdown")
                return
            poke = await r.json()

        async with session.get(f"https://pokeapi.co/api/v2/pokemon-species/{poke['id']}") as r:
            species = await r.json() if r.status == 200 else None

    poke_id = poke['id']
    description = "No description available."
    if species:
        for e in species.get('flavor_text_entries', []):
            if e['language']['name'] == 'en':
                description = e['flavor_text'].replace('\n',' ').replace('\f',' ')
                break

    category = "Unknown"
    if species:
        for g in species.get('genera', []):
            if g['language']['name'] == 'en':
                category = g['genus']
                break

    types = " / ".join(t['type']['name'].capitalize() for t in poke['types'])
    abilities = ", ".join(a['ability']['name'].capitalize() for a in poke['abilities'])
    stats = {s['stat']['name']: s['base_stat'] for s in poke['stats']}
    total = sum(stats.values())
    name = poke['name'].capitalize()
    legend = is_legendary(poke_id)

    caption = (
        f"╔═══════════════════╗\n    🔍 *POKÉDEX #{poke_id}*\n╚═══════════════════╝\n\n"
        f"✦ *{name}*{'  👑' if legend else ''}\n📖 {category}\n\n"
        f"━━━━━━━━━━━━━━\n📊 *BASE STATS*\n"
        f"┣ ❤️ HP: *{stats.get('hp','?')}*\n"
        f"┣ ⚔️ ATK: *{stats.get('attack','?')}*\n"
        f"┣ 🛡️ DEF: *{stats.get('defense','?')}*\n"
        f"┣ 💫 SP.ATK: *{stats.get('special-attack','?')}*\n"
        f"┣ 🔰 SP.DEF: *{stats.get('special-defense','?')}*\n"
        f"┣ ⚡ SPD: *{stats.get('speed','?')}*\n"
        f"┗ 🌟 TOTAL: *{total}*\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏷️ Type: *{types}*\n"
        f"⚡ Abilities: *{abilities}*\n"
        f"📏 Height: *{poke['height']/10}m* | ⚖️ Weight: *{poke['weight']/10}kg*\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"📝 _{description}_"
    )

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✨ Shiny Form", callback_data=f"shiny_{poke_id}"),
        InlineKeyboardButton("🔄 Evolution", callback_data=f"evo_{poke['name']}")
    ]])

    await update.message.reply_photo(photo=get_official_image(poke_id), caption=caption, parse_mode="Markdown", reply_markup=kb)
