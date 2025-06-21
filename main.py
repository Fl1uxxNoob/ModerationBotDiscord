import discord
from discord.ext import commands, tasks
import yaml
import logging
import os
import asyncio
from utils.database import DatabaseManager
from utils.helpers import load_config, load_messages
from utils.permissions import PermissionManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ModerationBot(commands.Bot):
    def __init__(self):
        # Load configuration
        self.config = load_config()
        self.messages = load_messages()
        
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.moderation = True
        
        super().__init__(
            command_prefix=self.config['bot']['prefix'],
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        
        # Initialize managers
        self.db = DatabaseManager()
        self.permissions = PermissionManager(self)
        
        # Store active timeouts and temporary actions
        self.temp_actions = {}
        
    async def setup_hook(self):
        """Setup hook called when bot is starting up"""
        # Initialize database
        await self.db.initialize()
        
        # Load cogs
        cogs_to_load = [
            'cogs.moderation',
            'cogs.logging',
            'cogs.automod',
            'cogs.history',
            'cogs.admin',
            'cogs.help'
        ]
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
        
        # Start background tasks
        self.check_temp_actions.start()
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=self.config['bot']['status']
        )
        await self.change_presence(activity=activity)
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Initialize guild in database
        await self.db.setup_guild(guild.id)
        
        # Send welcome message to system channel if available
        if guild.system_channel:
            embed = discord.Embed(
                title="🛡️ Moderation Bot",
                description=self.messages['welcome']['description'],
                color=0x00ff00
            )
            embed.add_field(
                name="Getting Started",
                value=self.messages['welcome']['getting_started'],
                inline=False
            )
            try:
                await guild.system_channel.send(embed=embed)
            except discord.Forbidden:
                pass  # No permission to send messages
    
    async def on_error(self, event, *args, **kwargs):
        """Global error handler"""
        logger.error(f"Error in event {event}", exc_info=True)
    
    @tasks.loop(minutes=1)
    async def check_temp_actions(self):
        """Check and remove expired temporary actions"""
        try:
            expired_actions = await self.db.get_expired_temp_actions()
            
            for action in expired_actions:
                guild = self.get_guild(action['guild_id'])
                if not guild:
                    continue
                
                user = guild.get_member(action['user_id'])
                if not user:
                    continue
                
                action_type = action['action_type']
                
                if action_type == 'timeout' and user.timed_out_until:
                    try:
                        await user.timeout(None, reason="Temporary timeout expired")
                        logger.info(f"Removed timeout for {user} in {guild}")
                    except discord.Forbidden:
                        logger.warning(f"No permission to remove timeout for {user} in {guild}")
                
                elif action_type == 'tempban':
                    try:
                        await guild.unban(user, reason="Temporary ban expired")
                        logger.info(f"Unbanned {user} from {guild}")
                    except discord.NotFound:
                        pass  # User already unbanned
                    except discord.Forbidden:
                        logger.warning(f"No permission to unban {user} from {guild}")
                
                # Mark action as completed
                await self.db.complete_temp_action(action['id'])
                
        except Exception as e:
            logger.error(f"Error in check_temp_actions: {e}")
    
    @check_temp_actions.before_loop
    async def before_check_temp_actions(self):
        """Wait until bot is ready before starting the task"""
        await self.wait_until_ready()

async def main():
    """Main function to run the bot"""
    bot = ModerationBot()
    
    # Get bot token from environment variable
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable is required!")
        return
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token!")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
