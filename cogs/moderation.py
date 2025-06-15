import discord
from discord import app_commands
from discord.ext import commands, tasks
import yaml
from datetime import timedelta

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.yml', 'r') as f:
            self.config = yaml.safe_load(f)

    def get_role(self, guild, role_name):
        return discord.utils.get(guild.roles, name=role_name)

    @app_commands.command(name='mute')
    @app_commands.describe(member='Utente da mutare', duration='Durata in minuti', reason='Motivo')
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: int, reason: str):
        role = self.get_role(interaction.guild, self.config['roles']['muted'])
        await member.add_roles(role, reason=reason)
        # schedule unmute\...
        msg = self.config['messages']['mute_success'].format(
            member=member.mention, duration=f"{duration}min", reason=reason
        )
        await interaction.response.send_message(msg)

    @app_commands.command(name='kick')
    @app_commands.describe(member='Utente da espellere', reason='Motivo')
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await member.kick(reason=reason)
        msg = self.config['messages']['kick_success'].format(
            member=member.mention, reason=reason
        )
        await interaction.response.send_message(msg)

    @app_commands.command(name='ban')
    @app_commands.describe(member='Utente da bannare', duration='Durata in giorni', reason='Motivo')
    async def ban(self, interaction: discord.Interaction, member: discord.Member, duration: int, reason: str):
        await member.ban(reason=reason)
        # schedule unban after duration\...
        msg = self.config['messages']['ban_success'].format(
            member=member.mention, duration=f"{duration}d", reason=reason
        )
        await interaction.response.send_message(msg)

async def setup(bot):
    await bot.add_cog(Moderation(bot))