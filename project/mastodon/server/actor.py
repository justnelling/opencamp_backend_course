"""
Mastodon Actor Implementation

This module implements the Mastodon actor model for the server.
It handles user profiles and their associated data.
"""

from datetime import datetime
from typing import Dict, Optional

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