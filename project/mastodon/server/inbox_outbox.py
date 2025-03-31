"""
Mastodon Inbox/Outbox Implementation

This module implements the Mastodon inbox and outbox models for the server.
It handles storing and retrieving statuses and other activities.
"""

from datetime import datetime
from typing import Dict, List, Optional
import re

class Inbox:
    """Handles incoming activities."""
    
    def __init__(self):
        """Initialize inbox."""
        self.activities = []
        
    def add_activity(self, activity: Dict):
        """
        Add activity to inbox.
        
        Args:
            activity: Activity to add
        """
        self.activities.append(activity)
        
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
        activities = self.activities
        
        if since_id:
            activities = [a for a in activities if a["id"] > since_id]
            
        if max_id:
            activities = [a for a in activities if a["id"] < max_id]
            
        return sorted(activities, key=lambda x: x["id"])[-limit:]

class Outbox:
    """Handles outgoing activities."""
    
    def __init__(self):
        """Initialize outbox."""
        self.statuses = []
        
    def add_status(self, status: Dict):
        """
        Add status to outbox.
        
        Args:
            status: Status to add
        """
        self.statuses.append(status)
        
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
        statuses = self.statuses
        
        if since_id:
            statuses = [s for s in statuses if s["id"] > since_id]
            
        if max_id:
            statuses = [s for s in statuses if s["id"] < max_id]
            
        return sorted(statuses, key=lambda x: x["id"])[-limit:]
        
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
        statuses = [
            s for s in self.statuses
            if f"#{hashtag}" in s["content"].lower()
        ]
        
        if since_id:
            statuses = [s for s in statuses if s["id"] > since_id]
            
        if max_id:
            statuses = [s for s in statuses if s["id"] < max_id]
            
        return sorted(statuses, key=lambda x: x["id"])[-limit:]
        
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
        statuses = [
            s for s in self.statuses
            if s["account"]["username"] == username
        ]
        
        if since_id:
            statuses = [s for s in statuses if s["id"] > since_id]
            
        if max_id:
            statuses = [s for s in statuses if s["id"] < max_id]
            
        return sorted(statuses, key=lambda x: x["id"])[-limit:] 