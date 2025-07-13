import asyncio
import os
import random
from datetime import datetime, time
from telethon import TelegramClient, events

# Parametri di autenticazione (prendi da variabili d'ambiente)
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')
PASSWORD = os.getenv('PASSWORD')

client = TelegramClient('userbot', API_ID, API_HASH)

# --- VARIABILI GLOBALI ---
spam_message = None           # messaggio singolo
spam_messages_random = None   # lista messaggi random
group_messages = {}           # messaggi specifici per gruppo {group_id: messaggio}
scheduled_group_msgs = {}     # messaggi schedulati per gruppo {group_id: [(time, messaggio), ...]}
list_of_group_ids = []        # lista gruppi su cui spam

is_spamming = False           # flag spam attivo
delay_min = 60                # delay minimo in secondi
delay_max = 180               # delay massimo in secondi

media_path = None             # percorso media per messaggi con file

# --- FUNZIONE PER OTTENERE NOME GRUPPO ---
def get_group_name(entity, group_id):
    return getattr(entity, 'title', str(group_id))

# --- FUNZIONE SPAM ---
async def send_spam():
    global is_spamming
    while is_spamming:
        if not list_of_group_ids:
            print("⚠ Lista gruppi vuota, fermo spam.")
            is_spamming = False
            break
        
        for group_id in list_of_group_ids:
            try:
                if str(group_id) in group_messages:
                    msg = group_messages[str(group_id)]
                elif spam_messages_random:
                    msg = random.choice(spam_messages_random)
                elif spam_message:
                    msg = spam_message
                else:
                    print("⚠ Nessun messaggio impostato. Fermando spam.")
                    is_spamming = False
                    break
                
                if media_path and os.path.exists(media_path):
                    await client.send_file(int(group_id), media_path, caption=msg)
                else:
                    await client.send_message(int(group_id), msg)
                
                print(f"✅ Messaggio inviato a {group_id}")
            except Exception as e:
                print(f"Errore invio messaggio a {group_id}: {e}")
            await asyncio.sleep(random.randint(delay_min, delay_max))
        await asyncio.sleep(1)

# --- TASK MESSAGGI SCHEDULATI ---
async def scheduled_messages_task():
    while True:
        now = datetime.now().time()
        for group_id, msgs in scheduled_group_msgs.items():
            to_remove = []
            for i, (msg_time, msg) in enumerate(msgs):
                if now >= msg_time:
                    try:
                        await client.send_message(int(group_id), msg)
                        print(f"✅ Messaggio schedulato inviato a {group_id}")
                    except Exception as e:
                        print(f"Errore invio messaggio schedulato a {group_id}: {e}")
                    to_remove.append(i)
            # rimuovi messaggi inviati
            for i in reversed(to_remove):
                msgs.pop(i)
        await asyncio.sleep(30)

# --- HANDLER COMANDI ---

# .start - Avvia lo spam
@client.on(events.NewMessage(pattern=r'^\.start$'))
async def start_spam(event):
    global is_spamming
    if is_spamming:
        await event.respond("⚠ Lo spam è già attivo.")
        return
    if not (spam_message or spam_messages_random or group_messages):
        await event.respond("❌ Nessun messaggio impostato, usa .setmsg prima.")
        return
    if not list_of_group_ids:
        await event.respond("❌ Lista gruppi vuota, aggiungi almeno un gruppo con .join")
        return
    is_spamming = True
    await event.respond("✅ Avviato lo spam.")
    client.loop.create_task(send_spam())

# .stop - Ferma lo spam
@client.on(events.NewMessage(pattern=r'^\.stop$'))
async def stop_spam(event):
    global is_spamming
    if not is_spamming:
        await event.respond("⚠ Lo spam non è attivo.")
        return
    is_spamming = False
    await event.respond("✅ Spam fermato.")

# .status - Mostra stato attuale
@client.on(events.NewMessage(pattern=r'^\.status$'))
async def status(event):
    status_msg = "🟢 Spam attivo" if is_spamming else "🔴 Spam fermo"
    tot_groups = len(list_of_group_ids)
    msg_set = "✅ Messaggio singolo impostato." if spam_message else ""
    msg_rand = f"✅ {len(spam_messages_random)} messaggi random impostati." if spam_messages_random else ""
    msg_group = f"✅ Messaggi specifici per {len(group_messages)} gruppi." if group_messages else ""
    await event.respond(
        f"📊 Stato Bot:\n"
        f"{status_msg}\n"
        f"🗂 Gruppi in lista: {tot_groups}\n"
        f"{msg_set}\n{msg_rand}\n{msg_group}\n"
        f"⏳ Delay random: {delay_min}s - {delay_max}s"
    )

