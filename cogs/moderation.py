import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal
from datetime import datetime, timedelta
import logging
from utils.helpers import parse_duration, format_duration, create_embed, create_error_embed, create_success_embed
from utils.permissions import has_permissions, can_use_command, check_hierarchy

logger = logging.getLogger(__name__)

class ModerationCog(commands.Cog, name="Moderation"):
    def __init__(self, bot):
        self.bot = bot
    
    async def send_dm(self, user: discord.User, embed: discord.Embed) -> bool:
        """Send DM to user, return success status"""
        try:
            await user.send(embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False
    
    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="The user to ban",
        reason="Reason for the ban",
        duration="Duration for temporary ban (e.g., 1d, 1h, 30m)",
        delete_messages="Days of messages to delete (0-7)"
    )
    @can_use_command("ban")
    @check_hierarchy()
    async def ban(
        self, 
        interaction: discord.Interaction,
        user: discord.User,
        reason: Optional[str] = "No reason provided",
        duration: Optional[str] = None,
        delete_messages: Optional[app_commands.Range[int, 0, 7]] = 1
    ):
        """Ban a user from the server"""
        await interaction.response.defer()
        
        guild = interaction.guild
        moderator = interaction.user
        
        # Check if user is already banned
        try:
            ban_entry = await guild.fetch_ban(user)
            embed = create_error_embed(
                self.bot.messages['commands']['ban']['already_banned']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        except discord.NotFound:
            pass  # User is not banned, continue
        
        # Check for self-ban
        if user == moderator:
            embed = create_error_embed(
                self.bot.messages['commands']['ban']['cannot_ban_self']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Check if trying to ban a bot
        if user.bot and user != self.bot.user:
            embed = create_error_embed(
                self.bot.messages['commands']['ban']['cannot_ban_bot']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Parse duration if provided
        temp_ban = False
        ban_duration = None
        expires_at = None
        
        if duration:
            ban_duration = parse_duration(duration)
            if ban_duration:
                temp_ban = True
                expires_at = datetime.now() + ban_duration
            else:
                embed = create_error_embed(
                    self.bot.messages['commands']['invalid_duration']
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        # Send DM notification
        dm_sent = False
        if self.bot.config['moderation']['dm_on_punishment']:
            dm_embed = discord.Embed(
                title="🔨 You have been banned",
                description=self.bot.messages['commands']['ban']['dm'].format(
                    guild=guild.name,
                    reason=reason
                ),
                color=0xff0000
            )
            if temp_ban:
                dm_embed.add_field(
                    name="Duration",
                    value=format_duration(ban_duration),
                    inline=True
                )
            dm_sent = await self.send_dm(user, dm_embed)
        
        try:
            # Execute the ban
            await guild.ban(user, reason=reason, delete_message_days=delete_messages)
            
            # Log the action
            await self.bot.db.log_mod_action(
                guild.id, user.id, moderator.id, 
                "tempban" if temp_ban else "ban", reason,
                int(ban_duration.total_seconds()) if ban_duration else None
            )
            
            # Add temporary action if applicable
            if temp_ban:
                await self.bot.db.add_temp_action(guild.id, user.id, "tempban", expires_at)
            
            # Log staff action
            await self.bot.db.log_staff_action(
                guild.id, moderator.id, "ban", user.id, 
                interaction.channel.id, f"reason={reason}, duration={duration}"
            )
            
            # Send success message
            if temp_ban:
                message = self.bot.messages['commands']['ban']['success_temp'].format(
                    user=user.display_name,
                    duration=format_duration(ban_duration)
                )
            else:
                message = self.bot.messages['commands']['ban']['success'].format(
                    user=user.display_name
                )
            
            embed = create_success_embed(message)
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            if temp_ban:
                embed.add_field(name="Duration", value=format_duration(ban_duration), inline=True)
                embed.add_field(name="Expires", value=f"<t:{int(expires_at.timestamp())}:F>", inline=True)
            
            if not dm_sent:
                embed.set_footer(text="⚠️ Could not send DM to user")
            
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed(
                self.bot.messages['errors']['missing_permissions']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error banning user {user}: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(
        user="The user to unban (ID or username#discriminator)",
        reason="Reason for the unban"
    )
    @can_use_command("ban")
    async def unban(
        self,
        interaction: discord.Interaction,
        user: str,
        reason: Optional[str] = "No reason provided"
    ):
        """Unban a user from the server"""
        await interaction.response.defer()
        
        guild = interaction.guild
        moderator = interaction.user
        
        # Try to find the banned user
        banned_user = None
        
        # First try to get user by ID
        if user.isdigit():
            try:
                banned_user = await self.bot.fetch_user(int(user))
            except discord.NotFound:
                pass
        
        # If not found by ID, search through banned users
        if not banned_user:
            async for ban_entry in guild.bans():
                if (ban_entry.user.name == user or 
                    str(ban_entry.user) == user or
                    str(ban_entry.user.id) == user):
                    banned_user = ban_entry.user
                    break
        
        if not banned_user:
            embed = create_error_embed(
                self.bot.messages['commands']['user_not_found']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Check if user is actually banned
        try:
            await guild.fetch_ban(banned_user)
        except discord.NotFound:
            embed = create_error_embed(
                self.bot.messages['commands']['unban']['not_banned']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            # Execute the unban
            await guild.unban(banned_user, reason=reason)
            
            # Log the action
            await self.bot.db.log_mod_action(
                guild.id, banned_user.id, moderator.id, "unban", reason
            )
            
            # Log staff action
            await self.bot.db.log_staff_action(
                guild.id, moderator.id, "unban", banned_user.id, 
                interaction.channel.id, f"reason={reason}"
            )
            
            # Send success message
            message = self.bot.messages['commands']['unban']['success'].format(
                user=banned_user.display_name
            )
            
            embed = create_success_embed(message)
            embed.add_field(name="User", value=f"{banned_user} ({banned_user.id})", inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed(
                self.bot.messages['errors']['missing_permissions']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error unbanning user {banned_user}: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(
        user="The user to kick",
        reason="Reason for the kick"
    )
    @can_use_command("kick")
    @check_hierarchy()
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "No reason provided"
    ):
        """Kick a user from the server"""
        await interaction.response.defer()
        
        guild = interaction.guild
        moderator = interaction.user
        
        # Check for self-kick
        if user == moderator:
            embed = create_error_embed(
                self.bot.messages['commands']['kick']['cannot_kick_self']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Send DM notification
        dm_sent = False
        if self.bot.config['moderation']['dm_on_punishment']:
            dm_embed = discord.Embed(
                title="👢 You have been kicked",
                description=self.bot.messages['commands']['kick']['dm'].format(
                    guild=guild.name,
                    reason=reason
                ),
                color=0xff6600
            )
            dm_sent = await self.send_dm(user, dm_embed)
        
        try:
            # Execute the kick
            await guild.kick(user, reason=reason)
            
            # Log the action
            await self.bot.db.log_mod_action(
                guild.id, user.id, moderator.id, "kick", reason
            )
            
            # Log staff action
            await self.bot.db.log_staff_action(
                guild.id, moderator.id, "kick", user.id, 
                interaction.channel.id, f"reason={reason}"
            )
            
            # Send success message
            message = self.bot.messages['commands']['kick']['success'].format(
                user=user.display_name
            )
            
            embed = create_success_embed(message)
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            if not dm_sent:
                embed.set_footer(text="⚠️ Could not send DM to user")
            
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed(
                self.bot.messages['errors']['missing_permissions']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error kicking user {user}: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.describe(
        user="The user to timeout",
        duration="Duration of timeout (e.g., 1h, 30m, 1d)",
        reason="Reason for the timeout"
    )
    @can_use_command("timeout")
    @check_hierarchy()
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: Optional[str] = "10m",
        reason: Optional[str] = "No reason provided"
    ):
        """Timeout a user"""
        await interaction.response.defer()
        
        guild = interaction.guild
        moderator = interaction.user
        
        # Parse duration
        timeout_duration = parse_duration(duration)
        if not timeout_duration:
            embed = create_error_embed(
                self.bot.messages['commands']['invalid_duration']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Check maximum duration (28 days)
        max_duration = timedelta(days=28)
        if timeout_duration > max_duration:
            embed = create_error_embed(
                self.bot.messages['commands']['timeout']['max_duration']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Check if user is already timed out
        if user.timed_out_until:
            embed = create_error_embed(
                self.bot.messages['commands']['timeout']['already_timed_out']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Send DM notification
        dm_sent = False
        if self.bot.config['moderation']['dm_on_punishment']:
            dm_embed = discord.Embed(
                title="🔇 You have been timed out",
                description=self.bot.messages['commands']['timeout']['dm'].format(
                    guild=guild.name,
                    duration=format_duration(timeout_duration),
                    reason=reason
                ),
                color=0xffff00
            )
            dm_sent = await self.send_dm(user, dm_embed)
        
        try:
            # Execute the timeout
            until = datetime.now() + timeout_duration
            await user.timeout(until, reason=reason)
            
            # Log the action
            await self.bot.db.log_mod_action(
                guild.id, user.id, moderator.id, "timeout", reason,
                int(timeout_duration.total_seconds())
            )
            
            # Add temporary action
            await self.bot.db.add_temp_action(guild.id, user.id, "timeout", until)
            
            # Log staff action
            await self.bot.db.log_staff_action(
                guild.id, moderator.id, "timeout", user.id, 
                interaction.channel.id, f"reason={reason}, duration={duration}"
            )
            
            # Send success message
            message = self.bot.messages['commands']['timeout']['success'].format(
                user=user.display_name,
                duration=format_duration(timeout_duration)
            )
            
            embed = create_success_embed(message)
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="Duration", value=format_duration(timeout_duration), inline=True)
            embed.add_field(name="Expires", value=f"<t:{int(until.timestamp())}:F>", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            if not dm_sent:
                embed.set_footer(text="⚠️ Could not send DM to user")
            
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed(
                self.bot.messages['errors']['missing_permissions']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error timing out user {user}: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="untimeout", description="Remove timeout from a user")
    @app_commands.describe(
        user="The user to remove timeout from",
        reason="Reason for removing timeout"
    )
    @can_use_command("timeout")
    async def untimeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "No reason provided"
    ):
        """Remove timeout from a user"""
        await interaction.response.defer()
        
        guild = interaction.guild
        moderator = interaction.user
        
        # Check if user is timed out
        if not user.timed_out_until:
            embed = create_error_embed(
                self.bot.messages['commands']['timeout']['not_timed_out']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            # Remove the timeout
            await user.timeout(None, reason=reason)
            
            # Log the action
            await self.bot.db.log_mod_action(
                guild.id, user.id, moderator.id, "untimeout", reason
            )
            
            # Log staff action
            await self.bot.db.log_staff_action(
                guild.id, moderator.id, "untimeout", user.id, 
                interaction.channel.id, f"reason={reason}"
            )
            
            # Send success message
            message = self.bot.messages['commands']['timeout']['success_remove'].format(
                user=user.display_name
            )
            
            embed = create_success_embed(message)
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed(
                self.bot.messages['errors']['missing_permissions']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error removing timeout from user {user}: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(
        user="The user to warn",
        reason="Reason for the warning"
    )
    @can_use_command("warn")
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str
    ):
        """Warn a user"""
        await interaction.response.defer()
        
        guild = interaction.guild
        moderator = interaction.user
        
        try:
            # Add warning to database
            await self.bot.db.add_warning(guild.id, user.id, moderator.id, reason)
            
            # Get current warning count
            warning_count = await self.bot.db.get_warning_count(guild.id, user.id)
            max_warnings = self.bot.config['bot']['max_warnings']
            
            # Log the action
            await self.bot.db.log_mod_action(
                guild.id, user.id, moderator.id, "warn", reason
            )
            
            # Log staff action
            await self.bot.db.log_staff_action(
                guild.id, moderator.id, "warn", user.id, 
                interaction.channel.id, f"reason={reason}"
            )
            
            # Send DM notification
            dm_sent = False
            if self.bot.config['moderation']['dm_on_punishment']:
                dm_embed = discord.Embed(
                    title="⚠️ You have been warned",
                    description=self.bot.messages['commands']['warn']['dm'].format(
                        guild=guild.name,
                        reason=reason,
                        warnings=warning_count,
                        max_warnings=max_warnings
                    ),
                    color=0xffff00
                )
                dm_sent = await self.send_dm(user, dm_embed)
            
            # Check if max warnings reached
            auto_punish = False
            if (warning_count >= max_warnings and 
                self.bot.config['bot']['auto_punish_on_max_warnings']):
                
                auto_punish = True
                # Auto-timeout for 1 hour
                until = datetime.now() + timedelta(hours=1)
                await user.timeout(until, reason="Maximum warnings reached")
                
                # Log auto-punishment
                await self.bot.db.log_mod_action(
                    guild.id, user.id, self.bot.user.id, "auto_timeout", 
                    "Maximum warnings reached", 3600
                )
            
            # Send success message
            if auto_punish:
                message = self.bot.messages['commands']['warn']['max_warnings'].format(
                    user=user.display_name
                )
            else:
                message = self.bot.messages['commands']['warn']['success'].format(
                    user=user.display_name,
                    warnings=warning_count,
                    max_warnings=max_warnings
                )
            
            embed = create_success_embed(message)
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="Warnings", value=f"{warning_count}/{max_warnings}", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            if auto_punish:
                embed.add_field(name="Auto-Punishment", value="1 hour timeout", inline=True)
            
            if not dm_sent:
                embed.set_footer(text="⚠️ Could not send DM to user")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error warning user {user}: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unwarn", description="Remove a warning from a user")
    @app_commands.describe(
        user="The user to remove warning from",
        reason="Reason for removing warning"
    )
    @can_use_command("warn")
    async def unwarn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "No reason provided"
    ):
        """Remove a warning from a user"""
        await interaction.response.defer()
        
        guild = interaction.guild
        moderator = interaction.user
        
        # Remove warning
        removed = await self.bot.db.remove_warning(guild.id, user.id)
        
        if not removed:
            embed = create_error_embed(
                self.bot.messages['commands']['unwarn']['no_warnings']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            # Log the action
            await self.bot.db.log_mod_action(
                guild.id, user.id, moderator.id, "unwarn", reason
            )
            
            # Log staff action
            await self.bot.db.log_staff_action(
                guild.id, moderator.id, "unwarn", user.id, 
                interaction.channel.id, f"reason={reason}"
            )
            
            # Get updated warning count
            warning_count = await self.bot.db.get_warning_count(guild.id, user.id)
            max_warnings = self.bot.config['bot']['max_warnings']
            
            # Send success message
            message = self.bot.messages['commands']['unwarn']['success'].format(
                user=user.display_name
            )
            
            embed = create_success_embed(message)
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="Warnings", value=f"{warning_count}/{max_warnings}", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error removing warning from user {user}: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="purge", description="Delete multiple messages")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user",
        reason="Reason for purging messages"
    )
    @can_use_command("purge")
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
        user: Optional[discord.Member] = None,
        reason: Optional[str] = "No reason provided"
    ):
        """Delete multiple messages"""
        await interaction.response.defer(ephemeral=True)
        
        channel = interaction.channel
        moderator = interaction.user
        
        try:
            # Define check function for filtering messages
            def check(message):
                if user:
                    return message.author == user
                return True
            
            # Delete messages
            deleted = await channel.purge(limit=amount, check=check)
            deleted_count = len(deleted)
            
            # Log the action
            await self.bot.db.log_mod_action(
                interaction.guild.id, user.id if user else 0, moderator.id, 
                "purge", reason, deleted_count, 
                {"channel_id": channel.id, "deleted_count": deleted_count}
            )
            
            # Log staff action
            await self.bot.db.log_staff_action(
                interaction.guild.id, moderator.id, "purge", 
                user.id if user else None, channel.id, 
                f"amount={amount}, reason={reason}"
            )
            
            # Send success message
            if deleted_count == 0:
                message = self.bot.messages['commands']['purge']['no_messages']
            else:
                message = self.bot.messages['commands']['purge']['success'].format(
                    count=deleted_count
                )
            
            embed = create_success_embed(message)
            embed.add_field(name="Channel", value=channel.mention, inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            if user:
                embed.add_field(name="Target User", value=user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except discord.Forbidden:
            embed = create_error_embed(
                self.bot.messages['errors']['missing_permissions']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error purging messages: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
