# Discord Moderation Bot

A complete and professional Discord moderation bot built in Python with slash commands, auto-moderation, and detailed logging.

## Features

### 🛡️ Complete Moderation
- **Ban/Unban** - With temporary ban support
- **Kick** - Immediate removal from server
- **Timeout** - Automatic temporary muting
- **Warn/Unwarn** - Warning system with auto-punishment
- **Purge** - Mass message deletion

### 🤖 Auto-Moderation
- **Anti-Spam** - Rapid message detection
- **Anti-Caps** - Excessive uppercase control
- **Word Filter** - Customizable banned words list
- **Anti-Invite** - Discord invite link blocking
- **Repeated Text** - Duplicate content detection

### 📊 Complete Logging
- **Message Events** - Modifications and deletions
- **Member Events** - Joins, leaves, bans, unbans
- **Server Events** - Roles, channels, voice states
- **Staff Logs** - Moderator command tracking
- **Auto-Mod Logs** - Automatic violations

### 💾 SQLite Database
- **User History** - Complete moderation history
- **Active Warnings** - Persistent warning management
- **Temporary Actions** - Auto-removal on expiry
- **Automatic Backups** - Data protection
- **Automatic Cleanup** - Storage space management

### 🔐 Permission System
- **Hierarchical Roles** - Admin, Moderators, Helpers
- **Command Control** - Role-based access
- **Hierarchy Control** - Superior role protection

## Quick Setup

### 1. Discord Bot Configuration
1. Go to https://discord.com/developers/applications
2. Create a new application
3. Go to the "Bot" section
4. Copy the bot token
5. Invite the bot to your server with administrator permissions

### 2. Server Configuration
1. Add the token as environment variable `DISCORD_BOT_TOKEN`
2. Run `/setup` in the server to initialize
3. Configure roles with `/config roles`
4. Customize settings in `config.yml`

## Available Commands

### Moderation
- `/ban <user> [reason] [duration] [delete_messages]` - Ban a user
- `/unban <user> [reason]` - Remove ban
- `/kick <user> [reason]` - Kick user
- `/timeout <user> [duration] [reason]` - Temporarily mute
- `/untimeout <user> [reason]` - Remove mute
- `/warn <user> <reason>` - Warn user
- `/unwarn <user> [reason]` - Remove warning
- `/purge <amount> [user] [reason]` - Delete messages

### History and Logs
- `/history <user> [limit]` - Moderation history
- `/fullhistory <user>` - Complete paginated history
- `/warnings <user>` - Active warnings
- `/stafflogs [staff] [limit]` - Staff command logs
- `/automodlogs [user] [type] [limit]` - Auto-moderation logs

### Administration
- `/setup` - Configure bot for server
- `/config <setting> [action]` - Manage settings
- `/backup` - Backup database
- `/cleanup [days]` - Clean old data
- `/reload` - Reload configuration
- `/stats` - Bot statistics
- `/lock [channel] [reason]` - Lock channel
- `/unlock [channel] [reason]` - Unlock channel

### Utility
- `/help [command]` - Command guide

## Configuration

<details>
<summary><strong>📋 config.yml - Main Configuration</strong></summary>

```yaml
# Discord Moderation Bot Configuration

bot:
  prefix: "!"
  status: "over the server | /help"
  owners: [] # List of owner user IDs
  max_warnings: 3
  auto_punish_on_max_warnings: true

# Database settings
database:
  backup_interval: 24 # hours
  max_history_days: 365 # days to keep history

# Moderation settings
moderation:
  default_ban_delete_days: 1
  max_timeout_hours: 672 # 28 days maximum
  require_reason: true
  dm_on_punishment: true
  log_channel_name: "mod-logs"
  
  # Auto-moderation thresholds
  spam:
    enabled: true
    max_messages: 5
    time_window: 10 # seconds
    punishment: "timeout" # timeout, kick, ban
    duration: 600 # seconds for timeout
  
  caps:
    enabled: true
    threshold: 0.7 # 70% caps
    min_length: 10
    punishment: "warn"
  
  repeated_text:
    enabled: true
    threshold: 0.8 # 80% similarity
    punishment: "warn"
  
  bad_words:
    enabled: true
    punishment: "warn"
    words: 
      - "example_bad_word"
  
  invite_links:
    enabled: true
    punishment: "warn"
    whitelist: [] # Server IDs to allow invites for

# Logging settings
logging:
  enabled: true
  events:
    message_delete: true
    message_edit: true
    member_join: true
    member_leave: true
    member_ban: true
    member_unban: true
    role_create: true
    role_delete: true
    role_update: true
    channel_create: true
    channel_delete: true
    channel_update: true
    voice_state_update: true
    mod_actions: true

# Permission roles
permissions:
  admin_roles: [] # Role IDs with admin permissions
  moderator_roles: [] # Role IDs with moderator permissions
  helper_roles: [] # Role IDs with helper permissions
  
  # Command permissions
  commands:
    ban: ["admin", "moderator"]
    kick: ["admin", "moderator"]
    timeout: ["admin", "moderator", "helper"]
    warn: ["admin", "moderator", "helper"]
    history: ["admin", "moderator"]
    purge: ["admin", "moderator"]
    lock: ["admin", "moderator"]
    unlock: ["admin", "moderator"]

# Embed colors (hex values)
colors:
  success: 0x00ff00
  error: 0xff0000
  warning: 0xffff00
  info: 0x0099ff
  punishment: 0xff6600
  log: 0x36393e
```

