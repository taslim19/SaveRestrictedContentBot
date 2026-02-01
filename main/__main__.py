import glob
from pathlib import Path
from main.utils import load_plugins
import logging
import asyncio
import time
import threading
from . import bot, userbot

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

path = "main/plugins/*.py"
files = glob.glob(path)
for name in files:
    with open(name) as a:
        patt = Path(a.name)
        plugin_name = patt.stem
        load_plugins(plugin_name.replace(".py", ""))

# Pre-load peer cache after plugins are loaded
async def startup_preload():
    """Pre-load peer cache on startup"""
    from main import preload_peer_cache, userbot
    # Wait a bit for userbot to be fully ready
    await asyncio.sleep(2)
    try:
        await preload_peer_cache()
    except Exception as e:
        print(f"Error in startup preload: {e}")

# Run preload in background after a short delay
# Use bot's event loop to run the preload task
import asyncio
def run_preload():
    """Run preload in a separate task"""
    async def _run():
        await startup_preload()
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            asyncio.create_task(_run())
        else:
            loop.run_until_complete(_run())
    except Exception as e:
        print(f"Could not start peer cache preload: {e}")

# Schedule preload to run after bot starts
def delayed_preload():
    """Run preload after a delay"""
    time.sleep(3)  # Wait for bot to fully start
    run_preload()

preload_thread = threading.Thread(target=delayed_preload, daemon=True)
preload_thread.start()

#Don't be a thief 
print("Successfully deployed!")
print("By MaheshChauhan • DroneBots")

if __name__ == "__main__":
    bot.run_until_disconnected()
