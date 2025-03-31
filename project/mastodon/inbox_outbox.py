"""
Mastodon Inbox/Outbox Module

Handles Mastodon-specific inbox and outbox functionality
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

from .signature import generate_http_signature

class Activity(BaseModel):
    type: str
    object: Optional[Dict[str, Any]] = None

class MastodonInboxOutbox:
    def __init__(self, actor_id: str, actor_name: str, local_domain: str, private_key):
        """Initialize the Mastodon inbox/outbox manager.
        
        Args:
            actor_id: The actor's ID
            actor_name: The actor's username
            local_domain: The server's domain
            private_key: RSA private key for signing outbox responses
        """
        self.actor_id = actor_id
        self.actor_name = actor_name
        self.local_domain = local_domain
        self.private_key = private_key
        self.activities: List[Dict[str, Any]] = []
    
    def register_routes(self, app: FastAPI):
        """Register Mastodon-specific inbox/outbox routes."""
        
        @app.post(f"/api/v1/statuses")
        async def create_status(request: Request):
            """Handle status creation in Mastodon format."""
            return await self.handle_status_creation(request)
        
        @app.get(f"/api/v1/statuses")
        async def get_statuses():
            """Get statuses in Mastodon format."""
            return await self.handle_statuses_get()
    
    async def handle_status_creation(self, request: Request):
        """Process status creation in Mastodon format."""
        form_data = await request.form()
        
        # Convert Mastodon format to ActivityPub
        content = form_data.get("status", "")
        media_ids = form_data.getlist("media_ids[]")
        visibility = form_data.get("visibility", "public")
        
        # Create ActivityPub note
        note = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Note",
            "content": content,
            "published": datetime.utcnow().isoformat(),
            "to": ["https://www.w3.org/ns/activitystreams#Public"]
        }
        
        if media_ids:
            note["attachment"] = [
                {"type": "Image", "url": media_id} for media_id in media_ids
            ]
        
        # Create the activity
        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Create",
            "actor": self.actor_id,
            "object": note
        }
        
        # Store the activity
        self.activities.append(activity)
        
        # Sign the response
        headers = await generate_http_signature(
            request, 
            self.private_key, 
            f"{self.actor_id}#main-key",
            self.local_domain
        )
        
        # Return Mastodon-compatible status
        response = JSONResponse(content=self.convert_to_mastodon_status(activity))
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
    
    async def handle_statuses_get(self):
        """Retrieve statuses in Mastodon format."""
        mastodon_statuses = [
            self.convert_to_mastodon_status(activity)
            for activity in self.activities
        ]
        return JSONResponse(content=mastodon_statuses)
    
    def convert_to_mastodon_status(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ActivityPub activity to Mastodon status format."""
        note = activity.get("object", {})
        
        return {
            "id": note.get("id", ""),
            "uri": note.get("id", ""),
            "url": note.get("id", ""),
            "content": note.get("content", ""),
            "text": note.get("content", ""),
            "created_at": note.get("published", datetime.utcnow().isoformat()),
            "account": {
                "id": activity.get("actor", ""),
                "username": self.actor_name,
                "acct": self.actor_name,
                "display_name": self.actor_name,
                "locked": False,
                "bot": False,
                "discoverable": True,
                "group": False,
                "created_at": datetime.utcnow().isoformat(),
                "note": "",
                "url": activity.get("actor", ""),
                "avatar": None,
                "avatar_static": None,
                "header": None,
                "header_static": None,
                "followers_count": 0,
                "following_count": 0,
                "statuses_count": 0,
                "last_status_at": None,
                "emojis": [],
                "fields": [],
                "source": {
                    "privacy": "public",
                    "sensitive": False,
                    "language": "en",
                    "note": "",
                    "fields": [],
                    "follow_requests_count": 0
                }
            },
            "media_attachments": note.get("attachment", []),
            "emojis": [],
            "tags": note.get("tag", []),
            "visibility": "public",
            "favourited": False,
            "reblogged": False,
            "muted": False,
            "bookmarked": False,
            "pinned": False
        } 