</details>

<details>
<summary><strong>💬 messages.yml - Custom Messages</strong></summary>

```yaml
# Discord Moderation Bot Messages

# Welcome messages
welcome:
  description: "Thank you for adding me to your server! I'm here to help with moderation."
  getting_started: "Use `/setup` to configure me for your server. Use `/help` to see all available commands."

# Command responses
commands:
  # General
  success: "✅ Command executed successfully."
  error: "❌ An error occurred while executing the command."
  no_permission: "❌ You don't have permission to use this command."
  user_not_found: "❌ User not found."
  invalid_duration: "❌ Invalid duration format. Use examples: 1h, 30m, 1d"
  
  # Moderation
  ban:
    success: "🔨 **{user}** has been banned from the server."
    success_temp: "🔨 **{user}** has been temporarily banned for {duration}."
    dm: "You have been banned from **{guild}**.\nReason: {reason}"
    already_banned: "❌ User is already banned."
    cannot_ban_self: "❌ You cannot ban yourself."
    cannot_ban_bot: "❌ You cannot ban bots."
    higher_role: "❌ Cannot ban user with higher or equal role."
  
  unban:
    success: "✅ **{user}** has been unbanned."
    not_banned: "❌ User is not banned."
  
  kick:
    success: "👢 **{user}** has been kicked from the server."
    dm: "You have been kicked from **{guild}**.\nReason: {reason}"
    cannot_kick_self: "❌ You cannot kick yourself."
    higher_role: "❌ Cannot kick user with higher or equal role."
  
  timeout:
    success: "🔇 **{user}** has been timed out for {duration}."
    success_remove: "✅ Timeout removed for **{user}**."
    dm: "You have been timed out in **{guild}** for {duration}.\nReason: {reason}"
    already_timed_out: "❌ User is already timed out."
    not_timed_out: "❌ User is not timed out."
    max_duration: "❌ Maximum timeout duration is 28 days."
  
  warn:
    success: "⚠️ **{user}** has been warned. ({warnings}/{max_warnings})"
    dm: "You have been warned in **{guild}**.\nReason: {reason}\nWarnings: {warnings}/{max_warnings}"
    max_warnings: "⚠️ **{user}** has reached maximum warnings and will be automatically punished."
  
  unwarn:
    success: "✅ Warning removed from **{user}**."
    no_warnings: "❌ User has no warnings to remove."
  
  purge:
    success: "🗑️ Deleted {count} messages."
    no_messages: "❌ No messages found to delete."
    limit_exceeded: "❌ Cannot delete more than 100 messages at once."
  
  lock:
    success: "🔒 Channel has been locked."
    already_locked: "❌ Channel is already locked."
  
  unlock:
    success: "🔓 Channel has been unlocked."
    not_locked: "❌ Channel is not locked."

# History and logging
history:
  no_history: "No moderation history found for this user."
  user_info: "📋 **Moderation History for {user}**"
  total_actions: "Total Actions: {count}"
  
log:
  message_delete:
    title: "Message Deleted"
    author: "Author: {author}"
    channel: "Channel: {channel}"
    content: "Content: {content}"
  
  message_edit:
    title: "Message Edited"
    author: "Author: {author}"
    channel: "Channel: {channel}"
    before: "Before: {before}"
    after: "After: {after}"
  
  member_join:
    title: "Member Joined"
    user: "User: {user}"
    account_created: "Account Created: {created}"
  
  member_leave:
    title: "Member Left"
    user: "User: {user}"
    roles: "Roles: {roles}"
  
  member_ban:
    title: "Member Banned"
    user: "User: {user}"
    moderator: "Moderator: {moderator}"
    reason: "Reason: {reason}"
  
  member_unban:
    title: "Member Unbanned"
    user: "User: {user}"
    moderator: "Moderator: {moderator}"

# Auto-moderation
automod:
  spam:
    warning: "⚠️ **{user}**, please slow down your messages!"
    punishment: "🚫 **{user}** has been punished for spam."
  
  caps:
    warning: "⚠️ **{user}**, please don't use excessive caps!"
  
  bad_words:
    warning: "⚠️ **{user}**, please watch your language!"
  
  invite_links:
    warning: "⚠️ **{user}**, invite links are not allowed!"

# Setup and configuration
setup:
  success: "✅ Bot has been configured successfully!"
  log_channel_created: "📋 Created mod-logs channel for logging."
  roles_configured: "👥 Permission roles have been configured."
  
# Help command
help:
  title: "🛡️ Moderation Bot Commands"
  description: "Here are all available commands:"
  
  categories:
    moderation: "⚔️ Moderation"
    utility: "🔧 Utility"
    logging: "📋 Logging"
    admin: "👑 Admin"
  
  footer: "Use /help <command> for detailed information about a specific command."

# Error messages
errors:
  missing_permissions: "❌ I don't have the required permissions to perform this action."
  bot_missing_permissions: "❌ I need the following permissions: {permissions}"
  command_on_cooldown: "⏰ This command is on cooldown. Try again in {time} seconds."
  user_on_cooldown: "⏰ You're using commands too quickly. Please wait {time} seconds."
  database_error: "❌ A database error occurred. Please try again later."
  invalid_user: "❌ Please provide a valid user."
  invalid_channel: "❌ Please provide a valid channel."
  invalid_role: "❌ Please provide a valid role."
  reason_required: "❌ A reason is required for this action."
  dm_failed: "⚠️ Could not send DM to user."

# Success messages
success:
  database_backup: "✅ Database backup completed successfully."
  configuration_saved: "✅ Configuration saved successfully."
  permissions_updated: "✅ Permissions updated successfully."
```

