import os
import json
import asyncio
import random
from telethon import TelegramClient, events   # <-- questa deve esserci OBBLIGATORIO
from telethon.errors import FloodWaitError
from telethon.tl.types import Channel
from telethon.tl.functions.messages import GetDialogFiltersRequest
from dotenv import load_dotenv

# Carica variabili d'ambiente dal file .env
load_dotenv()

# Parametri di autenticazione (prendi da variabili d'ambiente)
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')
PASSWORD = os.getenv('PASSWORD')

# Controlla se le variabili d'ambiente sono caricate correttamente
if not API_ID or not API_HASH or not PHONE or not PASSWORD:
    print("ERROR: Le variabili di ambiente non sono correttamente configurate.")
    exit(1)

# Carica configurazione dal file spam_config.json, se esiste
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

# Parametri di configurazione
spam_groups = config['groups']
spam_interval = config['interval']
spam_message = config['message']
is_spamming = False

# Variabili aggiuntive
min_delay = None
max_delay = None
next_group_name = None
next_spam_in = None
spam_messages_random = None

# Variabili per lo stato dello spam
next_group_index = 0  # Indice del prossimo gruppo da spammare
last_spam_time = None  # Tempo dell'ultimo messaggio inviato

# Inizializza il client Telegram
client = TelegramClient('user.session', API_ID, API_HASH)

async def send_spam():
    global is_spamming, spam_message, spam_messages_random, spam_groups, min_delay, max_delay, next_group_name, next_spam_in

    while is_spamming:
        if not spam_groups:
            print("⚠️ Nessun gruppo configurato. Fermando lo spam.")
            is_spamming = False
            break

        for group_id in spam_groups:
            if not is_spamming:
                break

            try:
                # Ottieni il gruppo attuale
                entity = await client.get_entity(group_id)
                next_group_name = entity.title if hasattr(entity, 'title') else "Sconosciuto"

                # Scegli messaggio
                if spam_messages_random:
                    message = random.choice(spam_messages_random)
                elif spam_message:
                    message = spam_message
                else:
                    print("⚠️ Nessun messaggio impostato. Fermando spam.")
                    is_spamming = False
                    break

                # Invia il messaggio
                await client.send_message(group_id, message)
                print(f"✅ Messaggio inviato a {next_group_name}")

                # Calcola delay random
                if min_delay and max_delay:
                    delay = random.randint(min_delay, max_delay)
                else:
                    delay = 60  # Default 1 minuto

                next_spam_in = delay  # Salva il tempo per .status

                # Aspetta il delay
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"❌ Errore su {group_id}: {e}")
                continue

# Aggiungi il comando .status per mostrare lo stato
@client.on(events.NewMessage(pattern=r'\.status'))
async def check_status(event):
    global is_spamming, min_delay, max_delay, spam_message, spam_messages_random, spam_groups, next_group_name, next_spam_in

    status_text = ""

    if is_spamming:
        status_text += "✅ Spam ATTIVO!\n\n"
    else:
        status_text += "⛔ Spam NON attivo.\n\n"

    # Intervallo random
    if min_delay and max_delay:
        status_text += f"⏱️ Intervallo random: {min_delay // 60} - {max_delay // 60} minuti\n"
    else:
        status_text += "⏱️ Intervallo: default (1 minuto)\n"

    # Modalità di invio
    if spam_messages_random:
        status_text += f"💬 Modalità: Messaggi RANDOM ({len(spam_messages_random)} messaggi)\n"
    elif spam_message:
        status_text += "💬 Modalità: Messaggio SINGOLO\n"
    else:
        status_text += "⚠️ Nessun messaggio impostato!\n"

    # Gruppi caricati
    if spam_groups:
        status_text += f"👥 Gruppi configurati: {len(spam_groups)} gruppi\n"
    else:
        status_text += "⚠️ Nessun gruppo nella lista!\n"

    # Prossimo gruppo + tempo
    if next_group_name and next_spam_in:
        minuti_restanti = next_spam_in // 60
        secondi_restanti = next_spam_in % 60
        status_text += f"\n🔜 Prossimo spam su: **{next_group_name}** tra {minuti_restanti} min {secondi_restanti} sec."
    else:
        status_text += "\n🔜 Nessun spam pianificato."

    await event.respond(status_text)

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
            await event.respond(f"✅ Aggiunti {len(added)} gruppi alla lista spam:\n" + "\n".join([str(a) for a in added]))
        else:
            await event.respond("⚠️ Nessun nuovo gruppo da aggiungere.")

    except Exception as e:
        await event.respond(f"Errore durante l'aggiunta dei gruppi: {str(e)}")


