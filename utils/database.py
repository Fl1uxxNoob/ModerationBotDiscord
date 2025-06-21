import sqlite3
import aiosqlite
import logging
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
    
    async def initialize(self):
        """Initialize the database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # User warnings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT 1
                )
            """)
            
            # Moderation history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mod_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    reason TEXT,
                    duration INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    additional_data TEXT
                )
            """)
            
            # Guild settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    settings TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Message logs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS message_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    content TEXT,
                    action_type TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    additional_data TEXT
                )
            """)
            
            # Staff activity logs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS staff_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    staff_id INTEGER NOT NULL,
                    command TEXT NOT NULL,
                    target_id INTEGER,
                    channel_id INTEGER,
                    arguments TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT 1
                )
            """)
            
            # Temporary actions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS temp_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    expires_at DATETIME NOT NULL,
                    completed BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Auto-mod violations table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod_violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    violation_type TEXT NOT NULL,
                    content TEXT,
                    channel_id INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    action_taken TEXT
                )
            """)
            
            await db.commit()
            logger.info("Database initialized successfully")
    
    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        """Add a warning to a user"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, moderator_id, reason)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def remove_warning(self, guild_id: int, user_id: int) -> bool:
        """Remove the most recent active warning from a user"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM warnings WHERE guild_id = ? AND user_id = ? AND active = 1 ORDER BY timestamp DESC LIMIT 1",
                (guild_id, user_id)
            )
            row = await cursor.fetchone()
            
            if row:
                await db.execute(
                    "UPDATE warnings SET active = 0 WHERE id = ?",
                    (row[0],)
                )
                await db.commit()
                return True
            return False
    
    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict]:
        """Get all active warnings for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? AND active = 1 ORDER BY timestamp DESC",
                (guild_id, user_id)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_warning_count(self, guild_id: int, user_id: int) -> int:
        """Get the count of active warnings for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ? AND active = 1",
                (guild_id, user_id)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def log_mod_action(self, guild_id: int, user_id: int, moderator_id: int, 
                           action_type: str, reason: str = None, duration: int = None, 
                           additional_data: Dict = None):
        """Log a moderation action"""
        async with aiosqlite.connect(self.db_path) as db:
            additional_json = json.dumps(additional_data) if additional_data else None
            await db.execute(
                """INSERT INTO mod_history 
                   (guild_id, user_id, moderator_id, action_type, reason, duration, additional_data) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (guild_id, user_id, moderator_id, action_type, reason, duration, additional_json)
            )
            await db.commit()
    
    async def get_user_history(self, guild_id: int, user_id: int, limit: int = 50) -> List[Dict]:
        """Get moderation history for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM mod_history 
                   WHERE guild_id = ? AND user_id = ? 
                   ORDER BY timestamp DESC LIMIT ?""",
                (guild_id, user_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def log_staff_action(self, guild_id: int, staff_id: int, command: str, 
                             target_id: int = None, channel_id: int = None, 
                             arguments: str = None, success: bool = True):
        """Log a staff command usage"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO staff_logs 
                   (guild_id, staff_id, command, target_id, channel_id, arguments, success) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (guild_id, staff_id, command, target_id, channel_id, arguments, success)
            )
            await db.commit()
    
    async def get_staff_logs(self, guild_id: int, staff_id: int = None, limit: int = 100) -> List[Dict]:
        """Get staff command logs"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if staff_id:
                cursor = await db.execute(
                    """SELECT * FROM staff_logs 
                       WHERE guild_id = ? AND staff_id = ? 
                       ORDER BY timestamp DESC LIMIT ?""",
                    (guild_id, staff_id, limit)
                )
            else:
                cursor = await db.execute(
                    """SELECT * FROM staff_logs 
                       WHERE guild_id = ? 
                       ORDER BY timestamp DESC LIMIT ?""",
                    (guild_id, limit)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def log_message_action(self, guild_id: int, channel_id: int, message_id: int, 
                               user_id: int, action_type: str, content: str = None, 
                               additional_data: Dict = None):
        """Log a message-related action"""
        async with aiosqlite.connect(self.db_path) as db:
            additional_json = json.dumps(additional_data) if additional_data else None
            await db.execute(
                """INSERT INTO message_logs 
                   (guild_id, channel_id, message_id, user_id, content, action_type, additional_data) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (guild_id, channel_id, message_id, user_id, content, action_type, additional_json)
            )
            await db.commit()
    
    async def add_temp_action(self, guild_id: int, user_id: int, action_type: str, 
                            expires_at: datetime) -> int:
        """Add a temporary action"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO temp_actions (guild_id, user_id, action_type, expires_at) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, action_type, expires_at)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def get_expired_temp_actions(self) -> List[Dict]:
        """Get all expired temporary actions that haven't been completed"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM temp_actions WHERE expires_at <= ? AND completed = 0",
                (datetime.now(),)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def complete_temp_action(self, action_id: int):
        """Mark a temporary action as completed"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE temp_actions SET completed = 1 WHERE id = ?",
                (action_id,)
            )
            await db.commit()
    
    async def log_automod_violation(self, guild_id: int, user_id: int, violation_type: str, 
                                  content: str, channel_id: int, action_taken: str = None):
        """Log an auto-moderation violation"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO automod_violations 
                   (guild_id, user_id, violation_type, content, channel_id, action_taken) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (guild_id, user_id, violation_type, content, channel_id, action_taken)
            )
            await db.commit()
    
    async def get_automod_violations(self, guild_id: int, user_id: int = None, 
                                   violation_type: str = None, limit: int = 50) -> List[Dict]:
        """Get auto-moderation violations"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = "SELECT * FROM automod_violations WHERE guild_id = ?"
            params = [guild_id]
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if violation_type:
                query += " AND violation_type = ?"
                params.append(violation_type)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def setup_guild(self, guild_id: int, settings: Dict = None):
        """Setup a guild in the database"""
        if settings is None:
            settings = {}
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO guild_settings (guild_id, settings, updated_at) 
                   VALUES (?, ?, ?)""",
                (guild_id, json.dumps(settings), datetime.now())
            )
            await db.commit()
    
    async def get_guild_settings(self, guild_id: int) -> Dict:
        """Get guild settings"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT settings FROM guild_settings WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
            return {}
    
    async def update_guild_settings(self, guild_id: int, settings: Dict):
        """Update guild settings"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO guild_settings (guild_id, settings, updated_at) 
                   VALUES (?, ?, ?)""",
                (guild_id, json.dumps(settings), datetime.now())
            )
            await db.commit()
    
    async def cleanup_old_data(self, days: int = 365):
        """Clean up old data from the database"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Clean old message logs
            await db.execute(
                "DELETE FROM message_logs WHERE timestamp < ?",
                (cutoff_date,)
            )
            
            # Clean old completed temp actions
            await db.execute(
                "DELETE FROM temp_actions WHERE completed = 1 AND created_at < ?",
                (cutoff_date,)
            )
            
            # Clean old automod violations
            await db.execute(
                "DELETE FROM automod_violations WHERE timestamp < ?",
                (cutoff_date,)
            )
            
            await db.commit()
            logger.info(f"Cleaned up data older than {days} days")
    
    async def backup_database(self, backup_path: str = None):
        """Create a backup of the database"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"database_backup_{timestamp}.db"
        
        async with aiosqlite.connect(self.db_path) as source:
            async with aiosqlite.connect(backup_path) as backup:
                await source.backup(backup)
        
        logger.info(f"Database backed up to {backup_path}")
        return backup_path
