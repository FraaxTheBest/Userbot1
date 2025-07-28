import os
import json
import asyncio
import random
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from datetime import datetime, timedelta
from telethon.tl.types import Channel
from dotenv import load_dotenv

group_messages = {}
media_path = None

load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')
PASSWORD = os.getenv('PASSWORD')

if not API_ID or not API_HASH or not PHONE or not PASSWORD:
    print("ERROR: Le variabili di ambiente non sono correttamente configurate.")
    exit(1)

def load_config():
    if os.path.exists('spam_config.json'):
        with open('spam_config.json', 'r') as f:
            return json.load(f)
    else:
        print("Il file spam_config.json non è stato trovato, usando la configurazione predefinita.")
        return {
            'groups': [],
            'interval': 60,
            'message': 'Spam messaggio predefinito'
        }

config = load_config()

spam_groups = config['groups']
spam_interval = config['interval']
spam_message = config['message']
is_spamming = False

min_delay = None
max_delay = None
next_group_name = None
next_spam_in = None
spam_messages_random = None

spam_counter = 0
spam_mode = "manuale"
spam_start_time = None
spam_end_time = None
spam_started_at = None
spam_custom_messages = {}

start_hour = None
end_hour = None
spam_timer_active = False

client = TelegramClient('user.session', API_ID, API_HASH)

async def spam_timer_loop():
    global is_spamming, spam_started_at
    while spam_timer_active:
        now = datetime.now()
        current_hour = now.hour

        if start_hour <= current_hour < end_hour:
            if not is_spamming:
                is_spamming = True
                spam_started_at = datetime.now()
                asyncio.create_task(send_spam())
                print("🔄 Spam automatico avviato")
        else:
            if is_spamming:
                is_spamming = False
                print("🛑 Spam automatico fermato")
        await asyncio.sleep(60)