@client.on(events.NewMessage(pattern=r'\.deljoin\s+(-?\d+)'))
async def remove_group(event):
    global spam_groups
    chat_id = int(event.pattern_match.group(1))
    if chat_id in spam_groups:
        spam_groups.remove(chat_id)
        config['groups'] = spam_groups
        with open('spam_config.json', 'w') as f:
            json.dump(config, f, indent=4)
        await event.respond(f"Gruppo {chat_id} rimosso dalla lista spam.")
    else:
        await event.respond("Questo gruppo non è nella lista.")

@client.on(events.NewMessage(pattern=r'\.id\s+(https?://t\.me/\S+)'))
async def get_group_id(event):
    invite_link = event.pattern_match.group(1)
    try:
        group = await client.get_entity(invite_link)
        group_id = group.id
        # Se l'entità è un canale o supergruppo, forziamo il formato con il prefisso "-100"
        if isinstance(group, Channel) and not str(group_id).startswith("-100"):
            group_id = f"-100{abs(group.id)}"
        await event.respond(f"🔹 Nome: {group.title} | ID: {group_id}")
    except Exception as e:
        await event.respond(f"Errore nel recuperare l'ID: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.cleanlist'))
async def clean_list(event):
    global spam_groups
    valid_groups = []
    for group_id in spam_groups:
        try:
            await client.get_entity(group_id)
            valid_groups.append(group_id)
        except Exception as e:
            print(f"Rimuovendo gruppo {group_id}, non sei più presente: {e}")
    spam_groups = valid_groups
    config['groups'] = spam_groups
    with open('spam_config.json', 'w') as f:
        json.dump(config, f, indent=4)
    await event.respond("Lista gruppi pulita! Rimossi quelli in cui non sei più presente.")

@client.on(events.NewMessage(pattern=r'\.dev'))
async def show_developer(event):
    await event.respond("Lo sviluppatore del userbot è @ASTROMOONEY")

@client.on(events.NewMessage(pattern=r'\.help'))
async def show_help(event):
    help_text = (
        "🌟 **Benvenuto nel tuo Spambot!**\n"
        "Usa i comandi qui sotto:\n\n"

        "🚀 **Spam:**\n"
        "• **.start** ➔ Avvia lo spam\n"
        "• **.stop** ➔ Ferma lo spam\n"
        "• **.setmsg <testo>** ➔ Imposta un messaggio fisso oppure più messaggi separati da '//'\n"
        "• **.addtime <min> <max>** ➔ Imposta un delay random tra MIN e MAX minuto\n\n"

        "🛠️ **Gestione Gruppi:**\n"
        "• **.join <id1> <id2> ...** ➔ Aggiunge più gruppi\n"
        "• **.deljoin <id>** ➔ Rimuove un gruppo\n"
        "• **.cleanlist** ➔ Rimuove gruppi dove non fai più parte\n"
        "• **.scanallgroups** ➔ Scansiona e mostra tutti i gruppi\n"
        "• **.listchat** ➔ Mostra gruppi configurati\n"
        "• **.listallids** ➔ Lista ID di tutti i gruppi\n\n"

        "📋 **Informazioni:**\n"
        "• **.status** ➔ Stato del bot\n"
        "• **.dev** ➔ Info sul creatore\n"
    )
    await event.respond(help_text)

@client.on(events.NewMessage(pattern=r'\.listchat'))
async def list_chats(event):
    if not spam_groups:
        await event.respond("❌ Nessun gruppo configurato nella lista spam.")
        return

    chat_details = []
    for chat_id in spam_groups:
        try:
            chat = await client.get_entity(chat_id)
            chat_details.append(f"📌 {chat.title} - `{chat_id}`")
        except Exception as e:
            chat_details.append(f"❌ Gruppo sconosciuto - `{chat_id}` (Errore: {str(e)})")

    await event.respond("**📋 Gruppi configurati:**\n" + "\n".join(chat_details))
    

@client.on(events.NewMessage(pattern=r'\.start'))
async def start_spam(event):
    global is_spamming
    if not is_spamming:
        is_spamming = True
        asyncio.create_task(send_spam())
        await event.respond("Spam avviato.")

@client.on(events.NewMessage(pattern=r'\.stop'))
async def stop_spam(event):
    global is_spamming
    is_spamming = False
    await event.respond("Spam fermato.")

@client.on(events.NewMessage(pattern=r'\.scanallgroups'))
async def scan_all_groups(event):
    global spam_groups
    try:
        dialogs = await client.get_dialogs()
        added_groups = []

        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:  # prende solo gruppi/supergruppi/canali
                chat_id = dialog.id
                chat_name = dialog.name

                if chat_id not in spam_groups:
                    spam_groups.append(chat_id)
                    added_groups.append(f"{chat_name} ({chat_id})")

        # Salva il nuovo spam_config.json
        config['groups'] = spam_groups
        with open('spam_config.json', 'w') as f:
            json.dump(config, f, indent=4)

        if added_groups:
            await event.respond(f"✅ Aggiunti {len(added_groups)} gruppi alla lista spam:\n\n" + "\n".join(added_groups))
        else:
            await event.respond("⚠️ Nessun nuovo gruppo trovato o già tutti presenti nella lista.")
    except Exception as e:
        await event.respond(f"Errore durante la scansione dei gruppi: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.addtime (\d+) (\d+)'))
async def set_random_interval(event):
    global min_delay, max_delay
    min_minutes = int(event.pattern_match.group(1))
    max_minutes = int(event.pattern_match.group(2))

    if min_minutes >= max_minutes:
        await event.respond("⚠️ Il primo numero deve essere minore del secondo!")
    else:
        min_delay = min_minutes * 60  # Converti minuti in secondi
        max_delay = max_minutes * 60
        await event.respond(f"✅ Delay random impostato tra {min_minutes} e {max_minutes} minuti.")

@client.on(events.NewMessage(pattern=r'\.listallids'))
async def list_all_group_ids(event):
    try:
        dialogs = await client.get_dialogs()
        groups_info = []

        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                group_id = dialog.id
                group_name = dialog.name
                groups_info.append(f"{group_name} ➔ `{group_id}`")

        if groups_info:
            response = "📋 **Lista di tutti i gruppi dove sei dentro:**\n\n" + "\n".join(groups_info)
        else:
            response = "❌ Non sei dentro a nessun gruppo."

        await event.respond(response)
    except Exception as e:
        await event.respond(f"Errore durante il recupero dei gruppi: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.setmsg (.+)'))
async def set_message(event):
    global spam_message, spam_messages_random
    text = event.pattern_match.group(1)

    if '//' in text:
        # Se ci sono '//' ➔ più messaggi
        spam_messages_random = [msg.strip() for msg in text.split('//')]
        spam_message = None
        await event.respond(f"✅ Impostati {len(spam_messages_random)} messaggi random.")
    else:
        # Se no ➔ messaggio singolo
        spam_message = text.strip()
        spam_messages_random = None
        await event.respond("✅ Messaggio singolo impostato correttamente.")

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
            continue

if __name__ == '__main__':
    print("Avvio del bot...")
    asyncio.run(main())
