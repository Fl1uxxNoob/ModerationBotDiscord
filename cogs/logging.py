import discord
from discord.ext import commands
from datetime import datetime
import logging
from utils.helpers import create_embed, clean_content, truncate_text

logger = logging.getLogger(__name__)

class LoggingCog(commands.Cog, name="Logging"):
    def __init__(self, bot):
        self.bot = bot
    
    def get_log_channel(self, guild: discord.Guild) -> discord.TextChannel:
        """Get the logging channel for a guild"""
        log_channel_name = self.bot.config['moderation']['log_channel_name']
        return discord.utils.get(guild.text_channels, name=log_channel_name)
    
    async def send_log(self, guild: discord.Guild, embed: discord.Embed):
        """Send a log message to the logging channel"""
        if not self.bot.config['logging']['enabled']:
            return
        
        log_channel = self.get_log_channel(guild)
        if not log_channel:
            return
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning(f"No permission to send logs in {guild.name}")
        except Exception as e:
            logger.error(f"Error sending log in {guild.name}: {e}")
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log deleted messages"""
        if not self.bot.config['logging']['events']['message_delete']:
            return
        
        if message.guild is None or message.author.bot:
            return
        
        # Log to database
        await self.bot.db.log_message_action(
            message.guild.id, message.channel.id, message.id,
            message.author.id, "delete", clean_content(message.content)
        )
        
        # Create embed for logging channel
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=0xff0000,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Author",
            value=f"{message.author} ({message.author.id})",
            inline=True
        )
        embed.add_field(
            name="Channel",
            value=message.channel.mention,
            inline=True
        )
        
        if message.content:
            embed.add_field(
                name="Content",
                value=truncate_text(clean_content(message.content), 1024),
                inline=False
            )
        
        if message.attachments:
            attachments = ", ".join([att.filename for att in message.attachments])
            embed.add_field(
                name="Attachments",
                value=truncate_text(attachments, 1024),
                inline=False
            )
        
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url
        )
        
        await self.send_log(message.guild, embed)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Log edited messages"""
        if not self.bot.config['logging']['events']['message_edit']:
            return
        
        if before.guild is None or before.author.bot:
            return
        
        # Skip if content didn't change
        if before.content == after.content:
            return
        
        # Log to database
        await self.bot.db.log_message_action(
            before.guild.id, before.channel.id, before.id,
            before.author.id, "edit", clean_content(before.content),
            {"new_content": clean_content(after.content)}
        )
        
        # Create embed for logging channel
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=0xffff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Author",
            value=f"{before.author} ({before.author.id})",
            inline=True
        )
        embed.add_field(
            name="Channel",
            value=before.channel.mention,
            inline=True
        )
        embed.add_field(
            name="Jump to Message",
            value=f"[Click here]({after.jump_url})",
            inline=True
        )
        
        if before.content:
            embed.add_field(
                name="Before",
                value=truncate_text(clean_content(before.content), 512),
                inline=False
            )
        
        if after.content:
            embed.add_field(
                name="After",
                value=truncate_text(clean_content(after.content), 512),
                inline=False
            )
        
        embed.set_author(
            name=before.author.display_name,
            icon_url=before.author.display_avatar.url
        )
        
        await self.send_log(before.guild, embed)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Log member joins"""
        if not self.bot.config['logging']['events']['member_join']:
            return
        
        embed = discord.Embed(
            title="📥 Member Joined",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="User",
            value=f"{member} ({member.id})",
            inline=True
        )
        embed.add_field(
            name="Account Created",
            value=f"<t:{int(member.created_at.timestamp())}:F>",
            inline=True
        )
        embed.add_field(
            name="Member Count",
            value=str(member.guild.member_count),
            inline=True
        )
        
        # Account age
        account_age = datetime.utcnow() - member.created_at
        if account_age.days < 7:
            embed.add_field(
                name="⚠️ Warning",
                value=f"Account is only {account_age.days} days old",
                inline=False
            )
        
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar.url
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await self.send_log(member.guild, embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log member leaves"""
        if not self.bot.config['logging']['events']['member_leave']:
            return
        
        embed = discord.Embed(
            title="📤 Member Left",
            color=0xff6600,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="User",
            value=f"{member} ({member.id})",
            inline=True
        )
        embed.add_field(
            name="Joined",
            value=f"<t:{int(member.joined_at.timestamp())}:F>" if member.joined_at else "Unknown",
            inline=True
        )
        embed.add_field(
            name="Member Count",
            value=str(member.guild.member_count),
            inline=True
        )
        
        # Show roles if any
        if member.roles[1:]:  # Exclude @everyone
            roles = ", ".join([role.name for role in member.roles[1:]])
            embed.add_field(
                name="Roles",
                value=truncate_text(roles, 1024),
                inline=False
            )
        
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar.url
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await self.send_log(member.guild, embed)
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Log member bans"""
        if not self.bot.config['logging']['events']['member_ban']:
            return
        
        # Try to get ban reason from audit log
        ban_reason = "Unknown"
        moderator = "Unknown"
        
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=5):
                if entry.target == user:
                    ban_reason = entry.reason or "No reason provided"
                    moderator = entry.user
                    break
        except discord.Forbidden:
            pass
        
        embed = discord.Embed(
            title="🔨 Member Banned",
            color=0xff0000,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="User",
            value=f"{user} ({user.id})",
            inline=True
        )
        embed.add_field(
            name="Moderator",
            value=str(moderator),
            inline=True
        )
        embed.add_field(
            name="Reason",
            value=ban_reason,
            inline=False
        )
        
        embed.set_author(
            name=user.display_name,
            icon_url=user.display_avatar.url
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await self.send_log(guild, embed)
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Log member unbans"""
        if not self.bot.config['logging']['events']['member_unban']:
            return
        
        # Try to get unban reason from audit log
        unban_reason = "Unknown"
        moderator = "Unknown"
        
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.unban, limit=5):
                if entry.target == user:
                    unban_reason = entry.reason or "No reason provided"
                    moderator = entry.user
                    break
        except discord.Forbidden:
            pass
        
        embed = discord.Embed(
            title="✅ Member Unbanned",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="User",
            value=f"{user} ({user.id})",
            inline=True
        )
        embed.add_field(
            name="Moderator",
            value=str(moderator),
            inline=True
        )
        embed.add_field(
            name="Reason",
            value=unban_reason,
            inline=False
        )
        
        embed.set_author(
            name=user.display_name,
            icon_url=user.display_avatar.url
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await self.send_log(guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Log role creation"""
        if not self.bot.config['logging']['events']['role_create']:
            return
        
        embed = discord.Embed(
            title="➕ Role Created",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Role", value=f"{role.mention} ({role.id})", inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Mentionable", value=str(role.mentionable), inline=True)
        embed.add_field(name="Hoisted", value=str(role.hoist), inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        
        await self.send_log(role.guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Log role deletion"""
        if not self.bot.config['logging']['events']['role_delete']:
            return
        
        embed = discord.Embed(
            title="➖ Role Deleted",
            color=0xff0000,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Role", value=f"{role.name} ({role.id})", inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Members", value=str(len(role.members)), inline=True)
        
        await self.send_log(role.guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log channel creation"""
        if not self.bot.config['logging']['events']['channel_create']:
            return
        
        embed = discord.Embed(
            title="📝 Channel Created",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Channel", value=f"{channel.mention} ({channel.id})", inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)
        
        await self.send_log(channel.guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log channel deletion"""
        if not self.bot.config['logging']['events']['channel_delete']:
            return
        
        embed = discord.Embed(
            title="🗑️ Channel Deleted",
            color=0xff0000,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Channel", value=f"{channel.name} ({channel.id})", inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)
        
        await self.send_log(channel.guild, embed)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Log voice state changes"""
        if not self.bot.config['logging']['events']['voice_state_update']:
            return
        
        if before.channel == after.channel:
            return  # No channel change
        
        embed = discord.Embed(
            title="🎵 Voice State Update",
            color=0x0099ff,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="User",
            value=f"{member} ({member.id})",
            inline=True
        )
        
        if before.channel and after.channel:
            embed.add_field(
                name="Action",
                value=f"Moved from {before.channel.name} to {after.channel.name}",
                inline=False
            )
        elif before.channel:
            embed.add_field(
                name="Action",
                value=f"Left {before.channel.name}",
                inline=False
            )
        elif after.channel:
            embed.add_field(
                name="Action",
                value=f"Joined {after.channel.name}",
                inline=False
            )
        
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar.url
        )
        
        await self.send_log(member.guild, embed)

async def setup(bot):
    await bot.add_cog(LoggingCog(bot))
