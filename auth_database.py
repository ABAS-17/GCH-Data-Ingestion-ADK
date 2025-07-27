"""
SQLite database manager for user authentication
"""

import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import aiosqlite
import asyncio
import os

logger = logging.getLogger(__name__)

class AuthDatabase:
    def __init__(self, db_path: str = "auth.db"):
        self.db_path = db_path
        self.initialized = False
    
    async def initialize(self):
        """Initialize the authentication database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Create users table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT UNIQUE NOT NULL,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # Create auth_tokens table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS auth_tokens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        token TEXT UNIQUE NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Create indexes for better performance
                await db.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_tokens_token ON auth_tokens(token)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_tokens_user_id ON auth_tokens(user_id)')
                
                await db.commit()
                
            self.initialized = True
            logger.info("✅ Authentication database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize auth database: {e}")
            return False
    
    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000  # iterations
        )
        return password_hash.hex(), salt
    
    def _verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        password_hash, _ = self._hash_password(password, salt)
        return password_hash == stored_hash
    
    def _generate_token(self) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(32)
    
    async def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        try:
            if not self.initialized:
                await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                # Check if user already exists
                async with db.execute(
                    'SELECT id FROM users WHERE email = ? OR username = ?', 
                    (email, username)
                ) as cursor:
                    existing = await cursor.fetchone()
                    if existing:
                        return {
                            "success": False,
                            "message": "User with this email or username already exists"
                        }
                
                # Generate user ID and hash password
                user_id = secrets.token_urlsafe(16)
                password_hash, salt = self._hash_password(password)
                
                # Insert new user
                await db.execute('''
                    INSERT INTO users (user_id, username, email, password_hash, salt)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, username, email, password_hash, salt))
                
                await db.commit()
                
                logger.info(f"✅ User registered successfully: {username} ({email})")
                return {
                    "success": True,
                    "message": "User registered successfully",
                    "user_id": user_id,
                    "username": username,
                    "email": email
                }
                
        except Exception as e:
            logger.error(f"❌ Error registering user: {e}")
            return {
                "success": False,
                "message": f"Registration failed: {str(e)}"
            }
    
    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login user and generate auth token"""
        try:
            if not self.initialized:
                await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                # Get user by email
                async with db.execute('''
                    SELECT user_id, username, email, password_hash, salt, is_active
                    FROM users WHERE email = ?
                ''', (email,)) as cursor:
                    user = await cursor.fetchone()
                    
                    if not user:
                        return {
                            "success": False,
                            "message": "Invalid email or password"
                        }
                
                user_id, username, email, stored_hash, salt, is_active = user
                
                if not is_active:
                    return {
                        "success": False,
                        "message": "Account is deactivated"
                    }
                
                # Verify password
                if not self._verify_password(password, stored_hash, salt):
                    return {
                        "success": False,
                        "message": "Invalid email or password"
                    }
                
                # Generate auth token
                token = self._generate_token()
                expires_at = datetime.utcnow() + timedelta(days=7)  # Token valid for 7 days
                
                # Clean up old tokens for this user
                await db.execute('DELETE FROM auth_tokens WHERE user_id = ?', (user_id,))
                
                # Store new token
                await db.execute('''
                    INSERT INTO auth_tokens (user_id, token, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, token, expires_at))
                
                # Update last login
                await db.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?
                ''', (user_id,))
                
                await db.commit()
                
                logger.info(f"✅ User logged in successfully: {username}")
                return {
                    "success": True,
                    "message": "Login successful",
                    "user_id": user_id,
                    "username": username,
                    "email": email,
                    "token": token,
                    "expires_at": expires_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Error during login: {e}")
            return {
                "success": False,
                "message": f"Login failed: {str(e)}"
            }
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify authentication token"""
        try:
            if not self.initialized:
                await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT u.user_id, u.username, u.email, t.expires_at
                    FROM users u
                    JOIN auth_tokens t ON u.user_id = t.user_id
                    WHERE t.token = ? AND u.is_active = 1
                ''', (token,)) as cursor:
                    result = await cursor.fetchone()
                    
                    if not result:
                        return {
                            "success": False,
                            "message": "Invalid token"
                        }
                
                user_id, username, email, expires_at = result
                
                # Check if token is expired
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expires_datetime < datetime.utcnow():
                    # Clean up expired token
                    await db.execute('DELETE FROM auth_tokens WHERE token = ?', (token,))
                    await db.commit()
                    
                    return {
                        "success": False,
                        "message": "Token expired"
                    }
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "username": username,
                    "email": email
                }
                
        except Exception as e:
            logger.error(f"❌ Error verifying token: {e}")
            return {
                "success": False,
                "message": f"Token verification failed: {str(e)}"
            }
    
    async def logout_user(self, token: str) -> Dict[str, Any]:
        """Logout user by invalidating token"""
        try:
            if not self.initialized:
                await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                # Remove the token
                await db.execute('DELETE FROM auth_tokens WHERE token = ?', (token,))
                await db.commit()
                
                return {
                    "success": True,
                    "message": "Logged out successfully"
                }
                
        except Exception as e:
            logger.error(f"❌ Error during logout: {e}")
            return {
                "success": False,
                "message": f"Logout failed: {str(e)}"
            }
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            if not self.initialized:
                await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                # Total users
                async with db.execute('SELECT COUNT(*) FROM users') as cursor:
                    total_users = (await cursor.fetchone())[0]
                
                # Active users
                async with db.execute('SELECT COUNT(*) FROM users WHERE is_active = 1') as cursor:
                    active_users = (await cursor.fetchone())[0]
                
                # Users registered today
                async with db.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE date(created_at) = date('now')
                ''') as cursor:
                    users_today = (await cursor.fetchone())[0]
                
                # Active sessions
                async with db.execute('''
                    SELECT COUNT(*) FROM auth_tokens 
                    WHERE expires_at > datetime('now')
                ''') as cursor:
                    active_sessions = (await cursor.fetchone())[0]
                
                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "users_registered_today": users_today,
                    "active_sessions": active_sessions
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting user stats: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "users_registered_today": 0,
                "active_sessions": 0
            }
    
    async def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        try:
            if not self.initialized:
                await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    DELETE FROM auth_tokens WHERE expires_at < datetime('now')
                ''')
                await db.commit()
                
            logger.info("🧹 Cleaned up expired tokens")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up tokens: {e}")

# Global instance
auth_db = AuthDatabase()