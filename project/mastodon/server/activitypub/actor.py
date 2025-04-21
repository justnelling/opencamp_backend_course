"""
Actor Module

This module implements the Actor class for ActivityPub.
"""

import json
import logging
from datetime import datetime

from server.database import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Actor:
    """Represents a Mastodon user actor."""
    
    def __init__(self, username=None):
        """
        Initialize actor.
        
        Args:
            username: Optional username to load
        """
        self.username = username
        self.display_name = None
        self.bio = None
        self.avatar = None
        self.header = None
        self.followers_count = 0
        self.following_count = 0
        self.statuses_count = 0
        
        if username:
            self.load_from_db()
            
    def load_from_db(self):
        """Load actor data from database."""
        try:
            user = db.get_user(self.username)
            if user:
                self.display_name = user.get('display_name')
                self.bio = user.get('bio')
                self.avatar = user.get('avatar_url')
                self.header = user.get('header_url')
                self.followers_count = len(db.get_followers(user['id']))
                self.following_count = len(db.get_following(user['id']))
                self.statuses_count = len(db.get_user_statuses(user['id']))
            else:
                # Create new user if not found
                user = db.create_user(
                    username=self.username,
                    display_name=self.username,
                    bio="",
                    avatar_url=None,
                    header_url=None
                )
                if user:
                    self.display_name = user['display_name']
        except Exception as e:
            logger.error(f"Error loading actor from database: {e}")
            
    def save_to_db(self):
        """Save actor data to database."""
        try:
            if self.username:
                db.update_user(
                    username=self.username,
                    display_name=self.display_name,
                    bio=self.bio,
                    avatar_url=self.avatar,
                    header_url=self.header
                )
        except Exception as e:
            logger.error(f"Error saving actor to database: {e}")
            
    def to_dict(self):
        """
        Convert actor to dictionary.
        
        Returns:
            Dict containing actor data
        """
        return {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1"
            ],
            "id": f"https://example.com/users/{self.username}",
            "type": "Person",
            "name": self.display_name or self.username,
            "preferredUsername": self.username,
            "summary": self.bio or "",
            "inbox": f"https://example.com/users/{self.username}/inbox",
            "outbox": f"https://example.com/users/{self.username}/outbox",
            "followers": f"https://example.com/users/{self.username}/followers",
            "following": f"https://example.com/users/{self.username}/following",
            "publicKey": {
                "id": f"https://example.com/users/{self.username}#main-key",
                "owner": f"https://example.com/users/{self.username}",
                "publicKeyPem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----"
            },
            "icon": {
                "type": "Image",
                "mediaType": "image/jpeg",
                "url": self.avatar or "https://example.com/avatar.jpg"
            },
            "image": {
                "type": "Image",
                "mediaType": "image/jpeg",
                "url": self.header or "https://example.com/header.jpg"
            }
        } 