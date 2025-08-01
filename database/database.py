"""
Database module for the Telegram moderation bot.
Handles SQLite database operations and schema management.
"""
import aiosqlite
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

async def init_db():
    """Initialize the database and create tables if they don't exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")
        
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                experience INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                last_xp_time INTEGER DEFAULT 0,
                xp_multiplier REAL DEFAULT 1.0,
                art_points INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT FALSE,
                is_moderator BOOLEAN DEFAULT FALSE,
                is_art_leader BOOLEAN DEFAULT FALSE,
                can_use_stickers BOOLEAN DEFAULT FALSE,
                join_date INTEGER DEFAULT (strftime('%s', 'now')),
                last_seen INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        # Warnings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                warning_date INTEGER DEFAULT (strftime('%s', 'now')),
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (moderator_id) REFERENCES users (user_id)
            )
        """)
        
        # Mutes table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                mute_date INTEGER DEFAULT (strftime('%s', 'now')),
                unmute_date INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (moderator_id) REFERENCES users (user_id)
            )
        """)
        
        # Bans table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                ban_date INTEGER DEFAULT (strftime('%s', 'now')),
                unban_date INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (moderator_id) REFERENCES users (user_id)
            )
        """)
        
        # Tickets table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                create_date INTEGER DEFAULT (strftime('%s', 'now')),
                close_date INTEGER,
                assigned_moderator INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (assigned_moderator) REFERENCES users (user_id)
            )
        """)
        
        # Ticket messages table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                send_date INTEGER DEFAULT (strftime('%s', 'now')),
                is_moderator_message BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Bad words table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS badwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE NOT NULL,
                added_by INTEGER NOT NULL,
                add_date INTEGER DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (added_by) REFERENCES users (user_id)
            )
        """)
        
        # Custom roles table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role_name TEXT NOT NULL,
                assigned_by INTEGER NOT NULL,
                assign_date INTEGER DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (assigned_by) REFERENCES users (user_id)
            )
        """)
        
        # Message statistics table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message_date DATE DEFAULT (date('now')),
                message_count INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, message_date)
            )
        """)
        
        # Create indexes for better performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_level ON users(level)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_experience ON users(experience)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_warnings_user_id ON warnings(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_warnings_active ON warnings(is_active)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_mutes_user_id ON mutes(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_mutes_active ON mutes(is_active)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bans_user_id ON bans(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bans_active ON bans(is_active)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_badwords_word ON badwords(word)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_message_stats_user_date ON message_stats(user_id, message_date)")
        
        await db.commit()
        logger.info("Database initialized successfully")

