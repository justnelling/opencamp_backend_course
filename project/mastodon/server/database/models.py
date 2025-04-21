"""
Database Models

This module contains all the database operations for different models.
"""

from typing import Dict, List, Optional
from .connection import Database

class UserModel:
    """User-related database operations."""
    
    def __init__(self, db: Database):
        self.db = db
        
    def create_user(self, username: str, password_hash: str, display_name: str = None,
                   bio: str = None, avatar_url: str = None, header_url: str = None) -> Dict:
        """Create a new user."""
        query = """
            INSERT INTO users (username, password_hash, display_name, bio, avatar_url, header_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        return self.db.execute(query, (username, password_hash, display_name, bio, avatar_url, header_url))[0]
        
    def get_user(self, username: str) -> Optional[Dict]:
        """Get a user by username."""
        query = "SELECT * FROM users WHERE username = %s"
        result = self.db.execute(query, (username,))
        return result[0] if result else None
        
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get a user by ID."""
        query = "SELECT * FROM users WHERE id = %s"
        result = self.db.execute(query, (user_id,))
        return result[0] if result else None

class StatusModel:
    """Status-related database operations."""
    
    def __init__(self, db: Database):
        self.db = db
        
    def create_status(self, user_id: str, content: str, visibility: str = 'public',
                     sensitive: bool = False, spoiler_text: str = None,
                     latitude: float = None, longitude: float = None) -> Dict:
        """Create a new status."""
        query = """
            INSERT INTO statuses (user_id, content, visibility, sensitive, spoiler_text, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        return self.db.execute(query, (user_id, content, visibility, sensitive, spoiler_text, latitude, longitude))[0]
        
    def get_status(self, status_id: str) -> Optional[Dict]:
        """Get a status by ID."""
        query = "SELECT * FROM statuses WHERE id = %s"
        result = self.db.execute(query, (status_id,))
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
        
        return self.db.execute(query, tuple(params))
        
    def get_public_timeline(self, limit: int = 20, since_id: str = None, max_id: str = None) -> List[Dict]:
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
        
        return self.db.execute(query, tuple(params))

class MediaModel:
    """Media-related database operations."""
    
    def __init__(self, db: Database):
        self.db = db
        
    def create_media_attachment(self, file_path: str, file_type: str,
                              description: str = None, status_id: str = None) -> Dict:
        """Create a new media attachment."""
        query = """
            INSERT INTO media_attachments (status_id, file_path, file_type, description)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """
        return self.db.execute(query, (status_id, file_path, file_type, description))[0]
        
    def get_status_media(self, status_id: str) -> List[Dict]:
        """Get media attachments for a status."""
        query = "SELECT * FROM media_attachments WHERE status_id = %s"
        return self.db.execute(query, (status_id,))
        
    def update_media_status(self, media_id: str, status_id: str) -> Dict:
        """Update the status ID of a media attachment."""
        query = """
            UPDATE media_attachments 
            SET status_id = %s 
            WHERE id::text = %s
            RETURNING *
        """
        result = self.db.execute(query, (status_id, media_id))
        return result[0] if result else None

class HashtagModel:
    """Hashtag-related database operations."""
    
    def __init__(self, db: Database):
        self.db = db
        
    def create_hashtag(self, name: str) -> Dict:
        """Create a new hashtag."""
        query = """
            INSERT INTO hashtags (name)
            VALUES (%s)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING *
        """
        return self.db.execute(query, (name,))[0]
        
    def link_status_to_hashtag(self, status_id: str, hashtag_id: str):
        """Link a status to a hashtag."""
        query = """
            INSERT INTO status_hashtags (status_id, hashtag_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """
        self.db.execute(query, (status_id, hashtag_id))
        
    def get_hashtag_timeline(self, hashtag: str, limit: int = 20,
                           since_id: str = None, max_id: str = None) -> List[Dict]:
        """Get timeline for a hashtag."""
        query = """
            SELECT s.* FROM statuses s
            JOIN status_hashtags sh ON s.id = sh.status_id
            JOIN hashtags h ON sh.hashtag_id = h.id
            WHERE h.name = %s AND s.visibility = 'public'
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
        
        return self.db.execute(query, tuple(params))

class RelationshipModel:
    """Relationship-related database operations."""
    
    def __init__(self, db: Database):
        self.db = db
        
    def follow_user(self, follower_id: str, following_id: str):
        """Create a follow relationship."""
        query = """
            INSERT INTO relationships (follower_id, following_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """
        self.db.execute(query, (follower_id, following_id))
        
    def unfollow_user(self, follower_id: str, following_id: str):
        """Remove a follow relationship."""
        query = """
            DELETE FROM relationships
            WHERE follower_id = %s AND following_id = %s
        """
        self.db.execute(query, (follower_id, following_id))
        
    def get_followers(self, user_id: str) -> List[Dict]:
        """Get followers of a user."""
        query = """
            SELECT u.* FROM users u
            JOIN relationships r ON u.id = r.follower_id
            WHERE r.following_id = %s
        """
        return self.db.execute(query, (user_id,))
        
    def get_following(self, user_id: str) -> List[Dict]:
        """Get users followed by a user."""
        query = """
            SELECT u.* FROM users u
            JOIN relationships r ON u.id = r.following_id
            WHERE r.follower_id = %s
        """
        return self.db.execute(query, (user_id,)) 