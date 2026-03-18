import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
OWNER_ID = int(os.environ.get("OWNER_ID", "7728424218"))
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
