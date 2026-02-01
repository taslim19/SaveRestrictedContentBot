#Github.com/Vasusen-code

from pyrogram import Client

from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from decouple import config
import logging, time, sys, asyncio

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

# Filter out peer ID invalid errors from Pyrogram dispatcher
class PeerIdErrorFilter(logging.Filter):
    def filter(self, record):
        # Suppress "Peer id invalid" errors - these happen when bot receives updates about channels it hasn't accessed
        if "Peer id invalid" in str(record.getMessage()):
            return False
        return True

# Apply filter to Pyrogram logger
pyrogram_logger = logging.getLogger("pyrogram")
pyrogram_logger.addFilter(PeerIdErrorFilter())

# Also filter asyncio errors
asyncio_logger = logging.getLogger("asyncio")
asyncio_logger.addFilter(PeerIdErrorFilter())

# variables
API_ID = config("API_ID", default=None, cast=int)
API_HASH = config("API_HASH", default=None)
BOT_TOKEN = config("BOT_TOKEN", default=None)
SESSION = config("SESSION", default=None)
AUTH = config("AUTH", default=None, cast=int)
# Optional: Comma-separated list of channel/group IDs or usernames to pre-populate peer cache
PRELOAD_CHATS = config("PRELOAD_CHATS", default=None)

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN) 

userbot = Client("saverestricted", session_string=SESSION, api_hash=API_HASH, api_id=API_ID) 

try:
    userbot.start()
except BaseException:
    print("Userbot Error ! Have you added SESSION while deploying??")
    sys.exit(1)

# Function to pre-populate peer cache on startup
async def preload_peer_cache():
    """Pre-populate Pyrogram's peer cache by accessing known channels/groups"""
    if not PRELOAD_CHATS:
        print("No PRELOAD_CHATS configured. Skipping peer cache preload.")
        return
    
    chats_to_preload = [chat.strip() for chat in PRELOAD_CHATS.split(',') if chat.strip()]
    if not chats_to_preload:
        return
    
    print(f"Pre-loading peer cache for {len(chats_to_preload)} chat(s)...")
    success_count = 0
    failed_count = 0
    
    for chat_identifier in chats_to_preload:
        try:
            # Try to access the chat to populate cache
            chat = await userbot.get_chat(chat_identifier)
            print(f"✓ Pre-loaded peer cache for: {chat.title if hasattr(chat, 'title') else chat_identifier} (ID: {chat.id})")
            success_count += 1
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"✗ Failed to pre-load peer cache for {chat_identifier}: {e}")
            failed_count += 1
    
    print(f"Peer cache preload complete: {success_count} succeeded, {failed_count} failed")

# Pre-load peer cache will be called after userbot starts
# This is handled in __main__.py to ensure proper async context

Bot = Client(
    "SaveRestricted",
    bot_token=BOT_TOKEN,
    api_id=int(API_ID),
    api_hash=API_HASH
)    

try:
    Bot.start()
except Exception as e:
    print(e)
    sys.exit(1)
