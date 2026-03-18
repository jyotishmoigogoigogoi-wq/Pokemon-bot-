import time

# Per-user state
_states = {}
_cooldowns = {}
_col_loading = {}
_col_last_used = {}

def get_state(uid, key, default=None):
    return _states.get(uid, {}).get(key, default)

def set_state(uid, key, val):
    if uid not in _states: _states[uid] = {}
    _states[uid][key] = val

def del_state(uid, key):
    if uid in _states: _states[uid].pop(key, None)

def check_cooldown(uid, secs=3):
    now = time.time()
    last = _cooldowns.get(uid, 0)
    if now - last < secs:
        return int(secs - (now - last)) + 1
    _cooldowns[uid] = now
    return 0

def is_col_loading(uid): return _col_loading.get(uid, False)
def set_col_loading(uid, val): _col_loading[uid] = val

def get_col_last_used(uid): return _col_last_used.get(uid, 0)
def set_col_last_used(uid, t): _col_last_used[uid] = t
