"""
Mastodon Actor Implementation

This module implements the Mastodon actor model for the server.
It handles user profiles and their associated data.
"""

from datetime import datetime
from typing import Dict, Optional
from database import db

class Actor:
    """Represents a Mastodon user actor."""
    
    def __init__(
        self,
        username: str = "testuser",
        display_name: str = "Test User",
        bio: str = "Test user bio",
        avatar: str = "https://example.com/avatar.jpg",
        header: str = "https://example.com/header.jpg",
        followers_count: int = 0,
        following_count: int = 0,
        statuses_count: int = 0
    ):
        """
        Initialize actor.
        
        Args:
            username: Username
            display_name: Display name
            bio: User bio
            avatar: Avatar URL
            header: Header image URL
            followers_count: Number of followers
            following_count: Number of following
            statuses_count: Number of statuses
        """
        self.username = username
        self.display_name = display_name
        self.bio = bio
        self.avatar = avatar
        self.header = header
        self.followers_count = followers_count
        self.following_count = following_count
        self.statuses_count = statuses_count
        self.created_at = datetime.now().isoformat()
        
        # Try to load from database or create new
        self._load_or_create()
    
    def _load_or_create(self):
        """Load actor from database or create if not exists."""
        user_data = db.get_user(self.username)
        
        if user_data:
            # Update instance with database data
            self.id = user_data['id']
            self.username = user_data['username']
            self.display_name = user_data['display_name'] or self.display_name
            self.bio = user_data['bio'] or self.bio
            self.avatar = user_data['avatar_url'] or self.avatar
            self.header = user_data['header_url'] or self.header
            self.created_at = user_data['created_at'].isoformat()
            
            # Get counts from database
            self.followers_count = len(db.get_followers(self.id))
            self.following_count = len(db.get_following(self.id))
            self.statuses_count = len(db.get_user_statuses(self.id))
        else:
            # Create new user in database
            user_data = db.create_user(
                username=self.username,
                display_name=self.display_name,
                bio=self.bio,
                avatar_url=self.avatar,
                header_url=self.header
            )
            
            if user_data:
                self.id = user_data['id']
            else:
                # Fallback to a default ID if database creation fails
                self.id = f"/users/{self.username}"
    
    def save(self):
        """Save actor to database."""
        # This would update the user in the database
        # For now, we're just creating on init
        pass
        
    def to_dict(self) -> Dict:
        """
        Convert actor to dictionary.
        
        Returns:
            Actor data as dict
        """
        return {
            "id": f"/users/{self.username}",
            "username": self.username,
            "acct": self.username,
            "display_name": self.display_name,
            "locked": False,
            "bot": False,
            "discoverable": True,
            "group": False,
            "created_at": self.created_at,
            "note": self.bio,
            "url": f"https://example.com/users/{self.username}",
            "avatar": self.avatar,
            "avatar_static": self.avatar,
            "header": self.header,
            "header_static": self.header,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "statuses_count": self.statuses_count,
            "last_status_at": None,
            "emojis": [],
            "fields": [],
            "source": {
                "privacy": "public",
                "sensitive": False,
                "language": "en",
                "note": self.bio,
                "fields": []
            }
        } 