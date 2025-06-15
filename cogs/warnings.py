import discord
from discord import app_commands
from discord.ext import commands
from database import add_warning, get_warnings
import yaml

class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.yml', 'r') as f:
            self.config = yaml.safe_load(f)

    @app_commands.command(name='warn')
    @app_commands.describe(member='Utente da avvertire', reason='Motivo')
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        add_warning(member.id, interaction.user.id, reason)
        count = get_warnings(member.id)
        msg = self.config['messages']['warn_message'].format(
            member=member.mention, reason=reason, count=count
        )
        await interaction.response.send_message(msg)

async def setup(bot):
    await bot.add_cog(Warnings(bot))