# .setmsg <testo> oppure con media (risposta)
@client.on(events.NewMessage(pattern=r'^\.setmsg(?:\s+(.+))?$', func=lambda e: not e.is_reply))
async def set_message(event):
    global spam_message, spam_messages_random, media_path, group_messages

    text = event.pattern_match.group(1)
    if not text:
        await event.respond("❌ Usa .setmsg <messaggio> oppure .setmsg id1::msg1 || id2::msg2 || ...")
        return

    # Messaggi specifici per gruppi
    if "::" in text and "||" in text:
        parts = [p.strip() for p in text.split("||")]
        group_messages.clear()
        for part in parts:
            if "::" in part:
                gid, msg = part.split("::", 1)
                group_messages[gid.strip()] = msg.strip()
        spam_message = None
        spam_messages_random = None
        media_path = None
        await event.respond(f"✅ Impostati {len(group_messages)} messaggi specifici per gruppi.")
        return

    # Messaggi random divisi da //
    if '//' in text:
        spam_messages_random = [m.strip() for m in text.split("//")]
        spam_message = None
        group_messages.clear()
        media_path = None
        await event.respond(f"✅ Impostati {len(spam_messages_random)} messaggi random.")
        return

    # Messaggio singolo
    spam_message = text.strip()
    spam_messages_random = None
    group_messages.clear()
    media_path = None
    await event.respond("✅ Messaggio singolo impostato.")

# .setmsg con media (risposta)
@client.on(events.NewMessage(pattern=r'^\.setmsg$', func=lambda e: e.is_reply))
async def set_message_with_media(event):
    global spam_message, spam_messages_random, media_path, group_messages

    replied = await event.get_reply_message()
    if not replied:
        await event.respond("❌ Devi rispondere a un messaggio con testo o media.")
        return

    if replied.media:
        file_path = await replied.download_media()
        media_path = file_path
        spam_message = replied.message or ""
        spam_messages_random = None
        group_messages.clear()
        await event.respond("✅ Messaggio con media impostato.")
    else:
        spam_message = replied.message or ""
        spam_messages_random = None
        group_messages.clear()
        media_path = None
        await event.respond("✅ Messaggio di testo impostato.")

# .addtime <minuti> - modifica delay
@client.on(events.NewMessage(pattern=r'^\.addtime\s+(\d+)$'))
async def add_time(event):
    global delay_min, delay_max
    minuti = int(event.pattern_match.group(1))
    if minuti < 1 or minuti > 60*60:
        await event.respond("❌ Minuti non validi, scegli tra 1 e 3600.")
        return
    delay_min = minuti * 60
    delay_max = delay_min + 60  # un minuto in più
    await event.respond(f"✅ Delay impostato tra {delay_min}s e {delay_max}s.")

# .listchat - mostra lista gruppi con nomi
@client.on(events.NewMessage(pattern=r'^\.listchat$'))
async def list_chat(event):
    if not list_of_group_ids:
        await event.respond("❌ Lista gruppi vuota.")
        return
    msg = "📋 Lista gruppi:\n"
    for gid in list_of_group_ids:
        try:
            entity = await client.get_entity(int(gid))
            name = get_group_name(entity, gid)
        except Exception:
            name = str(gid)
        msg += f"- {name} (ID: {gid})\n"
    await event.respond(msg)

# .listallids - mostra solo ID gruppi
@client.on(events.NewMessage(pattern=r'^\.listallids$'))
async def list_all_ids(event):
    if not list_of_group_ids:
        await event.respond("❌ Lista gruppi vuota.")
        return
    msg = "📋 Lista ID gruppi:\n" + "\n".join(str(g) for g in list_of_group_ids)
    await event.respond(msg)

# .cleanlist - pulisce lista gruppi
@client.on(events.NewMessage(pattern=r'^\.cleanlist$'))
async def clean_list(event):
    global list_of_group_ids
    list_of_group_ids.clear()
    await event.respond("✅ Lista gruppi pulita.")

