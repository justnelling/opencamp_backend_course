"""
ActivityPub Inbox/Outbox

This module implements the ActivityPub inbox and outbox models.
"""

from datetime import datetime
from typing import Dict, List, Optional
import re
from ..database import db
from ..queue import ActivityQueue

class Inbox:
    """Handles incoming activities."""
    
    def __init__(self):
        """Initialize inbox."""
        # We'll use the database for activities
        pass
        
    def add_activity(self, activity: Dict):
        """
        Add activity to inbox.
        
        Args:
            activity: Activity to add
        """
        # For now, we're not storing activities in the database
        # This would be implemented for ActivityPub federation
        pass
        
    def get_activities(
        self,
        limit: int = 20,
        since_id: Optional[str] = None,
        max_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get activities from inbox.
        
        Args:
            limit: Number of activities to fetch
            since_id: Return only activities newer than this ID
            max_id: Return only activities older than this ID
            
        Returns:
            List of activities
        """
        # For now, we're not storing activities in the database
        return []

class Outbox:
    """Handles outgoing activities."""
    
    def __init__(self):
        """Initialize outbox."""
        # Initialize queue system
        self.queue = ActivityQueue()
        
    def add_status(self, status: Dict):
        """
        1. store to database
        2. create activity
        3. add activity to queue
        
        Args:
            status: Status to add
        """
        # Extract user ID from account
        username = status.get('account', {}).get('username')
        if not username:
            raise ValueError("Status must include account information")
            
        # Get user from database
        user = db.get_user(username)
        if not user:
            raise ValueError(f"User {username} not found")
            
        # Create status in database
        db_status = db.create_status(
            user_id=user['id'],
            content=status.get('content', ''),
            visibility=status.get('visibility', 'public'),
            sensitive=status.get('sensitive', False),
            spoiler_text=status.get('spoiler_text', ''),
            latitude=status.get('location', {}).get('coordinates', [None, None])[1],
            longitude=status.get('location', {}).get('coordinates', [None, None])[0]
        )
        
        if db_status:
            # Add media attachments
            for media in status.get('media_attachments', []):
                db.create_media_attachment(
                    status_id=db_status['id'],
                    file_path=media.get('url', ''),
                    file_type=media.get('type', 'image/jpeg'),
                    description=media.get('description', '')
                )
            
            # Extract and add hashtags
            hashtags = re.findall(r'#(\w+)', status.get('content', ''))
            for hashtag_name in hashtags:
                hashtag = db.create_hashtag(hashtag_name)
                if hashtag:
                    db.link_status_to_hashtag(db_status['id'], hashtag['id'])
                    
            # Create ActivityPub activity
            activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "type": "Create",
                "actor": f"/users/{username}",
                "object": {
                    "type": "Note",
                    "id": f"/statuses/{db_status['id']}",
                    "content": db_status['content'],
                    "published": db_status['created_at'].isoformat(),
                    "attributedTo": f"/users/{username}",
                    "to": ["https://www.w3.org/ns/activitystreams#Public"],
                    "cc": [f"/users/{username}/followers"]
                }
            }
            
            # Queue activity for delivery
            self.queue.enqueue_activity(activity)
        
    def get_statuses(
        self,
        limit: int = 20,
        since_id: Optional[str] = None,
        max_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get statuses from outbox.
        
        Args:
            limit: Number of statuses to fetch
            since_id: Return only statuses newer than this ID
            max_id: Return only statuses older than this ID
            
        Returns:
            List of statuses
        """
        # Get statuses from database
        db_statuses = db.get_public_timeline(limit, since_id, max_id)
        
        # Convert to Mastodon format
        statuses = []
        for db_status in db_statuses:
            # Get user
            user = db.get_user_by_id(db_status['user_id'])
            if not user:
                continue
                
            # Get media attachments
            media_attachments = db.get_status_media(db_status['id'])
            
            # Create status dict
            status = {
                "id": db_status['id'],
                "created_at": db_status['created_at'].isoformat(),
                "content": db_status['content'],
                "visibility": db_status['visibility'],
                "sensitive": db_status['sensitive'],
                "spoiler_text": db_status['spoiler_text'] or "",
                "account": {
                    "id": f"/users/{user['username']}",
                    "username": user['username'],
                    "acct": user['username'],
                    "display_name": user['display_name'] or user['username'],
                    "locked": False,
                    "bot": False,
                    "discoverable": True,
                    "group": False,
                    "created_at": user['created_at'].isoformat(),
                    "note": user['bio'] or "",
                    "url": f"https://example.com/users/{user['username']}",
                    "avatar": user['avatar_url'] or "https://example.com/avatar.jpg",
                    "avatar_static": user['avatar_url'] or "https://example.com/avatar.jpg",
                    "header": user['header_url'] or "https://example.com/header.jpg",
                    "header_static": user['header_url'] or "https://example.com/header.jpg",
                    "followers_count": len(db.get_followers(user['id'])),
                    "following_count": len(db.get_following(user['id'])),
                    "statuses_count": len(db.get_user_statuses(user['id'])),
                    "last_status_at": None,
                    "emojis": [],
                    "fields": []
                },
                "media_attachments": [
                    {
                        "id": media['id'],
                        "type": media['file_type'],
                        "url": media['url'],
                        "preview_url": media['url'],
                        "remote_url": None,
                        "text_url": None,
                        "description": media['description'] or None,
                        "blurhash": None
                    }
                    for media in media_attachments
                ],
                "location": None
            }
            
            # Add location if present
            if db_status['latitude'] is not None and db_status['longitude'] is not None:
                status["location"] = {
                    "name": f"{db_status['latitude']}, {db_status['longitude']}",
                    "type": "Point",
                    "coordinates": [db_status['longitude'], db_status['latitude']]
                }
            
            statuses.append(status)
            
        return statuses
        
    def get_statuses_by_hashtag(
        self,
        hashtag: str,
        limit: int = 20,
        since_id: Optional[str] = None,
        max_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get statuses containing hashtag.
        
        Args:
            hashtag: Hashtag to search for
            limit: Number of statuses to fetch
            since_id: Return only statuses newer than this ID
            max_id: Return only statuses older than this ID
            
        Returns:
            List of statuses
        """
        # Get statuses from database
        db_statuses = db.get_hashtag_timeline(hashtag, limit, since_id, max_id)
        
        # Convert to Mastodon format (similar to get_statuses)
        statuses = []
        for db_status in db_statuses:
            # Get user
            user = db.get_user_by_id(db_status['user_id'])
            if not user:
                continue
                
            # Get media attachments
            media_attachments = db.get_status_media(db_status['id'])
            
            # Create status dict
            status = {
                "id": db_status['id'],
                "created_at": db_status['created_at'].isoformat(),
                "content": db_status['content'],
                "visibility": db_status['visibility'],
                "sensitive": db_status['sensitive'],
                "spoiler_text": db_status['spoiler_text'] or "",
                "account": {
                    "id": f"/users/{user['username']}",
                    "username": user['username'],
                    "acct": user['username'],
                    "display_name": user['display_name'] or user['username'],
                    "locked": False,
                    "bot": False,
                    "discoverable": True,
                    "group": False,
                    "created_at": user['created_at'].isoformat(),
                    "note": user['bio'] or "",
                    "url": f"https://example.com/users/{user['username']}",
                    "avatar": user['avatar_url'] or "https://example.com/avatar.jpg",
                    "avatar_static": user['avatar_url'] or "https://example.com/avatar.jpg",
                    "header": user['header_url'] or "https://example.com/header.jpg",
                    "header_static": user['header_url'] or "https://example.com/header.jpg",
                    "followers_count": len(db.get_followers(user['id'])),
                    "following_count": len(db.get_following(user['id'])),
                    "statuses_count": len(db.get_user_statuses(user['id'])),
                    "last_status_at": None,
                    "emojis": [],
                    "fields": []
                },
                "media_attachments": [
                    {
                        "id": media['id'],
                        "type": media['file_type'],
                        "url": media['url'],
                        "preview_url": media['url'],
                        "remote_url": None,
                        "text_url": None,
                        "description": media['description'] or None,
                        "blurhash": None
                    }
                    for media in media_attachments
                ],
                "location": None
            }
            
            # Add location if present
            if db_status['latitude'] is not None and db_status['longitude'] is not None:
                status["location"] = {
                    "name": f"{db_status['latitude']}, {db_status['longitude']}",
                    "type": "Point",
                    "coordinates": [db_status['longitude'], db_status['latitude']]
                }
            
            statuses.append(status)
            
        return statuses
        
    def get_statuses_by_user(
        self,
        username: str,
        limit: int = 20,
        since_id: Optional[str] = None,
        max_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get statuses by user.
        
        Args:
            username: Username to fetch statuses for
            limit: Number of statuses to fetch
            since_id: Return only statuses newer than this ID
            max_id: Return only statuses older than this ID
            
        Returns:
            List of statuses
        """
        # Get user
        user = db.get_user(username)
        if not user:
            return []
            
        # Get statuses from database
        db_statuses = db.get_user_statuses(user['id'], limit, since_id, max_id)
        
        # Convert to Mastodon format (similar to get_statuses)
        statuses = []
        for db_status in db_statuses:
            # Get media attachments
            media_attachments = db.get_status_media(db_status['id'])
            
            # Create status dict
            status = {
                "id": db_status['id'],
                "created_at": db_status['created_at'].isoformat(),
                "content": db_status['content'],
                "visibility": db_status['visibility'],
                "sensitive": db_status['sensitive'],
                "spoiler_text": db_status['spoiler_text'] or "",
                "account": {
                    "id": f"/users/{user['username']}",
                    "username": user['username'],
                    "acct": user['username'],
                    "display_name": user['display_name'] or user['username'],
                    "locked": False,
                    "bot": False,
                    "discoverable": True,
                    "group": False,
                    "created_at": user['created_at'].isoformat(),
                    "note": user['bio'] or "",
                    "url": f"https://example.com/users/{user['username']}",
                    "avatar": user['avatar_url'] or "https://example.com/avatar.jpg",
                    "avatar_static": user['avatar_url'] or "https://example.com/avatar.jpg",
                    "header": user['header_url'] or "https://example.com/header.jpg",
                    "header_static": user['header_url'] or "https://example.com/header.jpg",
                    "followers_count": len(db.get_followers(user['id'])),
                    "following_count": len(db.get_following(user['id'])),
                    "statuses_count": len(db.get_user_statuses(user['id'])),
                    "last_status_at": None,
                    "emojis": [],
                    "fields": []
                },
                "media_attachments": [
                    {
                        "id": media['id'],
                        "type": media['file_type'],
                        "url": media['url'],
                        "preview_url": media['url'],
                        "remote_url": None,
                        "text_url": None,
                        "description": media['description'] or None,
                        "blurhash": None
                    }
                    for media in media_attachments
                ],
                "location": None
            }
            
            # Add location if present
            if db_status['latitude'] is not None and db_status['longitude'] is not None:
                status["location"] = {
                    "name": f"{db_status['latitude']}, {db_status['longitude']}",
                    "type": "Point",
                    "coordinates": [db_status['longitude'], db_status['latitude']]
                }
            
            statuses.append(status)
            
        return statuses 