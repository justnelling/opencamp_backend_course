"""
Mastodon Actor Module

Handles Mastodon-specific actor functionality and profile information
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
from datetime import datetime

class MastodonActor:
    def __init__(self, local_domain: str, actor_name: str, display_name: str, public_key_pem: str):
        """Initialize the Mastodon actor.
        
        Args:
            local_domain: The server's domain
            actor_name: Username for the actor
            display_name: Display name for the actor
            public_key_pem: Public key in PEM format
        """
        self.local_domain = local_domain
        self.actor_name = actor_name
        self.display_name = display_name
        self.actor_id = f"https://{local_domain}/users/{actor_name}"
        self.public_key_pem = public_key_pem
    
    def register_routes(self, app: FastAPI):
        """Register Mastodon-specific actor routes."""
        
        @app.get(f"/api/v1/accounts/{self.actor_name}")
        async def mastodon_account():
            """Returns the actor's profile in Mastodon format"""
            return JSONResponse(content=self.get_mastodon_account_data())
        
        @app.get("/.well-known/webfinger")
        async def webfinger(resource: str):
            """Webfinger protocol implementation for actor discovery"""
            if resource and resource == f"acct:{self.actor_name}@{self.local_domain}":
                return JSONResponse(content=self.get_webfinger_data(resource))
            else:
                raise HTTPException(status_code=404, detail='Resource not found')
    
    def get_mastodon_account_data(self) -> Dict[str, Any]:
        """Generate the actor profile data in Mastodon format."""
        return {
            "id": self.actor_id,
            "username": self.actor_name,
            "acct": self.actor_name,
            "display_name": self.display_name,
            "locked": False,
            "bot": False,
            "discoverable": True,
            "group": False,
            "created_at": datetime.utcnow().isoformat(),
            "note": "",
            "url": self.actor_id,
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
        }
    
    def get_webfinger_data(self, resource: str) -> Dict[str, Any]:
        """Generate webfinger response data."""
        return {
            'subject': resource,
            'links': [
                {
                    'rel': 'self',
                    'type': 'application/activity+json',
                    'href': self.actor_id
                }
            ],
        } 