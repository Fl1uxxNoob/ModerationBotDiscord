import yaml
import discord
from discord.ext import commands
import asyncio
import logging
from database import init_db

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load config
def load_config():
    try:
        with open('config.yml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("Errore: file config.yml non trovato!")
        exit(1)
    except yaml.YAMLError as e:
        print(f"Errore nel parsing del file config.yml: {e}")
        exit(1)

config = load_config()

# Setup intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database
token = config.get('token')
if not token or token == "BOT_TOKEN_HERE":
    print("Errore: Token del bot non configurato in config.yml!")
    exit(1)

async def load_extensions():
    """Carica le estensioni in modo asincrono"""
    cogs = ['cogs.moderation', 'cogs.warnings', 'cogs.automod']
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Caricato: {cog}")
        except Exception as e:
            print(f"❌ Errore nel caricamento di {cog}: {e}")

@bot.event
async def on_ready():
    print(f'🤖 Bot avviato come {bot.user} (ID: {bot.user.id})')
    
    # Sincronizza comandi slash
    try:
        # Per sviluppo: sincronizza per una guild specifica (più veloce)
        # guild = discord.Object(id=YOUR_GUILD_ID)  # Sostituisci con l'ID del tuo server
        # bot.tree.copy_global_to(guild=guild)
        # synced = await bot.tree.sync(guild=guild)
        
        # Per produzione: sincronizza globalmente
        synced = await bot.tree.sync()
        print(f"✅ Sincronizzati {len(synced)} comandi slash")
    except Exception as e:
        print(f"❌ Errore nella sincronizzazione: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Gestione errori comandi tradizionali"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Non hai i permessi per usare questo comando!")
    else:
        print(f"Errore comando: {error}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Gestione errori comandi slash"""
    if isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Non hai i permessi per usare questo comando!", ephemeral=True)
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏰ Comando in cooldown. Riprova tra {error.retry_after:.2f} secondi.", ephemeral=True)
    else:
        print(f"Errore comando slash: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Si è verificato un errore!", ephemeral=True)

async def main():
    """Funzione principale per avviare il bot"""
    # Inizializza database
    init_db()
    print("✅ Database inizializzato")
    
    # Carica estensioni
    await load_extensions()
    
    # Avvia bot
    try:
        await bot.start(token)
    except discord.LoginFailure:
        print("❌ Token del bot non valido!")
    except Exception as e:
        print(f"❌ Errore nell'avvio del bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())