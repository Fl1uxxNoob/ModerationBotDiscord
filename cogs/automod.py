import discord
from discord.ext import commands
from discord import app_commands
import yaml
from database import add_warning, get_warnings

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.yml', 'r') as f:
            self.config = yaml.safe_load(f)
        self.banned_words = set(self.config['automod']['banned_words'])
        self.warn_threshold = self.config['automod']['warn_threshold']

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        content = message.content.lower().split()
        if any(word in self.banned_words for word in content):
            # issue warning
            add_warning(message.author.id, None, 'Automod: parola non consentita')
            count = get_warnings(message.author.id)
            channel = message.channel
            if count >= self.warn_threshold:
                # mute
                role = discord.utils.get(message.guild.roles, name=self.config['roles']['muted'])
                await message.author.add_roles(role)
                await channel.send(self.config['messages']['automod_mute'].format(
                    member=message.author.mention, count=count
                ))
            else:
                await channel.send(self.config['messages']['automod_warn'].format(
                    member=message.author.mention, count=count, max_warns=self.warn_threshold
                ))
            # delete offending message
            await message.delete()

async def setup(bot):
    await bot.add_cog(AutoMod(bot))