import discord
from discord.ext import commands
from typing import List, Union, Optional
import logging

logger = logging.getLogger(__name__)

class PermissionManager:
    def __init__(self, bot):
        self.bot = bot
    
    def get_config(self):
        """Get bot configuration"""
        return getattr(self.bot, 'config', {})
    
    def is_owner(self, user: Union[discord.User, discord.Member]) -> bool:
        """Check if user is bot owner"""
        config = self.get_config()
        owners = config.get('bot', {}).get('owners', [])
        return user.id in owners or self.bot.is_owner(user)
    
    def is_admin(self, member: discord.Member) -> bool:
        """Check if member has admin permissions"""
        if self.is_owner(member):
            return True
        
        # Check if member has administrator permission
        if member.guild_permissions.administrator:
            return True
        
        # Check configured admin roles
        config = self.get_config()
        admin_roles = config.get('permissions', {}).get('admin_roles', [])
        
        for role in member.roles:
            if role.id in admin_roles:
                return True
        
        return False
    
    def is_moderator(self, member: discord.Member) -> bool:
        """Check if member has moderator permissions"""
        if self.is_admin(member):
            return True
        
        # Check configured moderator roles
        config = self.get_config()
        moderator_roles = config.get('permissions', {}).get('moderator_roles', [])
        
        for role in member.roles:
            if role.id in moderator_roles:
                return True
        
        return False
    
    def is_helper(self, member: discord.Member) -> bool:
        """Check if member has helper permissions"""
        if self.is_moderator(member):
            return True
        
        # Check configured helper roles
        config = self.get_config()
        helper_roles = config.get('permissions', {}).get('helper_roles', [])
        
        for role in member.roles:
            if role.id in helper_roles:
                return True
        
        return False
    
    def can_use_command(self, member: discord.Member, command_name: str) -> bool:
        """Check if member can use a specific command"""
        if self.is_owner(member):
            return True
        
        config = self.get_config()
        command_perms = config.get('permissions', {}).get('commands', {})
        
        required_perms = command_perms.get(command_name, [])
        
        if not required_perms:
            return True  # No specific permissions required
        
        for perm in required_perms:
            if perm == "admin" and self.is_admin(member):
                return True
            elif perm == "moderator" and self.is_moderator(member):
                return True
            elif perm == "helper" and self.is_helper(member):
                return True
        
        return False
    
    def get_user_level(self, member: discord.Member) -> str:
        """Get the highest permission level of a user"""
        if self.is_owner(member):
            return "owner"
        elif self.is_admin(member):
            return "admin"
        elif self.is_moderator(member):
            return "moderator"
        elif self.is_helper(member):
            return "helper"
        else:
            return "user"
    
    def check_hierarchy(self, moderator: discord.Member, target: discord.Member) -> bool:
        """Check if moderator can act on target based on role hierarchy"""
        if self.is_owner(moderator):
            return True
        
        if target == moderator.guild.owner:
            return False
        
        if moderator == moderator.guild.owner:
            return True
        
        # Check role hierarchy
        if moderator.top_role.position <= target.top_role.position:
            return False
        
        return True

def has_permissions(permission_level: str):
    """Decorator to check permissions for commands"""
    def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        
        bot = interaction.client
        perm_manager = getattr(bot, 'permissions', None)
        
        if not perm_manager:
            return False
        
        if permission_level == "owner":
            return perm_manager.is_owner(interaction.user)
        elif permission_level == "admin":
            return perm_manager.is_admin(interaction.user)
        elif permission_level == "moderator":
            return perm_manager.is_moderator(interaction.user)
        elif permission_level == "helper":
            return perm_manager.is_helper(interaction.user)
        
        return True
    
    return discord.app_commands.check(predicate)

def can_use_command(command_name: str):
    """Decorator to check if user can use a specific command"""
    def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        
        bot = interaction.client
        perm_manager = getattr(bot, 'permissions', None)
        
        if not perm_manager:
            return False
        
        return perm_manager.can_use_command(interaction.user, command_name)
    
    return discord.app_commands.check(predicate)

def check_hierarchy():
    """Decorator to check role hierarchy for moderation commands"""
    def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        
        # Get target from command parameters
        target = None
        if hasattr(interaction, 'namespace') and hasattr(interaction.namespace, 'user'):
            target = interaction.namespace.user
        elif hasattr(interaction, 'namespace') and hasattr(interaction.namespace, 'member'):
            target = interaction.namespace.member
        
        if not target or not isinstance(target, discord.Member):
            return True  # No target to check hierarchy against
        
        bot = interaction.client
        perm_manager = getattr(bot, 'permissions', None)
        
        if not perm_manager:
            return False
        
        return perm_manager.check_hierarchy(interaction.user, target)
    
    return discord.app_commands.check(predicate)

class PermissionError(commands.CheckFailure):
    """Exception raised when permission check fails"""
    pass

class HierarchyError(commands.CheckFailure):
    """Exception raised when hierarchy check fails"""
    pass

async def permission_error_handler(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle permission-related errors"""
    if isinstance(error, discord.app_commands.CheckFailure):
        bot = interaction.client
        messages = getattr(bot, 'messages', {})
        
        error_msg = messages.get('commands', {}).get('no_permission', 
                                                   "❌ You don't have permission to use this command.")
        
        embed = discord.Embed(
            title="Permission Denied",
            description=error_msg,
            color=0xff0000
        )
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to send permission error message: {e}")

def setup_permissions(bot):
    """Setup permission system for the bot"""
    bot.permissions = PermissionManager(bot)
    
    # Add error handler
    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        await permission_error_handler(interaction, error)
