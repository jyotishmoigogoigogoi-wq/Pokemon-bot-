import random
import re
import aiohttp

LEGENDARY_IDS = [
    144,145,146,150,151,
    243,244,245,249,250,251,
    377,378,379,380,381,382,383,384,385,386,
    480,481,482,483,484,485,486,487,488,489,490,491,492,
    494,638,639,640,641,642,643,644,645,646,647,648,649,
    716,717,718,719,720,721,
    772,773,785,786,787,788,789,790,791,792,800,801,802,
    888,889,890,891,892,893,894,895,896,897,898
]
PSEUDO_IDS = [149,248,376,445,373,635,706,784,887]
BLOCKED_IDS = [493]

async def get_random_pokemon(poke_type="normal"):
    attempts = 0
    while attempts < 10:
        if poke_type == "legendary":
            valid = [i for i in LEGENDARY_IDS if i not in BLOCKED_IDS]
            poke_id = random.choice(valid)
        else:
            poke_id = random.randint(1, 898)
            if poke_id in LEGENDARY_IDS or poke_id in PSEUDO_IDS or poke_id in BLOCKED_IDS:
                attempts += 1
                continue
        break
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://pokeapi.co/api/v2/pokemon/{poke_id}") as r:
            if r.status == 200:
                return await r.json()
    return None

def get_spawn_type():
    roll = random.random() * 100
    if roll < 1: return "legendary"
    if roll < 6: return "shiny"
    return "normal"

def get_gender(is_legendary=False):
    if is_legendary: return "genderless"
    return "male" if random.random() < 0.5 else "female"

def is_legendary(pid): return pid in LEGENDARY_IDS
def is_pseudo(pid): return pid in PSEUDO_IDS
def get_official_image(pid): return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pid}.png"
def get_shiny_image(pid): return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/shiny/{pid}.png"

def normalize_name(name):
    name = name.strip().lower()
    name = re.sub(r'\s+', '-', name)
    name = re.sub(r"[':]", '', name)
    name = name.replace('♀','-f').replace('♂','-m')
    name = name.replace('é','e').replace('è','e').replace('ê','e').replace('à','a')
    return re.sub(r'[^a-z0-9\-]', '', name)
