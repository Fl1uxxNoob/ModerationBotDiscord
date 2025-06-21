import yaml
import discord
from datetime import datetime, timedelta
import re
from typing import Optional, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file {config_path} not found!")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file: {e}")
        return {}

def load_messages(messages_path: str = "messages.yml") -> Dict[str, Any]:
    """Load messages from YAML file"""
    try:
        with open(messages_path, 'r', encoding='utf-8') as file:
            messages = yaml.safe_load(file)
        return messages
    except FileNotFoundError:
        logger.error(f"Messages file {messages_path} not found!")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing messages file: {e}")
        return {}

def parse_duration(duration_str: str) -> Optional[timedelta]:
    """Parse duration string into timedelta object
    
    Supports formats like:
    - 1m, 30m, 1h, 2d, 1w
    - 1 minute, 30 minutes, 1 hour, 2 days, 1 week
    """
    if not duration_str:
        return None
    
    # Remove extra spaces and convert to lowercase
    duration_str = duration_str.strip().lower()
    
    # Regex patterns for different formats
    patterns = [
        (r'(\d+)\s*s(?:ec(?:ond)?s?)?', 1),  # seconds
        (r'(\d+)\s*m(?:in(?:ute)?s?)?', 60),  # minutes
        (r'(\d+)\s*h(?:(?:ou)?rs?)?', 3600),  # hours
        (r'(\d+)\s*d(?:ays?)?', 86400),  # days
        (r'(\d+)\s*w(?:eeks?)?', 604800),  # weeks
    ]
    
    total_seconds = 0
    
    for pattern, multiplier in patterns:
        matches = re.findall(pattern, duration_str)
        for match in matches:
            total_seconds += int(match) * multiplier
    
    if total_seconds > 0:
        return timedelta(seconds=total_seconds)
    
    return None

def format_duration(duration: Union[timedelta, int]) -> str:
    """Format duration into human-readable string"""
    if isinstance(duration, int):
        duration = timedelta(seconds=duration)
    
    if not isinstance(duration, timedelta):
        return "Unknown duration"
    
    total_seconds = int(duration.total_seconds())
    
    if total_seconds == 0:
        return "0 seconds"
    
    units = [
        ('week', 604800),
        ('day', 86400),
        ('hour', 3600),
        ('minute', 60),
        ('second', 1)
    ]
    
    parts = []
    
    for unit_name, unit_seconds in units:
        if total_seconds >= unit_seconds:
            unit_count = total_seconds // unit_seconds
            total_seconds %= unit_seconds
            
            if unit_count == 1:
                parts.append(f"{unit_count} {unit_name}")
            else:
                parts.append(f"{unit_count} {unit_name}s")
    
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    else:
        return ", ".join(parts[:-1]) + f", and {parts[-1]}"

def create_embed(title: str, description: str = None, color: int = 0x0099ff, 
                **kwargs) -> discord.Embed:
    """Create a Discord embed with consistent formatting"""
    embed = discord.Embed(title=title, description=description, color=color)
    
    # Add timestamp
    embed.timestamp = datetime.utcnow()
    
    # Add fields from kwargs
    for key, value in kwargs.items():
        if key.startswith('field_'):
            field_name = key.replace('field_', '').replace('_', ' ').title()
            embed.add_field(name=field_name, value=value, inline=False)
    
    return embed

def create_error_embed(message: str, title: str = "Error") -> discord.Embed:
    """Create an error embed"""
    return create_embed(title=f"❌ {title}", description=message, color=0xff0000)

def create_success_embed(message: str, title: str = "Success") -> discord.Embed:
    """Create a success embed"""
    return create_embed(title=f"✅ {title}", description=message, color=0x00ff00)

def create_warning_embed(message: str, title: str = "Warning") -> discord.Embed:
    """Create a warning embed"""
    return create_embed(title=f"⚠️ {title}", description=message, color=0xffff00)

def create_info_embed(message: str, title: str = "Information") -> discord.Embed:
    """Create an info embed"""
    return create_embed(title=f"ℹ️ {title}", description=message, color=0x0099ff)

