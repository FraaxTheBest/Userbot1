import os
import json
import asyncio
import random
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import Channel
from dotenv import load_dotenv

# Carica .env
load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')
PASSWORD = os.getenv('PASSWORD')

if not API_ID or not API_HASH or not PHONE or not PASSWORD:
    print("ERROR: Variabili ambiente mancanti.")
    exit(1)

# Carica config
if os.path.exists('spam_config.json'):
    with open('spam_config.json') as f:
        config = json.load(f)
else:
    config = {'groups': [], 'interval': 60, 'message': 'Messaggio default'}

spam_groups = config['groups']
spam_interval = config['interval']
spam_message = config['message']

# Stato
is_spamming = False
min_delay = None
max_delay = None
next_group_name = None
next_spam_in = None
spam_messages_random = None
next_group_index = 0
last_spam_time = None

# FIX: Variabili mancanti
media_path = None
group_messages = {}

client = TelegramClient('user.session', API_ID, API_HASH)

async def send_spam():
    global is_spamming, spam_message, spam_messages_random, spam_groups
    global min_delay, max_delay, next_group_name, next_spam_in, media_path, group_messages

    while is_spamming:
        if not spam_groups:
            print("⚠ Nessun gruppo.")
            is_spamming = False
            break

        for group_id in spam_groups:
            if not is_spamming:
                break
            try:
                entity = await client.get_entity(group_id)
                next_group_name = getattr(entity, 'title', str(group_id))

                # Messaggio da inviare
                if str(group_id) in group_messages:
                    message = group_messages[str(group_id)]
                elif spam_messages_random:
                    message = random.choice(spam_messages_random)
                elif spam_message:
                    message = spam_message
                else:
                    print("❌ Nessun messaggio.")
                    is_spamming = False
                    break

                # Invia
                if media_path and os.path.exists(media_path):
                    await client.send_file(group_id, media_path, caption=message)
                else:
                    await client.send_message(group_id, message)

                print(f"✅ Inviato a {next_group_name}")

                delay = random.randint(min_delay, max_delay) if min_delay and max_delay else 60
                next_spam_in = delay
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"❌ Errore su {group_id}: {e}")
                continue

# Altri comandi qui sotto (come nel codice originale)

@client.on(events.NewMessage(pattern=r'\.setmsg\s+(.+)', func=lambda e: not e.is_reply))
async def set_message(event):
    global spam_message, spam_messages_random, media_path, group_messages
    text = event.pattern_match.group(1)

    if "::" in text and "||" in text:
        group_messages = {}
        for part in text.split("||"):
            if "::" in part:
                gid, msg = part.split("::", 1)
                group_messages[gid.strip()] = msg.strip()
        spam_message = None
        spam_messages_random = None
        media_path = None
        await event.respond(f"✅ Impostati {len(group_messages)} messaggi per gruppo.")
        return

    if '//' in text:
        spam_messages_random = [msg.strip() for msg in text.split('//') if msg.strip()]
        spam_message = None
        group_messages = {}
        await event.respond(f"✅ {len(spam_messages_random)} messaggi random impostati.")
    else:
        spam_message = text.strip()
        spam_messages_random = None
        group_messages = {}
        await event.respond("✅ Messaggio singolo impostato.")
    media_path = None

@client.on(events.NewMessage(pattern=r'\.setmsg', func=lambda e: e.is_reply))
async def set_message_with_media(event):
    global spam_message, spam_messages_random, media_path, group_messages
    reply = await event.get_reply_message()

    if not reply:
        await event.respond("⚠ Rispondi a un messaggio.")
        return

    if reply.media:
        media_path = await reply.download_media()
        spam_message = reply.message or ""
        spam_messages_random = None
        group_messages = {}
        await event.respond("✅ Messaggio con media salvato.")
    else:
        spam_message = reply.message or ""
        spam_messages_random = None
        group_messages = {}
        media_path = None
        await event.respond("✅ Messaggio di testo impostato.")

# Start/stop (semplificati qui per focus)
@client.on(events.NewMessage(pattern=r'\.start'))
async def start_spam(event):
    global is_spamming
    if not is_spamming:
        is_spamming = True
        asyncio.create_task(send_spam())
        await event.respond("🚀 Spam avviato.")

@client.on(events.NewMessage(pattern=r'\.stop'))
async def stop_spam(event):
    global is_spamming
    is_spamming = False
    await event.respond("🛑 Spam fermato.")

# Avvio client
async def main():
    while True:
        try:
            await client.start(phone=PHONE, password=PASSWORD)
            print("✅ Bot avviato!")
            await client.run_until_disconnected()
        except Exception as e:
            print(f"❌ Errore: {e}. Riconnessione in 30s...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
