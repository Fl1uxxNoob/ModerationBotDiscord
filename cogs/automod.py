import discord
from discord.ext import commands
import re
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
from utils.helpers import calculate_caps_ratio, calculate_text_similarity, extract_invite_code
from utils.permissions import PermissionManager

logger = logging.getLogger(__name__)

class AutoModerationCog(commands.Cog, name="Auto Moderation"):
    def __init__(self, bot):
        self.bot = bot
        
        # Track user message history for spam detection
        self.user_messages = defaultdict(lambda: deque(maxlen=10))
        self.user_violations = defaultdict(int)
        
        # Cache for recent messages for similarity checking
        self.recent_messages = defaultdict(lambda: deque(maxlen=5))
    
    def is_staff(self, member: discord.Member) -> bool:
        """Check if member is staff (immune to automod)"""
        if not hasattr(self.bot, 'permissions'):
            return False
        return self.bot.permissions.is_helper(member)
    
    async def punish_user(self, member: discord.Member, punishment: str, reason: str, duration: int = None):
        """Apply punishment to user"""
        try:
            if punishment == "warn":
                await self.bot.db.add_warning(
                    member.guild.id, member.id, self.bot.user.id, reason
                )
                
                # Get warning count for potential auto-punishment
                warning_count = await self.bot.db.get_warning_count(member.guild.id, member.id)
                max_warnings = self.bot.config['bot']['max_warnings']
                
                if (warning_count >= max_warnings and 
                    self.bot.config['bot']['auto_punish_on_max_warnings']):
                    
                    # Auto-timeout for 1 hour
                    until = datetime.now() + timedelta(hours=1)
                    await member.timeout(until, reason="Maximum warnings reached (automod)")
                    
                    await self.bot.db.log_mod_action(
                        member.guild.id, member.id, self.bot.user.id, 
                        "auto_timeout", "Maximum warnings reached (automod)", 3600
                    )
            
            elif punishment == "timeout":
                timeout_duration = timedelta(seconds=duration) if duration else timedelta(minutes=10)
                until = datetime.now() + timeout_duration
                await member.timeout(until, reason=reason)
                
                await self.bot.db.log_mod_action(
                    member.guild.id, member.id, self.bot.user.id, "timeout", reason,
                    int(timeout_duration.total_seconds())
                )
            
            elif punishment == "kick":
                await member.kick(reason=reason)
                await self.bot.db.log_mod_action(
                    member.guild.id, member.id, self.bot.user.id, "kick", reason
                )
            
            elif punishment == "ban":
                await member.ban(reason=reason, delete_message_days=1)
                await self.bot.db.log_mod_action(
                    member.guild.id, member.id, self.bot.user.id, "ban", reason
                )
                
        except discord.Forbidden:
            logger.warning(f"No permission to punish {member} in {member.guild}")
        except Exception as e:
            logger.error(f"Error punishing user {member}: {e}")
    
    async def send_automod_log(self, message: discord.Message, violation_type: str, action_taken: str):
        """Send automod log to logging channel"""
        # Log to database
        await self.bot.db.log_automod_violation(
            message.guild.id, message.author.id, violation_type,
            message.content, message.channel.id, action_taken
        )
        
        # Get logging channel
        log_channel_name = self.bot.config['moderation']['log_channel_name']
        log_channel = discord.utils.get(message.guild.text_channels, name=log_channel_name)
        
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="🤖 Auto-Moderation Action",
            color=0xff6600,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="User",
            value=f"{message.author} ({message.author.id})",
            inline=True
        )
        embed.add_field(
            name="Channel",
            value=message.channel.mention,
            inline=True
        )
        embed.add_field(
            name="Violation",
            value=violation_type,
            inline=True
        )
        embed.add_field(
            name="Action Taken",
            value=action_taken,
            inline=True
        )
        
        if message.content:
            embed.add_field(
                name="Content",
                value=message.content[:1024] if len(message.content) > 1024 else message.content,
                inline=False
            )
        
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url
        )
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Process messages for auto-moderation"""
        # Skip if not in guild, is bot, or is staff
        if not message.guild or message.author.bot or self.is_staff(message.author):
            return
        
        # Skip if automod is disabled
        if not self.bot.config.get('moderation', {}).get('spam', {}).get('enabled', False):
            return
        
        member = message.author
        guild = message.guild
        
        # Check for spam
        await self.check_spam(message)
        
        # Check for excessive caps
        await self.check_caps(message)
        
        # Check for repeated text
        await self.check_repeated_text(message)
        
        # Check for bad words
        await self.check_bad_words(message)
        
        # Check for invite links
        await self.check_invite_links(message)
    
    async def check_spam(self, message: discord.Message):
        """Check for spam (too many messages in short time)"""
        config = self.bot.config['moderation']['spam']
        if not config['enabled']:
            return
        
        user_id = message.author.id
        now = datetime.now()
        
        # Add current message to user's history
        self.user_messages[user_id].append(now)
        
        # Count messages in time window
        time_window = timedelta(seconds=config['time_window'])
        recent_messages = [
            msg_time for msg_time in self.user_messages[user_id]
            if now - msg_time <= time_window
        ]
        
        if len(recent_messages) >= config['max_messages']:
            # Spam detected
            try:
                await message.delete()
            except discord.NotFound:
                pass  # Message already deleted
            except discord.Forbidden:
                pass  # No permission to delete
            
            # Apply punishment
            punishment = config['punishment']
            duration = config.get('duration', 600)  # Default 10 minutes
            
            await self.punish_user(
                message.author, punishment, 
                "Spam detection", duration
            )
            
            # Send warning message
            warning_msg = self.bot.messages['automod']['spam']['punishment'].format(
                user=message.author.display_name
            )
            
            try:
                warning = await message.channel.send(warning_msg)
                # Delete warning after 5 seconds
                await warning.delete(delay=5)
            except discord.Forbidden:
                pass
            
            await self.send_automod_log(message, "Spam", f"{punishment} applied")
            
            # Clear user's message history to prevent further triggers
            self.user_messages[user_id].clear()
    
    async def check_caps(self, message: discord.Message):
        """Check for excessive capital letters"""
        config = self.bot.config['moderation']['caps']
        if not config['enabled']:
            return
        
        content = message.content
        if len(content) < config['min_length']:
            return
        
        caps_ratio = calculate_caps_ratio(content)
        
        if caps_ratio >= config['threshold']:
            # Excessive caps detected
            try:
                await message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass
            
            # Apply punishment
            punishment = config['punishment']
            await self.punish_user(
                message.author, punishment, 
                "Excessive capital letters"
            )
            
            # Send warning message
            warning_msg = self.bot.messages['automod']['caps']['warning'].format(
                user=message.author.display_name
            )
            
            try:
                warning = await message.channel.send(warning_msg)
                await warning.delete(delay=5)
            except discord.Forbidden:
                pass
            
            await self.send_automod_log(message, "Excessive Caps", f"{punishment} applied")
    
    async def check_repeated_text(self, message: discord.Message):
        """Check for repeated/similar text"""
        config = self.bot.config['moderation']['repeated_text']
        if not config['enabled']:
            return
        
        content = message.content.lower()
        channel_id = message.channel.id
        
        # Add to recent messages
        self.recent_messages[channel_id].append(content)
        
        # Check similarity with recent messages
        for recent_content in list(self.recent_messages[channel_id])[:-1]:  # Exclude current message
            similarity = calculate_text_similarity(content, recent_content)
            
            if similarity >= config['threshold']:
                # Repeated text detected
                try:
                    await message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    pass
                
                # Apply punishment
                punishment = config['punishment']
                await self.punish_user(
                    message.author, punishment, 
                    "Repeated text"
                )
                
                # Send warning message
                warning_msg = self.bot.messages['automod']['repeated_text']['warning'].format(
                    user=message.author.display_name
                )
                
                try:
                    warning = await message.channel.send(warning_msg)
                    await warning.delete(delay=5)
                except discord.Forbidden:
                    pass
                
                await self.send_automod_log(message, "Repeated Text", f"{punishment} applied")
                break
    
    async def check_bad_words(self, message: discord.Message):
        """Check for bad words"""
        config = self.bot.config['moderation']['bad_words']
        if not config['enabled']:
            return
        
        bad_words = config.get('words', [])
        if not bad_words:
            return
        
        content = message.content.lower()
        
        # Check for bad words
        for bad_word in bad_words:
            if bad_word.lower() in content:
                # Bad word detected
                try:
                    await message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    pass
                
                # Apply punishment
                punishment = config['punishment']
                await self.punish_user(
                    message.author, punishment, 
                    f"Inappropriate language: {bad_word}"
                )
                
                # Send warning message
                warning_msg = self.bot.messages['automod']['bad_words']['warning'].format(
                    user=message.author.display_name
                )
                
                try:
                    warning = await message.channel.send(warning_msg)
                    await warning.delete(delay=5)
                except discord.Forbidden:
                    pass
                
                await self.send_automod_log(message, "Inappropriate Language", f"{punishment} applied")
                break
    
    async def check_invite_links(self, message: discord.Message):
        """Check for Discord invite links"""
        config = self.bot.config['moderation']['invite_links']
        if not config['enabled']:
            return
        
        invite_code = extract_invite_code(message.content)
        if not invite_code:
            return
        
        # Check if invite is whitelisted
        whitelist = config.get('whitelist', [])
        
        try:
            invite = await self.bot.fetch_invite(invite_code)
            if invite.guild and invite.guild.id in whitelist:
                return  # Whitelisted server
        except discord.NotFound:
            pass  # Invalid invite
        except discord.HTTPException:
            pass  # Error fetching invite
        
        # Invite link detected (not whitelisted)
        try:
            await message.delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        
        # Apply punishment
        punishment = config['punishment']
        await self.punish_user(
            message.author, punishment, 
            "Unauthorized invite link"
        )
        
        # Send warning message
        warning_msg = self.bot.messages['automod']['invite_links']['warning'].format(
            user=message.author.display_name
        )
        
        try:
            warning = await message.channel.send(warning_msg)
            await warning.delete(delay=5)
        except discord.Forbidden:
            pass
        
        await self.send_automod_log(message, "Invite Link", f"{punishment} applied")

async def setup(bot):
    await bot.add_cog(AutoModerationCog(bot))
