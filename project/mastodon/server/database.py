"""
Database Connection Module for Mastodon Server

This module provides database connection and operations for the Mastodon server.
It handles connecting to CockroachDB and provides functions for common database operations.
"""

import psycopg2
from psycopg2.extras import DictCursor
from typing import Dict, List, Optional, Any, Tuple
import uuid
from datetime import datetime
import hashlib

# Connection string for CockroachDB
CONNECTION_STRING = "postgresql://root@localhost:26257/defaultdb?sslmode=disable"

class Database:
    """Database connection and operations handler."""
    
    def __init__(self):
        """Initialize database connection."""
        self.conn = None
        self.connect()
    
    def connect(self):
        """Connect to the database."""
        try:
            self.conn = psycopg2.connect(CONNECTION_STRING)
            self.conn.autocommit = True
        except Exception as e:
            print(f"Database connection error: {e}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a query and return results as dictionaries."""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, params)
                if cur.description:
                    return [dict(row) for row in cur.fetchall()]
                return []
        except Exception as e:
            print(f"Query execution error: {e}")
            self.connect()  # Try to reconnect
            raise
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute a query with multiple parameter sets."""
        try:
            with self.conn.cursor() as cur:
                cur.executemany(query, params_list)
        except Exception as e:
            print(f"Batch execution error: {e}")
            self.connect()  # Try to reconnect
            raise
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    # User operations
    def create_user(self, username: str, password: str, display_name: str = None, 
                   bio: str = None, avatar_url: str = None, header_url: str = None) -> Dict:
        """Create a new user."""
        password_hash = self._hash_password(password)
        query = """
            INSERT INTO users (username, password_hash, display_name, bio, avatar_url, header_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *;
        """
        result = self.execute(query, (username, password_hash, display_name, bio, avatar_url, header_url))
        return result[0] if result else None
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """Verify user credentials and return user data if valid."""
        password_hash = self._hash_password(password)
        query = """
            SELECT * FROM users 
            WHERE username = %s AND password_hash = %s;
        """
        result = self.execute(query, (username, password_hash))
        return result[0] if result else None
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username."""
        query = "SELECT * FROM users WHERE username = %s;"
        result = self.execute(query, (username,))
        return result[0] if result else None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get a user by ID."""
        query = "SELECT * FROM users WHERE id = %s"
        result = self.execute(query, (user_id,))
        return result[0] if result else None
    
    # Status operations
    def create_status(self, user_id: str, content: str, visibility: str = 'public',
                     sensitive: bool = False, spoiler_text: str = None,
                     latitude: float = None, longitude: float = None) -> Dict:
        """Create a new status."""
        query = """
            INSERT INTO statuses (user_id, content, visibility, sensitive, spoiler_text, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        result = self.execute(query, (user_id, content, visibility, sensitive, spoiler_text, latitude, longitude))
        return result[0] if result else None
    
    def get_status(self, status_id: str) -> Optional[Dict]:
        """Get a status by ID."""
        query = "SELECT * FROM statuses WHERE id = %s"
        result = self.execute(query, (status_id,))
        return result[0] if result else None
    
    def get_user_statuses(self, user_id: str, limit: int = 20, 
                         since_id: str = None, max_id: str = None) -> List[Dict]:
        """Get statuses for a user with pagination."""
        query = "SELECT * FROM statuses WHERE user_id = %s"
        params = [user_id]
        
        if since_id:
            query += " AND id > %s"
            params.append(since_id)
        
        if max_id:
            query += " AND id < %s"
            params.append(max_id)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        return self.execute(query, tuple(params))
    
    def get_public_timeline(self, limit: int = 20, 
                           since_id: str = None, max_id: str = None) -> List[Dict]:
        """Get public timeline with pagination."""
        query = "SELECT * FROM statuses WHERE visibility = 'public'"
        params = []
        
        if since_id:
            query += " AND id > %s"
            params.append(since_id)
        
        if max_id:
            query += " AND id < %s"
            params.append(max_id)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        return self.execute(query, tuple(params))
    
    # Media operations
    def create_media_attachment(self, status_id: str, file_path: str, 
                               file_type: str, description: str = None, 
                               url: str = None) -> Dict:
        """Create a new media attachment."""
        if url is None:
            url = file_path
            
        query = """
            INSERT INTO media_attachments (status_id, file_path, file_type, description, url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """
        result = self.execute(query, (status_id, file_path, file_type, description, url))
        return result[0] if result else None
    
    def get_status_media(self, status_id: str) -> List[Dict]:
        """Get all media attachments for a status."""
        query = "SELECT * FROM media_attachments WHERE status_id = %s"
        return self.execute(query, (status_id,))
    
    # Hashtag operations
    def create_hashtag(self, name: str) -> Dict:
        """Create a new hashtag."""
        query = """
            INSERT INTO hashtags (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
            RETURNING *
        """
        result = self.execute(query, (name,))
        return result[0] if result else None
    
    def get_hashtag(self, name: str) -> Optional[Dict]:
        """Get a hashtag by name."""
        query = "SELECT * FROM hashtags WHERE name = %s"
        result = self.execute(query, (name,))
        return result[0] if result else None
    
    def link_status_to_hashtag(self, status_id: str, hashtag_id: str) -> None:
        """Link a status to a hashtag."""
        query = """
            INSERT INTO status_hashtags (status_id, hashtag_id)
            VALUES (%s, %s)
            ON CONFLICT (status_id, hashtag_id) DO NOTHING
        """
        self.execute(query, (status_id, hashtag_id))
    
    def get_hashtag_timeline(self, hashtag_name: str, limit: int = 20,
                            since_id: str = None, max_id: str = None) -> List[Dict]:
        """Get timeline for a hashtag with pagination."""
        query = """
            SELECT s.* FROM statuses s
            JOIN status_hashtags sh ON s.id = sh.status_id
            JOIN hashtags h ON sh.hashtag_id = h.id
            WHERE h.name = %s
        """
        params = [hashtag_name]
        
        if since_id:
            query += " AND s.id > %s"
            params.append(since_id)
        
        if max_id:
            query += " AND s.id < %s"
            params.append(max_id)
        
        query += " ORDER BY s.created_at DESC LIMIT %s"
        params.append(limit)
        
        return self.execute(query, tuple(params))
    
    # Relationship operations
    def create_relationship(self, follower_id: str, following_id: str, 
                          relationship_type: str) -> Dict:
        """Create a relationship between users."""
        query = """
            INSERT INTO relationships (follower_id, following_id, relationship_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (follower_id, following_id, relationship_type) DO NOTHING
            RETURNING *
        """
        result = self.execute(query, (follower_id, following_id, relationship_type))
        return result[0] if result else None
    
    def get_followers(self, user_id: str) -> List[Dict]:
        """Get all followers of a user."""
        query = """
            SELECT u.* FROM users u
            JOIN relationships r ON u.id = r.follower_id
            WHERE r.following_id = %s AND r.relationship_type = 'follow'
        """
        return self.execute(query, (user_id,))
    
    def get_following(self, user_id: str) -> List[Dict]:
        """Get all users that a user is following."""
        query = """
            SELECT u.* FROM users u
            JOIN relationships r ON u.id = r.following_id
            WHERE r.follower_id = %s AND r.relationship_type = 'follow'
        """
        return self.execute(query, (user_id,))
    
    # Mention operations
    def create_mention(self, status_id: str, mentioned_user_id: str) -> Dict:
        """Create a mention of a user in a status."""
        query = """
            INSERT INTO mentions (status_id, mentioned_user_id)
            VALUES (%s, %s)
            ON CONFLICT (status_id, mentioned_user_id) DO NOTHING
            RETURNING *
        """
        result = self.execute(query, (status_id, mentioned_user_id))
        return result[0] if result else None
    
    def get_status_mentions(self, status_id: str) -> List[Dict]:
        """Get all mentions in a status."""
        query = """
            SELECT u.* FROM users u
            JOIN mentions m ON u.id = m.mentioned_user_id
            WHERE m.status_id = %s
        """
        return self.execute(query, (status_id,))
    
    def get_user_mentions(self, user_id: str, limit: int = 20,
                         since_id: str = None, max_id: str = None) -> List[Dict]:
        """Get all statuses that mention a user."""
        query = """
            SELECT s.* FROM statuses s
            JOIN mentions m ON s.id = m.status_id
            WHERE m.mentioned_user_id = %s
        """
        params = [user_id]
        
        if since_id:
            query += " AND s.id > %s"
            params.append(since_id)
        
        if max_id:
            query += " AND s.id < %s"
            params.append(max_id)
        
        query += " ORDER BY s.created_at DESC LIMIT %s"
        params.append(limit)
        
        return self.execute(query, tuple(params))

# Create a global database instance
db = Database() 