import aiosqlite
import logging
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from .models import User, Punishment, Ticket, BadWord, UserRole, UserRight, PunishmentType

logger = logging.getLogger(__name__)

class Database:
    """Database manager for the bot"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def init_db(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    experience INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    messages_count INTEGER DEFAULT 0,
                    art_points INTEGER DEFAULT 0,
                    rights TEXT DEFAULT 'user',
                    custom_role TEXT,
                    custom_title TEXT,
                    last_xp_time TIMESTAMP,
                    xp_multiplier REAL DEFAULT 1.0,
                    is_blocked_tickets BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Punishments table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS punishments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    punishment_type TEXT NOT NULL,
                    reason TEXT,
                    duration_minutes INTEGER,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (moderator_id) REFERENCES users (user_id)
                )
            """)
            
            # Tickets table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    admin_message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Bad words table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bad_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL UNIQUE,
                    added_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (added_by) REFERENCES users (user_id)
                )
            """)
            
            # User roles table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role_name TEXT NOT NULL,
                    assigned_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (assigned_by) REFERENCES users (user_id)
                )
            """)
            
            await db.commit()
            logger.info("Database initialized successfully")
    
    async def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> User:
        """Get existing user or create new one"""
        async with aiosqlite.connect(self.db_path) as db:
            # Try to get existing user
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return User(
                    user_id=row[0],
                    username=row[1],
                    first_name=row[2],
                    last_name=row[3],
                    experience=row[4],
                    level=row[5],
                    messages_count=row[6],
                    art_points=row[7],
                    rights=UserRight(row[8]),
                    custom_role=row[9],
                    custom_title=row[10],
                    last_xp_time=datetime.fromisoformat(row[11]) if row[11] else None,
                    xp_multiplier=row[12],
                    is_blocked_tickets=bool(row[13]),
                    created_at=datetime.fromisoformat(row[14]) if row[14] else None,
                    updated_at=datetime.fromisoformat(row[15]) if row[15] else None
                )
            else:
                # Create new user
                await db.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                """, (user_id, username, first_name, last_name))
                await db.commit()
                
                return User(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
    
    async def update_user(self, user: User):
        """Update user in database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET
                    username = ?, first_name = ?, last_name = ?, experience = ?,
                    level = ?, messages_count = ?, art_points = ?, rights = ?,
                    custom_role = ?, custom_title = ?, last_xp_time = ?,
                    xp_multiplier = ?, is_blocked_tickets = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (
                user.username, user.first_name, user.last_name, user.experience,
                user.level, user.messages_count, user.art_points, user.rights.value,
                user.custom_role, user.custom_title,
                user.last_xp_time.isoformat() if user.last_xp_time else None,
                user.xp_multiplier, user.is_blocked_tickets, user.user_id
            ))
            await db.commit()
    
    async def add_punishment(self, punishment: Punishment) -> int:
        """Add punishment to database"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO punishments (user_id, moderator_id, punishment_type, reason, duration_minutes, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                punishment.user_id, punishment.moderator_id, punishment.punishment_type.value,
                punishment.reason, punishment.duration_minutes,
                punishment.expires_at.isoformat() if punishment.expires_at else None
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_active_punishments(self, user_id: int, punishment_type: PunishmentType = None) -> List[Punishment]:
        """Get active punishments for user"""
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT * FROM punishments WHERE user_id = ? AND is_active = TRUE"
            params = [user_id]
            
            if punishment_type:
                query += " AND punishment_type = ?"
                params.append(punishment_type.value)
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            punishments = []
            for row in rows:
                punishments.append(Punishment(
                    id=row[0],
                    user_id=row[1],
                    moderator_id=row[2],
                    punishment_type=PunishmentType(row[3]),
                    reason=row[4],
                    duration_minutes=row[5],
                    expires_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    is_active=bool(row[7]),
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None
                ))
            
            return punishments
    
    async def remove_punishment(self, user_id: int, punishment_type: PunishmentType):
        """Remove active punishment"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE punishments SET is_active = FALSE
                WHERE user_id = ? AND punishment_type = ? AND is_active = TRUE
            """, (user_id, punishment_type.value))
            await db.commit()
    
    async def create_ticket(self, ticket: Ticket) -> int:
        """Create new ticket"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO tickets (user_id, message)
                VALUES (?, ?)
            """, (ticket.user_id, ticket.message))
            await db.commit()
            return cursor.lastrowid
    
    async def update_ticket(self, ticket_id: int, status: str = None, admin_message_id: int = None):
        """Update ticket"""
        async with aiosqlite.connect(self.db_path) as db:
            if status:
                await db.execute("""
                    UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, ticket_id))
            
            if admin_message_id:
                await db.execute("""
                    UPDATE tickets SET admin_message_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (admin_message_id, ticket_id))
            
            await db.commit()
    
    async def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        """Get ticket by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
            row = await cursor.fetchone()
            
            if row:
                return Ticket(
                    id=row[0],
                    user_id=row[1],
                    message=row[2],
                    status=row[3],
                    admin_message_id=row[4],
                    created_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    updated_at=datetime.fromisoformat(row[6]) if row[6] else None
                )
            return None
    
    async def add_bad_word(self, word: str, added_by: int) -> bool:
        """Add bad word to database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO bad_words (word, added_by)
                    VALUES (?, ?)
                """, (word.lower(), added_by))
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False  # Word already exists
    
    async def remove_bad_word(self, word: str) -> bool:
        """Remove bad word from database"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM bad_words WHERE word = ?
            """, (word.lower(),))
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_bad_words(self) -> List[str]:
        """Get all bad words"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT word FROM bad_words")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def get_top_users(self, limit: int = 10, offset: int = 0) -> List[User]:
        """Get top users by experience"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM users ORDER BY experience DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = await cursor.fetchall()
            
            users = []
            for row in rows:
                users.append(User(
                    user_id=row[0],
                    username=row[1],
                    first_name=row[2],
                    last_name=row[3],
                    experience=row[4],
                    level=row[5],
                    messages_count=row[6],
                    art_points=row[7],
                    rights=UserRight(row[8]),
                    custom_role=row[9],
                    custom_title=row[10],
                    last_xp_time=datetime.fromisoformat(row[11]) if row[11] else None,
                    xp_multiplier=row[12],
                    is_blocked_tickets=bool(row[13]),
                    created_at=datetime.fromisoformat(row[14]) if row[14] else None,
                    updated_at=datetime.fromisoformat(row[15]) if row[15] else None
                ))
            
            return users
    
    async def get_user_rank(self, user_id: int) -> Optional[int]:
        """Get user's rank by experience"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) + 1 as rank FROM users
                WHERE experience > (SELECT experience FROM users WHERE user_id = ?)
            """, (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else None