import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime, timedelta
import logging
from utils.helpers import create_embed, create_error_embed, format_duration, format_timestamp, Paginator
from utils.permissions import has_permissions, can_use_command

logger = logging.getLogger(__name__)

class HistoryCog(commands.Cog, name="History"):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="history", description="View moderation history for a user")
    @app_commands.describe(
        user="The user to view history for",
        limit="Number of entries to show (max 50)"
    )
    @can_use_command("history")
    async def history(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        limit: Optional[app_commands.Range[int, 1, 50]] = 25
    ):
        """View moderation history for a user"""
        await interaction.response.defer()
        
        try:
            # Get user history from database
            history = await self.bot.db.get_user_history(interaction.guild.id, user.id, limit)
            
            if not history:
                embed = create_error_embed(
                    self.bot.messages['history']['no_history']
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create main embed
            embed = discord.Embed(
                title=f"📋 Moderation History - {user.display_name}",
                description=f"Showing {len(history)} most recent entries",
                color=0x0099ff,
                timestamp=datetime.utcnow()
            )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(
                name="User",
                value=f"{user} ({user.id})",
                inline=True
            )
            embed.add_field(
                name="Total Actions",
                value=str(len(history)),
                inline=True
            )
            
            # Get current warnings count
            warnings_count = await self.bot.db.get_warning_count(interaction.guild.id, user.id)
            max_warnings = self.bot.config['bot']['max_warnings']
            embed.add_field(
                name="Active Warnings",
                value=f"{warnings_count}/{max_warnings}",
                inline=True
            )
            
            # Add history entries
            history_text = ""
            for entry in history[:10]:  # Show first 10 entries in embed
                moderator = interaction.guild.get_member(entry['moderator_id'])
                moderator_name = moderator.display_name if moderator else f"ID: {entry['moderator_id']}"
                
                action_emoji = {
                    'ban': '🔨',
                    'tempban': '🔨',
                    'unban': '✅',
                    'kick': '👢',
                    'timeout': '🔇',
                    'untimeout': '🔊',
                    'warn': '⚠️',
                    'unwarn': '✅',
                    'auto_timeout': '🤖',
                    'purge': '🗑️'
                }.get(entry['action_type'], '📝')
                
                timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                
                entry_text = f"{action_emoji} **{entry['action_type'].title()}** by {moderator_name}\n"
                entry_text += f"└ {format_timestamp(timestamp, 'R')}"
                
                if entry['reason']:
                    entry_text += f" • {entry['reason'][:100]}{'...' if len(entry['reason']) > 100 else ''}"
                
                if entry['duration']:
                    duration = timedelta(seconds=entry['duration'])
                    entry_text += f" • Duration: {format_duration(duration)}"
                
                entry_text += "\n"
                
                if len(history_text + entry_text) > 1024:
                    break
                history_text += entry_text
            
            if history_text:
                embed.add_field(
                    name="Recent Actions",
                    value=history_text,
                    inline=False
                )
            
            if len(history) > 10:
                embed.set_footer(text=f"Showing 10 of {len(history)} entries. Use /fullhistory for complete history.")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error retrieving user history: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="fullhistory", description="View complete moderation history for a user")
    @app_commands.describe(
        user="The user to view history for"
    )
    @can_use_command("history")
    async def full_history(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):
        """View complete moderation history for a user with pagination"""
        await interaction.response.defer()
        
        try:
            # Get complete user history
            history = await self.bot.db.get_user_history(interaction.guild.id, user.id, 1000)
            
            if not history:
                embed = create_error_embed(
                    self.bot.messages['history']['no_history']
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create paginated view
            paginator = Paginator(history, per_page=5)
            current_page = 0
            
            def create_history_embed(page_entries, page_num):
                embed = discord.Embed(
                    title=f"📋 Complete History - {user.display_name}",
                    description=f"Page {page_num + 1}/{paginator.max_pages} • Total: {len(history)} entries",
                    color=0x0099ff,
                    timestamp=datetime.utcnow()
                )
                
                embed.set_thumbnail(url=user.display_avatar.url)
                
                for entry in page_entries:
                    moderator = interaction.guild.get_member(entry['moderator_id'])
                    moderator_name = moderator.display_name if moderator else f"ID: {entry['moderator_id']}"
                    
                    action_emoji = {
                        'ban': '🔨',
                        'tempban': '🔨',
                        'unban': '✅',
                        'kick': '👢',
                        'timeout': '🔇',
                        'untimeout': '🔊',
                        'warn': '⚠️',
                        'unwarn': '✅',
                        'auto_timeout': '🤖',
                        'purge': '🗑️'
                    }.get(entry['action_type'], '📝')
                    
                    timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    
                    field_name = f"{action_emoji} {entry['action_type'].title()}"
                    field_value = f"**Moderator:** {moderator_name}\n"
                    field_value += f"**Time:** {format_timestamp(timestamp, 'F')}\n"
                    
                    if entry['reason']:
                        field_value += f"**Reason:** {entry['reason']}\n"
                    
                    if entry['duration']:
                        duration = timedelta(seconds=entry['duration'])
                        field_value += f"**Duration:** {format_duration(duration)}\n"
                    
                    embed.add_field(
                        name=field_name,
                        value=field_value,
                        inline=False
                    )
                
                return embed
            
            # Create view with navigation buttons
            view = HistoryPaginationView(paginator, create_history_embed, user)
            embed = create_history_embed(paginator.get_page(0), 0)
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error retrieving full user history: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="warnings", description="View active warnings for a user")
    @app_commands.describe(
        user="The user to view warnings for"
    )
    @can_use_command("history")
    async def warnings(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):
        """View active warnings for a user"""
        await interaction.response.defer()
        
        try:
            # Get warnings from database
            warnings = await self.bot.db.get_warnings(interaction.guild.id, user.id)
            
            if not warnings:
                embed = create_error_embed(
                    f"{user.display_name} has no active warnings."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create embed
            embed = discord.Embed(
                title=f"⚠️ Active Warnings - {user.display_name}",
                description=f"{len(warnings)} active warning(s)",
                color=0xffff00,
                timestamp=datetime.utcnow()
            )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            
            max_warnings = self.bot.config['bot']['max_warnings']
            embed.add_field(
                name="Warning Count",
                value=f"{len(warnings)}/{max_warnings}",
                inline=True
            )
            
            # Add warning details
            for i, warning in enumerate(warnings[:10], 1):  # Show up to 10 warnings
                moderator = interaction.guild.get_member(warning['moderator_id'])
                moderator_name = moderator.display_name if moderator else f"ID: {warning['moderator_id']}"
                
                timestamp = datetime.fromisoformat(warning['timestamp'].replace('Z', '+00:00'))
                
                embed.add_field(
                    name=f"Warning #{i}",
                    value=f"**Moderator:** {moderator_name}\n"
                           f"**Date:** {format_timestamp(timestamp, 'F')}\n"
                           f"**Reason:** {warning['reason']}",
                    inline=False
                )
            
            if len(warnings) > 10:
                embed.set_footer(text=f"Showing 10 of {len(warnings)} warnings")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error retrieving user warnings: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="stafflogs", description="View staff command logs")
    @app_commands.describe(
        staff="Staff member to view logs for (optional)",
        limit="Number of entries to show (max 100)"
    )
    @has_permissions("admin")
    async def staff_logs(
        self,
        interaction: discord.Interaction,
        staff: Optional[discord.Member] = None,
        limit: Optional[app_commands.Range[int, 1, 100]] = 50
    ):
        """View staff command logs"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get staff logs from database
            logs = await self.bot.db.get_staff_logs(
                interaction.guild.id, 
                staff.id if staff else None, 
                limit
            )
            
            if not logs:
                embed = create_error_embed(
                    "No staff logs found."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create embed
            title = f"👑 Staff Logs"
            if staff:
                title += f" - {staff.display_name}"
            
            embed = discord.Embed(
                title=title,
                description=f"Showing {len(logs)} most recent entries",
                color=0x36393e,
                timestamp=datetime.utcnow()
            )
            
            if staff:
                embed.set_thumbnail(url=staff.display_avatar.url)
            
            # Add log entries
            log_text = ""
            for log in logs[:15]:  # Show first 15 entries
                staff_member = interaction.guild.get_member(log['staff_id'])
                staff_name = staff_member.display_name if staff_member else f"ID: {log['staff_id']}"
                
                timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                
                status_emoji = "✅" if log['success'] else "❌"
                entry_text = f"{status_emoji} **{log['command']}** by {staff_name}\n"
                entry_text += f"└ {format_timestamp(timestamp, 'R')}"
                
                if log['target_id']:
                    target = interaction.guild.get_member(log['target_id'])
                    target_name = target.display_name if target else f"ID: {log['target_id']}"
                    entry_text += f" • Target: {target_name}"
                
                if log['arguments']:
                    args = log['arguments'][:50] + "..." if len(log['arguments']) > 50 else log['arguments']
                    entry_text += f" • Args: {args}"
                
                entry_text += "\n"
                
                if len(log_text + entry_text) > 1024:
                    break
                log_text += entry_text
            
            if log_text:
                embed.add_field(
                    name="Recent Commands",
                    value=log_text,
                    inline=False
                )
            
            if len(logs) > 15:
                embed.set_footer(text=f"Showing 15 of {len(logs)} entries")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error retrieving staff logs: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="automodlogs", description="View auto-moderation violation logs")
    @app_commands.describe(
        user="User to view violations for (optional)",
        violation_type="Type of violation to filter by",
        limit="Number of entries to show (max 50)"
    )
    @has_permissions("moderator")
    async def automod_logs(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        violation_type: Optional[str] = None,
        limit: Optional[app_commands.Range[int, 1, 50]] = 25
    ):
        """View auto-moderation violation logs"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get automod violations from database
            violations = await self.bot.db.get_automod_violations(
                interaction.guild.id,
                user.id if user else None,
                violation_type,
                limit
            )
            
            if not violations:
                embed = create_error_embed(
                    "No auto-moderation violations found."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create embed
            title = "🤖 Auto-Moderation Logs"
            if user:
                title += f" - {user.display_name}"
            if violation_type:
                title += f" - {violation_type.title()}"
            
            embed = discord.Embed(
                title=title,
                description=f"Showing {len(violations)} most recent violations",
                color=0xff6600,
                timestamp=datetime.utcnow()
            )
            
            if user:
                embed.set_thumbnail(url=user.display_avatar.url)
            
            # Add violation entries
            for violation in violations[:10]:  # Show first 10 violations
                violator = interaction.guild.get_member(violation['user_id'])
                violator_name = violator.display_name if violator else f"ID: {violation['user_id']}"
                
                channel = interaction.guild.get_channel(violation['channel_id'])
                channel_name = channel.mention if channel else f"ID: {violation['channel_id']}"
                
                timestamp = datetime.fromisoformat(violation['timestamp'].replace('Z', '+00:00'))
                
                field_name = f"{violation['violation_type'].title()} Violation"
                field_value = f"**User:** {violator_name}\n"
                field_value += f"**Channel:** {channel_name}\n"
                field_value += f"**Time:** {format_timestamp(timestamp, 'F')}\n"
                
                if violation['action_taken']:
                    field_value += f"**Action:** {violation['action_taken']}\n"
                
                if violation['content']:
                    content = violation['content'][:100] + "..." if len(violation['content']) > 100 else violation['content']
                    field_value += f"**Content:** {content}"
                
                embed.add_field(
                    name=field_name,
                    value=field_value,
                    inline=False
                )
            
            if len(violations) > 10:
                embed.set_footer(text=f"Showing 10 of {len(violations)} violations")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error retrieving automod logs: {e}")
            embed = create_error_embed(
                self.bot.messages['commands']['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class HistoryPaginationView(discord.ui.View):
    def __init__(self, paginator: Paginator, embed_func, user: discord.User):
        super().__init__(timeout=300)
        self.paginator = paginator
        self.embed_func = embed_func
        self.user = user
        self.current_page = 0
        
        # Disable buttons if only one page
        if paginator.max_pages <= 1:
            for item in self.children:
                item.disabled = True
    
    async def update_embed(self, interaction: discord.Interaction):
        """Update the embed with current page"""
        page_entries = self.paginator.get_page(self.current_page)
        embed = self.embed_func(page_entries, self.current_page)
        
        # Update button states
        self.first_page.disabled = self.current_page == 0
        self.previous_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.paginator.max_pages - 1
        self.last_page.disabled = self.current_page >= self.paginator.max_pages - 1
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='<<', style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        await self.update_embed(interaction)
    
    @discord.ui.button(label='<', style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        await self.update_embed(interaction)
    
    @discord.ui.button(label='>', style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.paginator.max_pages - 1:
            self.current_page += 1
        await self.update_embed(interaction)
    
    @discord.ui.button(label='>>', style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.paginator.max_pages - 1
        await self.update_embed(interaction)
    
    @discord.ui.button(label='Close', style=discord.ButtonStyle.danger)
    async def close_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(view=None)
        self.stop()

async def setup(bot):
    await bot.add_cog(HistoryCog(bot))
