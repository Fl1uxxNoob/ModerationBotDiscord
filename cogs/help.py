import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from utils.helpers import create_embed

logger = logging.getLogger(__name__)

class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="help", description="Show help information and available commands")
    @app_commands.describe(
        command="Specific command to get help for (optional)"
    )
    async def help(
        self,
        interaction: discord.Interaction,
        command: Optional[str] = None
    ):
        """Show help information and available commands"""
        if command:
            await self.show_command_help(interaction, command)
        else:
            await self.show_general_help(interaction)
    
    async def show_general_help(self, interaction: discord.Interaction):
        """Show general help with all commands"""
        embed = discord.Embed(
            title="🛡️ Moderation Bot - Command Help",
            description="A comprehensive moderation bot with slash commands, auto-moderation, and detailed logging.",
            color=0x0099ff
        )
        
        # Moderation commands
        moderation_commands = [
            "`/ban` - Ban a user from the server",
            "`/unban` - Unban a user from the server", 
            "`/kick` - Kick a user from the server",
            "`/timeout` - Timeout a user",
            "`/untimeout` - Remove timeout from a user",
            "`/warn` - Warn a user",
            "`/unwarn` - Remove a warning from a user",
            "`/purge` - Delete multiple messages"
        ]
        
        embed.add_field(
            name="⚔️ Moderation Commands",
            value="\n".join(moderation_commands),
            inline=False
        )
        
        # History commands
        history_commands = [
            "`/history` - View user's moderation history",
            "`/fullhistory` - View complete user history with pagination",
            "`/warnings` - View active warnings for a user",
            "`/stafflogs` - View staff command logs (Admin only)",
            "`/automodlogs` - View auto-moderation logs (Moderator+)"
        ]
        
        embed.add_field(
            name="📋 History & Logs",
            value="\n".join(history_commands),
            inline=False
        )
        
        # Admin commands
        admin_commands = [
            "`/setup` - Set up the bot for this server",
            "`/config` - Configure bot settings", 
            "`/backup` - Create database backup",
            "`/cleanup` - Clean up old database entries",
            "`/reload` - Reload bot configuration",
            "`/stats` - View bot statistics",
            "`/lock` - Lock a channel",
            "`/unlock` - Unlock a channel"
        ]
        
        embed.add_field(
            name="👑 Admin Commands",
            value="\n".join(admin_commands),
            inline=False
        )
        
        # Features
        features = [
            "🤖 **Auto-Moderation** - Spam, caps, bad words, invite links",
            "📊 **Comprehensive Logging** - All server events tracked", 
            "⏰ **Temporary Actions** - Auto-expiring bans and timeouts",
            "🛡️ **Permission System** - Role-based command access",
            "💾 **Database Storage** - SQLite with full history tracking",
            "📱 **Slash Commands** - Modern Discord interface"
        ]
        
        embed.add_field(
            name="✨ Features",
            value="\n".join(features),
            inline=False
        )
        
        embed.add_field(
            name="🔧 Quick Start",
            value="1. Run `/setup` to configure the bot\n"
                  "2. Use `/config roles` to set permission roles\n"
                  "3. Check `/config` for all settings\n"
                  "4. View `/help <command>` for specific help",
            inline=False
        )
        
        embed.set_footer(text="Use /help <command> for detailed information about a specific command")
        
        await interaction.response.send_message(embed=embed)
    
    async def show_command_help(self, interaction: discord.Interaction, command_name: str):
        """Show detailed help for a specific command"""
        # Command details
        command_help = {
            "ban": {
                "description": "Ban a user from the server with optional duration",
                "usage": "/ban <user> [reason] [duration] [delete_messages]",
                "examples": [
                    "/ban @user Spamming",
                    "/ban @user Harassment 7d",
                    "/ban 123456789 Rule violation 1h 3"
                ],
                "permissions": "Moderator or Admin"
            },
            "timeout": {
                "description": "Temporarily restrict a user from sending messages",
                "usage": "/timeout <user> [duration] [reason]", 
                "examples": [
                    "/timeout @user Being disruptive",
                    "/timeout @user 30m Please calm down",
                    "/timeout @user 2h Multiple warnings"
                ],
                "permissions": "Helper, Moderator, or Admin"
            },
            "warn": {
                "description": "Issue a warning to a user",
                "usage": "/warn <user> <reason>",
                "examples": [
                    "/warn @user Please follow the rules",
                    "/warn @user Inappropriate language"
                ],
                "permissions": "Helper, Moderator, or Admin"
            },
            "history": {
                "description": "View moderation history for a user",
                "usage": "/history <user> [limit]",
                "examples": [
                    "/history @user",
                    "/history @user 10"
                ],
                "permissions": "Moderator or Admin"
            },
            "setup": {
                "description": "Initialize the bot for your server",
                "usage": "/setup",
                "examples": ["/setup"],
                "permissions": "Admin only"
            },
            "config": {
                "description": "View or configure bot settings",
                "usage": "/config <setting> [action]",
                "examples": [
                    "/config roles view",
                    "/config automod view",
                    "/config logging view"
                ],
                "permissions": "Admin only"
            }
        }
        
        if command_name.lower() not in command_help:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"No help found for command: `{command_name}`\n\nUse `/help` to see all available commands.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        cmd_info = command_help[command_name.lower()]
        
        embed = discord.Embed(
            title=f"📖 Help: /{command_name}",
            description=cmd_info["description"],
            color=0x0099ff
        )
        
        embed.add_field(
            name="Usage",
            value=f"`{cmd_info['usage']}`",
            inline=False
        )
        
        embed.add_field(
            name="Examples",
            value="\n".join([f"`{ex}`" for ex in cmd_info["examples"]]),
            inline=False
        )
        
        embed.add_field(
            name="Required Permissions",
            value=cmd_info["permissions"],
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))