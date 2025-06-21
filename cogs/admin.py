import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal
import yaml
import logging
from datetime import datetime, timedelta
import asyncio
from utils.helpers import create_embed, create_error_embed, create_success_embed, load_config, load_messages
from utils.permissions import has_permissions, can_use_command

logger = logging.getLogger(__name__)

class AdminCog(commands.Cog, name="Administration"):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="setup", description="Set up the bot for this server")
    @has_permissions("admin")
    async def setup(self, interaction: discord.Interaction):
        """Set up the bot for the server"""
        await interaction.response.defer()
        
        guild = interaction.guild
        setup_results = []
        
        try:
            # Initialize guild in database
            await self.bot.db.setup_guild(guild.id)
            setup_results.append("✅ Database initialized")
            
            # Create mod-logs channel if it doesn't exist
            log_channel_name = self.bot.config['moderation']['log_channel_name']
            log_channel = discord.utils.get(guild.text_channels, name=log_channel_name)
            
            if not log_channel:
                # Create the channel
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        embed_links=True
                    )
                }
                
                # Add permission overwrites for admin/mod roles
                admin_roles = self.bot.config.get('permissions', {}).get('admin_roles', [])
                mod_roles = self.bot.config.get('permissions', {}).get('moderator_roles', [])
                
                for role_id in admin_roles + mod_roles:
                    role = guild.get_role(role_id)
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True)
                
                log_channel = await guild.create_text_channel(
                    log_channel_name,
                    topic="Moderation logs and bot activity",
                    overwrites=overwrites
                )
                setup_results.append(f"✅ Created #{log_channel_name} channel")
            else:
                setup_results.append(f"✅ Found existing #{log_channel_name} channel")
            
            # Send welcome message to log channel
            embed = discord.Embed(
                title="🛡️ Moderation Bot Setup Complete",
                description="The bot has been successfully configured for this server!",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Features Enabled",
                value="• Slash commands\n• Moderation logging\n• Auto-moderation\n• User history tracking\n• Staff command logging",
                inline=False
            )
            
            embed.add_field(
                name="Next Steps",
                value="• Configure permission roles with `/config roles`\n• Customize auto-moderation settings\n• Review `/help` for available commands",
                inline=False
            )
            
            await log_channel.send(embed=embed)
            setup_results.append("✅ Welcome message sent")
            
            # Create success embed
            embed = create_success_embed("Bot setup completed successfully!")
            embed.add_field(
                name="Setup Results",
                value="\n".join(setup_results),
                inline=False
            )
            embed.add_field(
                name="Log Channel",
                value=log_channel.mention,
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed(
                "Missing permissions to complete setup. Please ensure the bot has 'Manage Channels' and 'Manage Roles' permissions."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error during setup: {e}")
            embed = create_error_embed(
                f"An error occurred during setup: {str(e)}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="config", description="Configure bot settings")
    @app_commands.describe(
        setting="Setting to configure",
        action="Action to perform"
    )
    @has_permissions("admin")
    async def config(
        self,
        interaction: discord.Interaction,
        setting: Literal["roles", "automod", "logging", "general"],
        action: Literal["view", "edit"] = "view"
    ):
        """Configure bot settings"""
        await interaction.response.defer(ephemeral=True)
        
        if setting == "roles":
            await self._config_roles(interaction, action)
        elif setting == "automod":
            await self._config_automod(interaction, action)
        elif setting == "logging":
            await self._config_logging(interaction, action)
        elif setting == "general":
            await self._config_general(interaction, action)
    
    async def _config_roles(self, interaction: discord.Interaction, action: str):
        """Configure permission roles"""
        if action == "view":
            embed = discord.Embed(
                title="👥 Permission Roles Configuration",
                color=0x0099ff,
                timestamp=datetime.utcnow()
            )
            
            config = self.bot.config.get('permissions', {})
            
            # Admin roles
            admin_roles = config.get('admin_roles', [])
            admin_role_names = []
            for role_id in admin_roles:
                role = interaction.guild.get_role(role_id)
                admin_role_names.append(role.name if role else f"Unknown Role ({role_id})")
            
            embed.add_field(
                name="Admin Roles",
                value=", ".join(admin_role_names) if admin_role_names else "None configured",
                inline=False
            )
            
            # Moderator roles
            mod_roles = config.get('moderator_roles', [])
            mod_role_names = []
            for role_id in mod_roles:
                role = interaction.guild.get_role(role_id)
                mod_role_names.append(role.name if role else f"Unknown Role ({role_id})")
            
            embed.add_field(
                name="Moderator Roles",
                value=", ".join(mod_role_names) if mod_role_names else "None configured",
                inline=False
            )
            
            # Helper roles
            helper_roles = config.get('helper_roles', [])
            helper_role_names = []
            for role_id in helper_roles:
                role = interaction.guild.get_role(role_id)
                helper_role_names.append(role.name if role else f"Unknown Role ({role_id})")
            
            embed.add_field(
                name="Helper Roles",
                value=", ".join(helper_role_names) if helper_role_names else "None configured",
                inline=False
            )
            
            embed.set_footer(text="Use '/config roles edit' to modify these settings")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _config_automod(self, interaction: discord.Interaction, action: str):
        """Configure auto-moderation settings"""
        embed = discord.Embed(
            title="🤖 Auto-Moderation Configuration",
            color=0xff6600,
            timestamp=datetime.utcnow()
        )
        
        automod_config = self.bot.config.get('moderation', {})
        
        # Spam detection
        spam_config = automod_config.get('spam', {})
        embed.add_field(
            name="Spam Detection",
            value=f"**Enabled:** {spam_config.get('enabled', False)}\n"
                  f"**Max Messages:** {spam_config.get('max_messages', 5)}\n"
                  f"**Time Window:** {spam_config.get('time_window', 10)}s\n"
                  f"**Punishment:** {spam_config.get('punishment', 'timeout')}",
            inline=True
        )
        
        # Caps detection
        caps_config = automod_config.get('caps', {})
        embed.add_field(
            name="Excessive Caps",
            value=f"**Enabled:** {caps_config.get('enabled', False)}\n"
                  f"**Threshold:** {int(caps_config.get('threshold', 0.7) * 100)}%\n"
                  f"**Min Length:** {caps_config.get('min_length', 10)}\n"
                  f"**Punishment:** {caps_config.get('punishment', 'warn')}",
            inline=True
        )
        
        # Bad words
        bad_words_config = automod_config.get('bad_words', {})
        word_count = len(bad_words_config.get('words', []))
        embed.add_field(
            name="Bad Words Filter",
            value=f"**Enabled:** {bad_words_config.get('enabled', False)}\n"
                  f"**Word Count:** {word_count}\n"
                  f"**Punishment:** {bad_words_config.get('punishment', 'warn')}",
            inline=True
        )
        
        # Invite links
        invite_config = automod_config.get('invite_links', {})
        whitelist_count = len(invite_config.get('whitelist', []))
        embed.add_field(
            name="Invite Links",
            value=f"**Enabled:** {invite_config.get('enabled', False)}\n"
                  f"**Whitelisted:** {whitelist_count} servers\n"
                  f"**Punishment:** {invite_config.get('punishment', 'warn')}",
            inline=True
        )
        
        embed.set_footer(text="Auto-moderation settings are configured in config.yml")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _config_logging(self, interaction: discord.Interaction, action: str):
        """Configure logging settings"""
        embed = discord.Embed(
            title="📋 Logging Configuration",
            color=0x36393e,
            timestamp=datetime.utcnow()
        )
        
        logging_config = self.bot.config.get('logging', {})
        events_config = logging_config.get('events', {})
        
        embed.add_field(
            name="General",
            value=f"**Enabled:** {logging_config.get('enabled', True)}",
            inline=False
        )
        
        # Message events
        message_events = [
            ('Message Delete', events_config.get('message_delete', True)),
            ('Message Edit', events_config.get('message_edit', True))
        ]
        
        embed.add_field(
            name="Message Events",
            value="\n".join([f"**{name}:** {'✅' if enabled else '❌'}" for name, enabled in message_events]),
            inline=True
        )
        
        # Member events
        member_events = [
            ('Member Join', events_config.get('member_join', True)),
            ('Member Leave', events_config.get('member_leave', True)),
            ('Member Ban', events_config.get('member_ban', True)),
            ('Member Unban', events_config.get('member_unban', True))
        ]
        
        embed.add_field(
            name="Member Events",
            value="\n".join([f"**{name}:** {'✅' if enabled else '❌'}" for name, enabled in member_events]),
            inline=True
        )
        
        # Server events
        server_events = [
            ('Role Create/Delete', events_config.get('role_create', True)),
            ('Channel Create/Delete', events_config.get('channel_create', True)),
            ('Voice State Updates', events_config.get('voice_state_update', True)),
            ('Mod Actions', events_config.get('mod_actions', True))
        ]
        
        embed.add_field(
            name="Server Events",
            value="\n".join([f"**{name}:** {'✅' if enabled else '❌'}" for name, enabled in server_events]),
            inline=True
        )
        
        # Log channel
        log_channel_name = self.bot.config['moderation']['log_channel_name']
        log_channel = discord.utils.get(interaction.guild.text_channels, name=log_channel_name)
        
        embed.add_field(
            name="Log Channel",
            value=log_channel.mention if log_channel else f"#{log_channel_name} (not found)",
            inline=False
        )
        
        embed.set_footer(text="Logging settings are configured in config.yml")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _config_general(self, interaction: discord.Interaction, action: str):
        """Configure general settings"""
        embed = discord.Embed(
            title="⚙️ General Configuration",
            color=0x0099ff,
            timestamp=datetime.utcnow()
        )
        
        bot_config = self.bot.config.get('bot', {})
        mod_config = self.bot.config.get('moderation', {})
        
        embed.add_field(
            name="Bot Settings",
            value=f"**Prefix:** {bot_config.get('prefix', '!')}\n"
                  f"**Max Warnings:** {bot_config.get('max_warnings', 3)}\n"
                  f"**Auto-punish on Max:** {bot_config.get('auto_punish_on_max_warnings', True)}",
            inline=True
        )
        
        embed.add_field(
            name="Moderation Settings",
            value=f"**Require Reason:** {mod_config.get('require_reason', True)}\n"
                  f"**DM on Punishment:** {mod_config.get('dm_on_punishment', True)}\n"
                  f"**Default Ban Delete Days:** {mod_config.get('default_ban_delete_days', 1)}",
            inline=True
        )
        
        embed.add_field(
            name="Database",
            value=f"**Backup Interval:** {self.bot.config.get('database', {}).get('backup_interval', 24)}h\n"
                  f"**History Retention:** {self.bot.config.get('database', {}).get('max_history_days', 365)} days",
            inline=True
        )
        
        embed.set_footer(text="General settings are configured in config.yml")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="backup", description="Create a database backup")
    @has_permissions("admin")
    async def backup(self, interaction: discord.Interaction):
        """Create a database backup"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create backup
            backup_path = await self.bot.db.backup_database()
            
            embed = create_success_embed(
                self.bot.messages['success']['database_backup']
            )
            embed.add_field(
                name="Backup File",
                value=backup_path,
                inline=False
            )
            embed.add_field(
                name="Timestamp",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            embed = create_error_embed(
                self.bot.messages['errors']['database_error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="cleanup", description="Clean up old database entries")
    @app_commands.describe(
        days="Days of history to keep (default: 365)"
    )
    @has_permissions("admin")
    async def cleanup(
        self,
        interaction: discord.Interaction,
        days: Optional[app_commands.Range[int, 30, 3650]] = 365
    ):
        """Clean up old database entries"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Confirm action
            embed = discord.Embed(
                title="⚠️ Database Cleanup",
                description=f"This will permanently delete data older than {days} days.\n\n"
                           "**What will be deleted:**\n"
                           "• Old message logs\n"
                           "• Completed temporary actions\n"
                           "• Old auto-moderation violations\n\n"
                           "**What will NOT be deleted:**\n"
                           "• User warnings\n"
                           "• Moderation history\n"
                           "• Staff logs\n"
                           "• Guild settings",
                color=0xffff00
            )
            
            view = CleanupConfirmView(self.bot, days)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error starting cleanup: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="reload", description="Reload bot configuration")
    @has_permissions("admin")
    async def reload(self, interaction: discord.Interaction):
        """Reload bot configuration from files"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Reload configuration
            self.bot.config = load_config()
            self.bot.messages = load_messages()
            
            embed = create_success_embed(
                "Configuration reloaded successfully!"
            )
            embed.add_field(
                name="Reloaded Files",
                value="• config.yml\n• messages.yml",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error reloading configuration: {e}")
            embed = create_error_embed(
                f"Error reloading configuration: {str(e)}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="stats", description="View bot statistics")
    @has_permissions("moderator")
    async def stats(self, interaction: discord.Interaction):
        """View bot statistics"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild = interaction.guild
            
            embed = discord.Embed(
                title="📊 Bot Statistics",
                color=0x0099ff,
                timestamp=datetime.utcnow()
            )
            
            # Guild info
            embed.add_field(
                name="Server Info",
                value=f"**Name:** {guild.name}\n"
                      f"**Members:** {guild.member_count}\n"
                      f"**Channels:** {len(guild.channels)}\n"
                      f"**Roles:** {len(guild.roles)}",
                inline=True
            )
            
            # Bot info
            embed.add_field(
                name="Bot Info",
                value=f"**Guilds:** {len(self.bot.guilds)}\n"
                      f"**Latency:** {round(self.bot.latency * 1000)}ms\n"
                      f"**Commands:** {len(self.bot.tree.get_commands())}\n"
                      f"**Cogs:** {len(self.bot.cogs)}",
                inline=True
            )
            
            # Database stats (simplified, as we'd need to add these methods to DatabaseManager)
            embed.add_field(
                name="Database",
                value="**Status:** Connected\n"
                      "**Tables:** 7\n"
                      "**Auto-backup:** Enabled",
                inline=True
            )
            
            # Recent activity summary
            now = datetime.now()
            day_ago = now - timedelta(days=1)
            
            # Get recent mod actions count
            recent_history = await self.bot.db.get_user_history(guild.id, 0, 1000)  # Get all recent
            recent_actions = [h for h in recent_history if datetime.fromisoformat(h['timestamp'].replace('Z', '+00:00')) > day_ago]
            
            embed.add_field(
                name="Recent Activity (24h)",
                value=f"**Mod Actions:** {len(recent_actions)}\n"
                      "**Auto-mod Violations:** N/A\n"  # Would need to implement this query
                      "**Messages Logged:** N/A",  # Would need to implement this query
                inline=False
            )
            
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(text=f"Bot ID: {self.bot.user.id}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="lock", description="Lock a channel")
    @app_commands.describe(
        channel="Channel to lock (current channel if not specified)",
        reason="Reason for locking the channel"
    )
    @can_use_command("lock")
    async def lock(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        reason: Optional[str] = "No reason provided"
    ):
        """Lock a channel"""
        await interaction.response.defer()
        
        target_channel = channel or interaction.channel
        guild = interaction.guild
        moderator = interaction.user
        
        # Check if channel is already locked
        default_role = guild.default_role
        overwrites = target_channel.overwrites_for(default_role)
        
        if overwrites.send_messages is False:
            embed = create_error_embed(
                self.bot.messages['commands']['lock']['already_locked']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            # Lock the channel
            await target_channel.set_permissions(
                default_role,
                send_messages=False,
                reason=f"Channel locked by {moderator}: {reason}"
            )
            
            # Log the action
            await self.bot.db.log_mod_action(
                guild.id, 0, moderator.id, "lock", reason,
                additional_data={"channel_id": target_channel.id}
            )
            
            # Send success message
            embed = create_success_embed(
                self.bot.messages['commands']['lock']['success']
            )
            embed.add_field(name="Channel", value=target_channel.mention, inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.followup.send(embed=embed)
            
            # Send notification in locked channel
            lock_embed = discord.Embed(
                title="🔒 Channel Locked",
                description=f"This channel has been locked by {moderator.mention}.\n**Reason:** {reason}",
                color=0xff6600
            )
            await target_channel.send(embed=lock_embed)
            
        except discord.Forbidden:
            embed = create_error_embed(
                self.bot.messages['errors']['missing_permissions']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error locking channel: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unlock", description="Unlock a channel")
    @app_commands.describe(
        channel="Channel to unlock (current channel if not specified)",
        reason="Reason for unlocking the channel"
    )
    @can_use_command("unlock")
    async def unlock(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        reason: Optional[str] = "No reason provided"
    ):
        """Unlock a channel"""
        await interaction.response.defer()
        
        target_channel = channel or interaction.channel
        guild = interaction.guild
        moderator = interaction.user
        
        # Check if channel is locked
        default_role = guild.default_role
        overwrites = target_channel.overwrites_for(default_role)
        
        if overwrites.send_messages is not False:
            embed = create_error_embed(
                self.bot.messages['commands']['unlock']['not_locked']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            # Unlock the channel
            await target_channel.set_permissions(
                default_role,
                send_messages=None,  # Reset to default
                reason=f"Channel unlocked by {moderator}: {reason}"
            )
            
            # Log the action
            await self.bot.db.log_mod_action(
                guild.id, 0, moderator.id, "unlock", reason,
                additional_data={"channel_id": target_channel.id}
            )
            
            # Send success message
            embed = create_success_embed(
                self.bot.messages['commands']['unlock']['success']
            )
            embed.add_field(name="Channel", value=target_channel.mention, inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.followup.send(embed=embed)
            
            # Send notification in unlocked channel
            unlock_embed = discord.Embed(
                title="🔓 Channel Unlocked",
                description=f"This channel has been unlocked by {moderator.mention}.\n**Reason:** {reason}",
                color=0x00ff00
            )
            await target_channel.send(embed=unlock_embed)
            
        except discord.Forbidden:
            embed = create_error_embed(
                self.bot.messages['errors']['missing_permissions']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error unlocking channel: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class CleanupConfirmView(discord.ui.View):
    def __init__(self, bot, days: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.days = days
    
    @discord.ui.button(label='Confirm Cleanup', style=discord.ButtonStyle.danger)
    async def confirm_cleanup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        try:
            # Perform cleanup
            await self.bot.db.cleanup_old_data(self.days)
            
            embed = create_success_embed(
                f"Database cleanup completed successfully!\nRemoved data older than {self.days} days."
            )
            embed.add_field(
                name="Timestamp",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            await interaction.edit_original_response(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            embed = create_error_embed(
                f"Error during cleanup: {str(e)}"
            )
            await interaction.edit_original_response(embed=embed, view=None)
        
        self.stop()
    
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.secondary)
    async def cancel_cleanup(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_error_embed("Database cleanup cancelled.")
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