class Database:
    """Database helper class for common operations."""
    
    @staticmethod
    async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    @staticmethod
    async def create_or_update_user(user_id: int, username: str = None, 
                                   first_name: str = None, last_name: str = None) -> None:
        """Create a new user or update existing user info."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, last_seen)
                VALUES (?, ?, ?, ?, strftime('%s', 'now'))
            """, (user_id, username, first_name, last_name))
            await db.commit()
    
    @staticmethod
    async def update_user_experience(user_id: int, experience: int, level: int) -> None:
        """Update user experience and level."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                UPDATE users SET experience = ?, level = ?, last_xp_time = strftime('%s', 'now')
                WHERE user_id = ?
            """, (experience, level, user_id))
            await db.commit()
    
    @staticmethod
    async def get_top_users(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get top users by experience."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT user_id, username, first_name, experience, level
                FROM users
                ORDER BY experience DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    @staticmethod
    async def add_warning(user_id: int, moderator_id: int, reason: str = None) -> int:
        """Add a warning to user. Returns warning ID."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO warnings (user_id, moderator_id, reason)
                VALUES (?, ?, ?)
            """, (user_id, moderator_id, reason))
            await db.commit()
            return cursor.lastrowid
    
    @staticmethod
    async def get_active_warnings(user_id: int) -> List[Dict[str, Any]]:
        """Get active warnings for user."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM warnings
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY warning_date DESC
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    @staticmethod
    async def remove_warning(warning_id: int) -> bool:
        """Remove a warning by ID."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                UPDATE warnings SET is_active = FALSE
                WHERE id = ?
            """, (warning_id,))
            await db.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    async def clear_user_warnings(user_id: int) -> int:
        """Clear all warnings for a user. Returns number of warnings cleared."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                UPDATE warnings SET is_active = FALSE
                WHERE user_id = ? AND is_active = TRUE
            """, (user_id,))
            await db.commit()
            return cursor.rowcount
    
    @staticmethod
    async def add_mute(user_id: int, moderator_id: int, unmute_date: int, reason: str = None) -> int:
        """Add a mute to user. Returns mute ID."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO mutes (user_id, moderator_id, unmute_date, reason)
                VALUES (?, ?, ?, ?)
            """, (user_id, moderator_id, unmute_date, reason))
            await db.commit()
            return cursor.lastrowid
    
    @staticmethod
    async def remove_mute(user_id: int) -> bool:
        """Remove active mute for user."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                UPDATE mutes SET is_active = FALSE
                WHERE user_id = ? AND is_active = TRUE
            """, (user_id,))
            await db.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    async def is_user_muted(user_id: int) -> bool:
        """Check if user is currently muted."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM mutes
                WHERE user_id = ? AND is_active = TRUE
                AND (unmute_date IS NULL OR unmute_date > strftime('%s', 'now'))
            """, (user_id,)) as cursor:
                count = await cursor.fetchone()
                return count[0] > 0
    
    @staticmethod
    async def add_ban(user_id: int, moderator_id: int, unban_date: int = None, reason: str = None) -> int:
        """Add a ban to user. Returns ban ID."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO bans (user_id, moderator_id, unban_date, reason)
                VALUES (?, ?, ?, ?)
            """, (user_id, moderator_id, unban_date, reason))
            await db.commit()
            return cursor.lastrowid
    
    @staticmethod
    async def remove_ban(user_id: int) -> bool:
        """Remove active ban for user."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                UPDATE bans SET is_active = FALSE
                WHERE user_id = ? AND is_active = TRUE
            """, (user_id,))
            await db.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    async def is_user_banned(user_id: int) -> bool:
        """Check if user is currently banned."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM bans
                WHERE user_id = ? AND is_active = TRUE
                AND (unban_date IS NULL OR unban_date > strftime('%s', 'now'))
            """, (user_id,)) as cursor:
                count = await cursor.fetchone()
                return count[0] > 0
    
    @staticmethod
    async def create_ticket(user_id: int, subject: str, message: str) -> int:
        """Create a new ticket. Returns ticket ID."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO tickets (user_id, subject, message)
                VALUES (?, ?, ?)
            """, (user_id, subject, message))
            await db.commit()
            return cursor.lastrowid
    
    @staticmethod
    async def get_ticket(ticket_id: int) -> Optional[Dict[str, Any]]:
        """Get ticket by ID."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    @staticmethod
    async def add_badword(word: str, added_by: int) -> bool:
        """Add a bad word. Returns True if added, False if already exists."""
        try:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute("""
                    INSERT INTO badwords (word, added_by)
                    VALUES (?, ?)
                """, (word.lower(), added_by))
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False
    
    @staticmethod
    async def remove_badword(word: str) -> bool:
        """Remove a bad word."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("DELETE FROM badwords WHERE word = ?", (word.lower(),))
            await db.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    async def get_badwords() -> List[str]:
        """Get all bad words."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT word FROM badwords ORDER BY word") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    
    @staticmethod
    async def update_message_stats(user_id: int) -> None:
        """Update daily message statistics for user."""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO message_stats (user_id, message_count)
                VALUES (?, 1)
                ON CONFLICT(user_id, message_date)
                DO UPDATE SET message_count = message_count + 1
            """, (user_id,))
            await db.commit()