</details>

## Database Structure

The bot uses SQLite with the following tables:
- `warnings` - User warnings
- `mod_history` - Moderation history
- `guild_settings` - Server settings
- `message_logs` - Message logs
- `staff_logs` - Staff command logs
- `temp_actions` - Temporary actions
- `automod_violations` - Auto-mod violations

## Auto-Moderation

### Spam Configuration
```yaml
spam:
  enabled: true
  max_messages: 5
  time_window: 10
  punishment: "timeout"
  duration: 600
```

### Caps Configuration
```yaml
caps:
  enabled: true
  threshold: 0.7
  min_length: 10
  punishment: "warn"
```

### Word Filter
```yaml
bad_words:
  enabled: true
  punishment: "warn"
  words: 
    - "example_word"
```

## Event Logging

The bot automatically logs:
- **Messages** - Deletions and edits
- **Members** - Join, leave, ban, unban
- **Roles** - Creation, deletion, modifications
- **Channels** - Creation, deletion, modifications
- **Voice** - Voice channel entries/exits
- **Moderation** - All staff actions

## Required Permissions

The bot needs the following Discord permissions:
- Manage Messages
- Manage Roles
- Manage Channels
- Ban Members
- Kick Members
- Moderate Members (Timeout)
- Read Message History
- Send Messages
- Embed Links
- Use Slash Commands

## Security

- **Hierarchy Control** - Prevents actions on higher roles
- **Complete Logging** - Traceability of all actions
- **Automatic Backups** - Data loss protection
- **Granular Permissions** - Precise access control
- **Rate Limiting** - Command spam protection

## Support and Maintenance

- **Database Backup** - `/backup` for data security
- **Automatic Cleanup** - `/cleanup` for space management
- **Config Reload** - `/reload` for live updates
- **Statistics** - `/stats` for usage monitoring
- **Detailed Logs** - `bot.log` file for debugging

## Main Files

- `main.py` - Entry point and bot configuration
- `config.yml` - Main configuration
- `messages.yml` - Custom messages
- `cogs/` - Feature modules
- `utils/` - Utilities and helpers
- `database.db` - SQLite database

## License

DiscordModeretionBot is licensed under the **GNU General Public License v3.0** (GPL-3.0).  
You are free to use, modify, and distribute this software under the terms of the license.  
A copy of the license is available in the [LICENSE](./LICENSE) file.

## Credits

**Developer:** [Fl1uxxNoob](https://github.com/Fl1uxxNoob)

---