# .join <link> - aggiungi gruppo
@client.on(events.NewMessage(pattern=r'^\.join\s+(.+)$'))
async def join_group(event):
    link = event.pattern_match.group(1).strip()
    try:
        result = await client(telethon.functions.channels.JoinChannelRequest(link))
        # ottieni id gruppo e aggiungi lista
        entity = await client.get_entity(link)
        gid = entity.id
        if gid not in list_of_group_ids:
            list_of_group_ids.append(gid)
        await event.respond(f"✅ Iscritto al gruppo {get_group_name(entity, gid)} (ID: {gid})")
    except Exception as e:
        await event.respond(f"❌ Errore join: {e}")

# .deljoin <group_id> - rimuovi gruppo
@client.on(events.NewMessage(pattern=r'^\.deljoin\s+(\d+)$'))
async def del_join(event):
    global list_of_group_ids
    gid = int(event.pattern_match.group(1))
    if gid in list_of_group_ids:
        list_of_group_ids.remove(gid)
        await event.respond(f"✅ Rimosso gruppo con ID {gid} dalla lista.")
    else:
        await event.respond("❌ Gruppo non presente nella lista.")

# .id - mostra ID utente
@client.on(events.NewMessage(pattern=r'^\.id$'))
async def show_id(event):
    me = await client.get_me()
    await event.respond(f"🆔 Il tuo ID utente è: {me.id}")

# .dev - info sviluppatore
@client.on(events.NewMessage(pattern=r'^\.dev$'))
async def dev_info(event):
    await event.respond("🤖 Bot creato da te o dallo sviluppatore.\nContatto: tuo@email.com")

# .addgroupmsg <group_id> <HH:MM> <messaggio> - messaggi programmati per gruppo
@client.on(events.NewMessage(pattern=r'^\.addgroupmsg\s+(\d+)\s+(\d{2}:\d{2})\s+(.+)$'))
async def add_group_msg(event):
    group_id = event.pattern_match.group(1)
    time_str = event.pattern_match.group(2)
    msg = event.pattern_match.group(3).strip()
    try:
        msg_time = datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        await event.respond("❌ Formato orario non valido, usa HH:MM 24h.")
        return
    if group_id not in scheduled_group_msgs:
        scheduled_group_msgs[group_id] = []
    scheduled_group_msgs[group_id].append((msg_time, msg))
    await event.respond(f"✅ Messaggio programmato per il gruppo {group_id} alle {time_str}.")

# .help - lista comandi
@client.on(events.NewMessage(pattern=r'^\.help$'))
async def help_handler(event):
    help_text = (
        "📜 *Comandi disponibili:*\n"
        ".start - Avvia lo spam\n"
        ".stop - Ferma lo spam\n"
        ".setmsg <testo> - Imposta messaggio singolo\n"
        ".setmsg (rispondi a media o testo) - Imposta messaggio con media\n"
        ".setmsg id1::msg1 || id2::msg2 - Messaggi specifici per gruppi\n"
        ".addtime <minuti> - Modifica delay random (in minuti)\n"
        ".status - Mostra stato attuale\n"
        ".addgroupmsg <group_id> <HH:MM> <messaggio> - Programma messaggio per gruppo\n"
        ".listchat - Lista gruppi (con nomi)\n"
        ".listallids - Lista ID gruppi\n"
        ".cleanlist - Pulisce lista gruppi\n"
        ".join <link> - Aggiungi gruppo\n"
        ".deljoin <group_id> - Rimuovi gruppo\n"
        ".id - Mostra tuo ID utente\n"
        ".dev - Info sviluppatore\n"
        ".help - Mostra questo aiuto\n"
    )
    await event.respond(help_text)

# --- MAIN LOOP robusto con gestione riconnessione ---
async def main():
    while True:
        try:
            print("Avvio bot...")
            await client.start(phone=PHONE, password=PASSWORD)
            print("Bot avviato con successo!")
            client.loop.create_task(scheduled_messages_task())
            await client.run_until_disconnected()
        except Exception as e:
            print(f"Errore di connessione: {e}")
            print("Riconnessione tra 30 secondi...")
            await asyncio.sleep(30)
            continue

if __name__ == '__main__':
    print("Avvio del bot...")
    asyncio.run(main())
