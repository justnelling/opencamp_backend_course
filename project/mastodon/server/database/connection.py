"""
Database Connection

This module handles the database connection and core operations.
"""

import os
import logging
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from uuid import UUID
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    """Database connection and operations handler."""
    
    def __init__(self):
        """Initialize database connection."""
        # Get database URL from environment or use default for insecure local setup
        self.db_url = os.getenv('DATABASE_URL', 'postgresql://root@localhost:26257/mastodon?sslmode=disable')
        self.conn = None
        self.connect()
        
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
            
    def execute(self, query: str, params: tuple = None, fetch_one=False) -> Optional[List[Dict]] | Optional[Dict]:
        """
        Execute a database query.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: Whether to fetch only one row
            
        Returns:
            List of results as dictionaries, a single dictionary if fetch_one=True, or None
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    if fetch_one:
                        return cur.fetchone()
                    return cur.fetchall()
                # For INSERT/UPDATE/DELETE without RETURNING
                self.conn.commit()
                return None # Indicate success for commit operations
        except psycopg2.Error as e:
            logger.error(f"Database query failed: {e}")
            self.conn.rollback()
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during query execution: {e}")
            self.conn.rollback()
            raise
            
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Closed database connection")

    # --- User Methods ---
    def get_user(self, username: str) -> Optional[Dict]:
        """Fetch a user by username."""
        query = "SELECT * FROM users WHERE username = %s"
        return self.execute(query, (username,), fetch_one=True)

    def get_user_by_id(self, user_id: UUID) -> Optional[Dict]:
        """Fetch a user by ID."""
        query = "SELECT * FROM users WHERE id = %s"
        return self.execute(query, (user_id,), fetch_one=True)

    def create_user(self, username: str, password_hash: str, email: str) -> Optional[Dict]:
        """Create a new user and return their data."""
        # TODO: Add proper password hashing before storing
        query = """
            INSERT INTO users (username, password_hash, email)
            VALUES (%s, %s, %s)
            RETURNING *;
        """
        # In production, hash the password before passing it here
        return self.execute(query, (username, password_hash, email), fetch_one=True)

    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """Verify user credentials and return user data if valid."""
        # Hash the password before comparison
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        query = "SELECT * FROM users WHERE username = %s AND password_hash = %s"
        return self.execute(query, (username, password_hash), fetch_one=True)

    # --- Status Methods ---
    def create_status(self, user_id: UUID, content: str, visibility: str, sensitive: bool, spoiler_text: Optional[str], latitude: Optional[float], longitude: Optional[float]) -> Optional[Dict]:
        """Create a new status and return its data."""
        query = """
            INSERT INTO statuses (user_id, content, visibility, sensitive, spoiler_text, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
        """
        return self.execute(query, (user_id, content, visibility, sensitive, spoiler_text, latitude, longitude), fetch_one=True)

    def get_public_timeline(self, limit: int, since_id: Optional[str], max_id: Optional[str]) -> List[Dict]:
        """Fetch public timeline statuses."""
        query = """
            SELECT s.*, u.username as username
            FROM statuses s
            JOIN users u ON s.user_id = u.id
            WHERE s.visibility = 'public'
        """
        params = []
        if since_id:
            query += " AND s.id > %s"
            params.append(since_id)
        if max_id:
            query += " AND s.id < %s"
            params.append(max_id)

        query += " ORDER BY s.created_at DESC LIMIT %s"
        params.append(limit)

        return self.execute(query, tuple(params))

    def get_hashtag_timeline(self, hashtag: str, limit: int, since_id: Optional[str], max_id: Optional[str]) -> List[Dict]:
        """Fetch statuses for a specific hashtag."""
        query = """
            SELECT s.*, u.username as username
            FROM statuses s
            JOIN users u ON s.user_id = u.id
            JOIN status_hashtags sh ON s.id = sh.status_id
            JOIN hashtags h ON sh.hashtag_id = h.id
            WHERE h.name = %s
        """
        params = [hashtag]
        if since_id:
            query += " AND s.id > %s"
            params.append(since_id)
        if max_id:
            query += " AND s.id < %s"
            params.append(max_id)

        query += " ORDER BY s.created_at DESC LIMIT %s"
        params.append(limit)

        return self.execute(query, tuple(params))

    def get_user_statuses(self, user_id: UUID, limit: int, since_id: Optional[str], max_id: Optional[str]) -> List[Dict]:
        """Fetch statuses for a specific user."""
        query = """
            SELECT s.*, u.username as username
            FROM statuses s
            JOIN users u ON s.user_id = u.id
            WHERE s.user_id = %s
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

    # --- Media Methods ---
    def create_media_attachment(self, file_path: str, file_type: str, description: Optional[str] = None, status_id: Optional[UUID] = None) -> Optional[Dict]:
        """Create a new media attachment."""
        query = """
            INSERT INTO media_attachments (status_id, file_path, file_type, description)
            VALUES (%s, %s, %s, %s)
            RETURNING *;
        """
        return self.execute(query, (status_id, file_path, file_type, description), fetch_one=True)

    def get_status_media(self, status_id: UUID) -> List[Dict]:
        """Fetch media attachments for a given status."""
        query = """
            SELECT id, file_path as url, file_type, description
            FROM media_attachments
            WHERE status_id = %s;
        """
        return self.execute(query, (status_id,))

    def update_media_status(self, media_id: str, status_id: UUID) -> Optional[Dict]:
        """Update the status_id of a media attachment."""
        query = """
            UPDATE media_attachments 
            SET status_id = %s 
            WHERE id::text = %s
            RETURNING id, file_path as url, file_type, description;
        """
        result = self.execute(query, (status_id, media_id), fetch_one=True)
        return result

    # --- Relationship Methods ---
    def get_followers(self, user_id: UUID) -> List[Dict]:
        """Get list of users following the given user."""
        query = """
            SELECT u.*
            FROM users u
            JOIN relationships r ON u.id = r.follower_id
            WHERE r.following_id = %s AND r.relationship_type = 'follow'
        """
        return self.execute(query, (user_id,))

    def get_following(self, user_id: UUID) -> List[Dict]:
        """Get list of users the given user is following."""
        query = """
            SELECT u.*
            FROM users u
            JOIN relationships r ON u.id = r.following_id
            WHERE r.follower_id = %s AND r.relationship_type = 'follow'
        """
        return self.execute(query, (user_id,))

    # --- Hashtag Methods ---
    def create_hashtag(self, name: str) -> Optional[Dict]:
        """Create a new hashtag if it doesn't exist."""
        query = """
            INSERT INTO hashtags (name)
            VALUES (%s)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING *;
        """
        return self.execute(query, (name,), fetch_one=True)

    def link_status_to_hashtag(self, status_id: UUID, hashtag_id: UUID) -> None:
        """Link a status to a hashtag."""
        query = """
            INSERT INTO status_hashtags (status_id, hashtag_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
        """
        return self.execute(query, (status_id, hashtag_id))

# Instantiate the database connection globally
db = Database() 