async def send_spam():
    global is_spamming, spam_message, spam_messages_random, spam_groups, min_delay, max_delay, next_group_name, next_spam_in, spam_counter

    while is_spamming:
        if not spam_groups:
            print("⚠ Nessun gruppo configurato. Fermando lo spam.")
            is_spamming = False
            break

        for group_id in spam_groups:
            if not is_spamming:
                break
            try:
                entity = await client.get_entity(group_id)
                next_group_name = getattr(entity, 'title', str(group_id))

                if str(group_id) in group_messages:
                    message = group_messages[str(group_id)]
                elif spam_messages_random:
                    message = random.choice(spam_messages_random)
                elif spam_message:
                    message = spam_message
                else:
                    print("⚠ Nessun messaggio impostato. Fermando spam.")
                    is_spamming = False
                    break

                if media_path and os.path.exists(media_path):
                    await client.send_file(group_id, media_path, caption=message)
                else:
                    await client.send_message(group_id, message)

                spam_counter += 1
                print(f"✅ Messaggio inviato a {next_group_name}")
                delay = random.randint(min_delay, max_delay) if min_delay and max_delay else 60
                next_spam_in = delay
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"❌ Errore su {group_id}: {e}")
                continue
                @client.on(events.NewMessage(pattern=r"^\\.status\\b"))
                async def handler_status(event):
                    global spam_mode, start_hour, end_hour, spam_message, group_messages, spam_groups
                    global spam_counter, spam_started_at, is_spamming

    def format_time(dt):
        return dt.strftime("%H:%M") if dt else "N/D"

    status_parts = []

    if spam_mode == "automatica":
        status_parts.append("🧰 **Modalità spam**: Automatica (Giornaliera)")
        if start_hour is not None and end_hour is not None:
            status_parts.append(f"🕒 **Orari spam**: dalle {start_hour:02d}:00 alle {end_hour:02d}:00")
        else:
            status_parts.append("🕒 **Orari spam**: Non impostati")
        status_parts.append(f"🕒 **Avviato automaticamente alle**: {format_time(spam_started_at)}" if spam_started_at else "🕒 **Avvio**: N/D")
    else:
        status_parts.append("🧰 **Modalità spam**: Manuale")
        status_parts.append(f"🕒 **Inizio spam**: {format_time(spam_started_at)}" if spam_started_at else "🕒 **Inizio spam**: N/D")

    stato = "✅ **Attivo**" if is_spamming else "❌ **Non attivo**"
    status_parts.append(f"📡 **Stato attuale**: {stato}")
    status_parts.append(f"📬 **Messaggi inviati**: {spam_counter}")

    if spam_message:
        status_parts.append(f"📝 **Messaggio globale impostato**:\\n\\n{spam_message}")
    elif not spam_message and not group_messages:
        status_parts.append("ℹ️ **Nessun messaggio di spam impostato.**")

    if group_messages:
        status_parts.append("✏️ **Messaggi personalizzati per gruppo**:")
        for group_id, msg in group_messages.items():
            try:
                entity = await client.get_entity(group_id)
                name = entity.title or entity.username or str(group_id)
            except:
                name = str(group_id)
            status_parts.append(f\"\"\"• {name} (ID: {group_id}):\\n\\n{msg}\\n\"\"\")
    if spam_groups:
        status_parts.append("👥 **Gruppi attivi in spam**:")
        for group_id in spam_groups:
            try:
                entity = await client.get_entity(group_id)
                name = entity.title or entity.username or str(group_id)
            except:
                name = str(group_id)
            status_parts.append(f"• {name}")
    else:
        status_parts.append("👥 **Gruppi attivi in spam**: Nessuno")

    msg = ""
    for part in status_parts:
        if len(msg) + len(part) + 2 > 4000:
            await event.reply(msg)
            msg = ""
        msg += part + "\\n\\n"

    if msg:
        await event.reply(msg)

@client.on(events.NewMessage(pattern=r\"\\.start\"))
async def start_spam(event):
    global is_spamming, spam_started_at, spam_mode
    if not is_spamming:
        if spam_mode == \"manuale\":
            is_spamming = True
            spam_started_at = datetime.now()
            asyncio.create_task(send_spam())
            await event.respond(\"Spam avviato.\")
        else:
            await event.respond(\"⚠ Modalità automatica attiva - usa .settime per modificare\")

@client.on(events.NewMessage(pattern=r\"\\.stoptimer\"))
async def stop_timer(event):
    global spam_timer_active, spam_mode
    spam_timer_active = False
    spam_mode = \"manuale\"
    await event.respond(\"⏹️ Timer automatico disattivato. Ora in modalità manuale.\")

@client.on(events.NewMessage(pattern=r\"\\.settime (\\d{1,2}) (\\d{1,2})\"))
async def handler_settime(event):
    global start_hour, end_hour, spam_timer_active, spam_mode, is_spamming
    start_hour = int(event.pattern_match.group(1))
    end_hour = int(event.pattern_match.group(2))
    spam_timer_active = True
    spam_mode = \"automatica\"
    is_spamming = False
    asyncio.create_task(spam_timer_loop())
    await event.reply(f\"⏰ Timer attivo: spam dalle **{start_hour:02d}:00** alle **{end_hour:02d}:00** ogni giorno.\")

@client.on(events.NewMessage(pattern=r\"\\.stop\"))
async def stop_spam(event):
    global is_spamming
    is_spamming = False
    await event.respond(\"Spam fermato.\")

@client.on(events.NewMessage(pattern=r\"\\.dev\"))
async def show_developer(event):
    await event.respond(\"Lo sviluppatore del userbot è @ASTROMOONEY\")

@client.on(events.NewMessage(pattern=r\"\\.help\"))
async def show_help(event):
    help_text = (
        \"🌟 Benvenuto nel tuo Spambot!\\n\"
        \"Usa i comandi qui sotto:\\n\\n\"
        \"🚀 Spam:\\n\"
        \"• .start ➔ Avvia lo spam\\n\"
        \"• .stop ➔ Ferma lo spam\\n\"
        \"• .setmsg <testo> ➔ Imposta un messaggio fisso oppure più messaggi separati da '//'\\n\"
        \"• .settime ➔ Programma lo spam tra due orari precisi ogni giorno\\n\"
        \"• .stoptimer ➔ ferma lo spam automatico giornaliero\\n\"
        \"• .addtime <min> <max> ➔ Imposta un delay random tra MIN e MAX minuto\\n\\n\"
        \"🛠 Gestione Gruppi:\\n\"
        \"• .join <id1> <id2> ... ➔ Aggiunge più gruppi\\n\"
        \"• .deljoin <id> ➔ Rimuove un gruppo\\n\"
        \"• .cleanlist ➔ Rimuove gruppi dove non fai più parte\\n\"
        \"• .scanallgroups ➔ Scansiona e mostra tutti i gruppi\\n\"
        \"• .setgroupmsg <id> <msg> ➔ Imposta un messaggio specifico per un gruppo specifico\\n\"
        \"• .listchat ➔ Mostra gruppi configurati\\n\"
        \"• .listallids ➔ Lista ID di tutti i gruppi di cui sei dentro\\n\\n\"
        \"📋 Informazioni:\\n\"
        \"• .status ➔ Stato dello spam\\n\"
        \"• .dev ➔ Info sul creatore\\n\"
    )
    await event.respond(help_text)
    @client.on(events.NewMessage(pattern=r'\.join\s+(.+)'))
async def join_multiple_groups(event):
    global spam_groups
    ids_text = event.pattern_match.group(1)
    try:
        ids = ids_text.split()
        added = []

        for id_str in ids:
            chat_id = int(id_str)
            if chat_id not in spam_groups:
                spam_groups.append(chat_id)
                added.append(chat_id)

        config['groups'] = spam_groups
        with open('spam_config.json', 'w') as f:
            json.dump(config, f, indent=4)

        if added:
            await event.respond(f"✅ Aggiunti {len(added)} gruppi:\n" + "\n".join([str(a) for a in added]))
        else:
            await event.respond("⚠ Nessun nuovo gruppo da aggiungere.")
    except Exception as e:
        await event.respond(f"Errore: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.deljoin\s+(-?\d+)'))
async def remove_group(event):
    global spam_groups
    chat_id = int(event.pattern_match.group(1))
    if chat_id in spam_groups:
        spam_groups.remove(chat_id)
        config['groups'] = spam_groups
        with open('spam_config.json', 'w') as f:
            json.dump(config, f, indent=4)
        await event.respond(f"Rimosso: {chat_id}")
    else:
        await event.respond("Non è nella lista.")

@client.on(events.NewMessage(pattern=r'\.cleanlist'))
async def clean_list(event):
    global spam_groups
    valid = []
    for gid in spam_groups:
        try:
            await client.get_entity(gid)
            valid.append(gid)
        except:
            print(f"Rimosso: {gid}")
    spam_groups = valid
    config['groups'] = spam_groups
    with open('spam_config.json', 'w') as f:
        json.dump(config, f, indent=4)
    await event.respond("✅ Lista gruppi pulita.")

@client.on(events.NewMessage(pattern=r'\.scanallgroups'))
async def scan_all_groups(event):
    global spam_groups
    try:
        dialogs = await client.get_dialogs()
        added = []
        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                cid = dialog.id
                if cid not in spam_groups:
                    spam_groups.append(cid)
                    added.append(f"{dialog.name} ({cid})")

        config['groups'] = spam_groups
        with open('spam_config.json', 'w') as f:
            json.dump(config, f, indent=4)

        if added:
            await event.respond("✅ Aggiunti:\n" + "\n".join(added))
        else:
            await event.respond("⚠ Nessun nuovo gruppo.")
    except Exception as e:
        await event.respond(f"Errore: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.setgroupmsg\s+(-?\d+)::(.+)'))
async def set_group_specific_msg(event):
    global group_messages
    gid = event.pattern_match.group(1).strip()
    msg = event.pattern_match.group(2).strip()
    group_messages[gid] = msg
    await event.respond(f"✅ Messaggio impostato per gruppo {gid}")

@client.on(events.NewMessage(pattern=r'\.addtime (\d+) (\d+)'))
async def set_random_interval(event):
    global min_delay, max_delay
    min_minutes = int(event.pattern_match.group(1))
    max_minutes = int(event.pattern_match.group(2))
    if min_minutes >= max_minutes:
        await event.respond("⚠ Il primo numero deve essere minore del secondo!")
    else:
        min_delay = min_minutes * 60
        max_delay = max_minutes * 60
        await event.respond(f"✅ Delay impostato tra {min_minutes} e {max_minutes} minuti.")

@client.on(events.NewMessage(pattern=r'\.setmsg\s+([\s\S]+)', func=lambda e: not e.is_reply))
async def set_message(event):
    global spam_message, spam_messages_random, media_path, group_messages
    text = event.pattern_match.group(1).strip()
    if "::" in text and "||" in text:
        parts = [p.strip() for p in text.split("||")]
        group_messages = {}
        for part in parts:
            if "::" in part:
                gid, msg = part.split("::", 1)
                group_messages[gid.strip()] = msg.strip()
        spam_message = None
        spam_messages_random = None
        media_path = None
        await event.respond(f"✅ {len(group_messages)} messaggi per gruppi.")
        return
    if '//' in text:
        spam_messages_random = [msg.strip() for msg in text.split('//')]
        spam_message = None
        group_messages = {}
        media_path = None
        await event.respond(f"✅ {len(spam_messages_random)} messaggi random.")
        return
    spam_message = text
    spam_messages_random = None
    group_messages = {}
    media_path = None
    await event.respond("✅ Messaggio singolo impostato.")

@client.on(events.NewMessage(pattern=r'\.setmsg', func=lambda e: e.is_reply))
async def set_message_with_media(event):
    global spam_message, spam_messages_random, media_path, group_messages
    replied = await event.get_reply_message()
    if not replied:
        await event.respond("⚠ Rispondi a un messaggio.")
        return
    if replied.media:
        file = await replied.download_media()
        media_path = file
        spam_message = replied.message or ""
        media_type = "CON media"
    else:
        spam_message = replied.message or ""
        media_path = None
        media_type = "di TESTO"
    spam_messages_random = None
    group_messages = {}
    await event.respond(f"✅ Messaggio {media_type} impostato.")

@client.on(events.NewMessage(pattern=r'\.listallids'))
async def list_all_group_ids(event):
    dialogs = await client.get_dialogs()
    lines = [f"{d.name} ➔ {d.id}" for d in dialogs if d.is_group or d.is_channel]
    if lines:
        for i in range(0, len(lines), 50):
            await event.respond("\n".join(lines[i:i+50]))
    else:
        await event.respond("❌ Nessun gruppo trovato.")

async def main():
    while True:
        try:
            print("Avvio bot...")
            await client.start(phone=PHONE, password=PASSWORD)
            print("Bot avviato con successo!")
            await client.run_until_disconnected()
        except Exception as e:
            print(f"Errore di connessione: {str(e)}")
            print("Riconnessione tra 30 secondi...")
            await asyncio.sleep(30)

if __name__ == '__main__':
    print("Avvio del bot...")
    asyncio.run(main())
