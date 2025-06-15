import yaml
import discord
from discord.ext import commands, tasks
from database import init_db

# Load config
def load_config():
    with open('config.yml', 'r') as f:
        return yaml.safe_load(f)

config = load_config()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database
token = config['token']
init_db()

# Load cogs
cogs = ['cogs.moderation', 'cogs.warnings', 'cogs.automod']
for cog in cogs:
    bot.load_extension(cog)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

bot.run(token)