def truncate_text(text: str, max_length: int = 1024) -> str:
    """Truncate text to fit Discord embed limits"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def get_user_avatar(user: Union[discord.User, discord.Member]) -> str:
    """Get user avatar URL"""
    if user.avatar:
        return user.avatar.url
    return user.default_avatar.url

def format_user(user: Union[discord.User, discord.Member]) -> str:
    """Format user for display"""
    return f"{user.display_name} ({user.name}#{user.discriminator})"

def format_timestamp(timestamp: datetime, style: str = "F") -> str:
    """Format timestamp for Discord"""
    unix_timestamp = int(timestamp.timestamp())
    return f"<t:{unix_timestamp}:{style}>"

def check_hierarchy(guild: discord.Guild, moderator: discord.Member, 
                   target: discord.Member) -> bool:
    """Check if moderator can act on target based on role hierarchy"""
    if moderator == guild.owner:
        return True
    
    if target == guild.owner:
        return False
    
    if moderator.top_role.position <= target.top_role.position:
        return False
    
    return True

def is_url(text: str) -> bool:
    """Check if text contains a URL"""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return url_pattern.search(text) is not None

def extract_invite_code(text: str) -> Optional[str]:
    """Extract Discord invite code from text"""
    invite_patterns = [
        r'discord\.gg/([a-zA-Z0-9]+)',
        r'discord\.com/invite/([a-zA-Z0-9]+)',
        r'discordapp\.com/invite/([a-zA-Z0-9]+)'
    ]
    
    for pattern in invite_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None

def calculate_caps_ratio(text: str) -> float:
    """Calculate the ratio of capital letters in text"""
    if not text:
        return 0.0
    
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return 0.0
    
    caps_count = sum(1 for c in alpha_chars if c.isupper())
    return caps_count / len(alpha_chars)

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using simple ratio"""
    if not text1 or not text2:
        return 0.0
    
    # Simple character-based similarity
    shorter = min(text1, text2, key=len)
    longer = max(text1, text2, key=len)
    
    if len(longer) == 0:
        return 1.0
    
    matches = sum(1 for i, c in enumerate(shorter) if i < len(longer) and c == longer[i])
    return matches / len(longer)

def clean_content(content: str) -> str:
    """Clean message content for logging (remove mentions, etc.)"""
    # Remove user mentions
    content = re.sub(r'<@!?(\d+)>', r'@\1', content)
    # Remove role mentions
    content = re.sub(r'<@&(\d+)>', r'@role:\1', content)
    # Remove channel mentions
    content = re.sub(r'<#(\d+)>', r'#\1', content)
    
    return content

def get_permissions_list(permissions: discord.Permissions) -> list:
    """Get list of permission names from Permissions object"""
    perms = []
    for perm, value in permissions:
        if value:
            perms.append(perm.replace('_', ' ').title())
    return perms

def format_permissions(permissions: list) -> str:
    """Format permissions list for display"""
    if not permissions:
        return "None"
    
    if len(permissions) <= 3:
        return ", ".join(permissions)
    else:
        return f"{', '.join(permissions[:3])} and {len(permissions) - 3} more"

class Paginator:
    """Helper class for pagination"""
    
    def __init__(self, entries: list, per_page: int = 10):
        self.entries = entries
        self.per_page = per_page
        self.pages = []
        
        # Split entries into pages
        for i in range(0, len(entries), per_page):
            self.pages.append(entries[i:i + per_page])
    
    def get_page(self, page_num: int) -> list:
        """Get a specific page"""
        if 0 <= page_num < len(self.pages):
            return self.pages[page_num]
        return []
    
    @property
    def max_pages(self) -> int:
        """Get total number of pages"""
        return len(self.pages)

def validate_reason(reason: str, max_length: int = 512) -> Optional[str]:
    """Validate and clean reason string"""
    if not reason:
        return None
    
    reason = reason.strip()
    if len(reason) > max_length:
        reason = reason[:max_length - 3] + "..."
    
    return reason
