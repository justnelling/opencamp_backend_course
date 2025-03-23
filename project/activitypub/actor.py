"""
ActivityPub Actor Module

Handles actor creation and webfinger protocol
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any, List

class ActorManager:
    def __init__(self, local_domain: str, actor_name: str, display_name: str, public_key_pem: str):
        """Initialize the actor manager.
        
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
        """Register actor-related routes with the FastAPI app."""
        
        @app.get(f"/users/{self.actor_name}")
        async def actor():
            """Returns the actor's profile"""
            return JSONResponse(content=self.get_actor_data())
        
        @app.get("/.well-known/webfinger")
        async def webfinger(resource: str):
            """Webfinger protocol implementation for actor discovery"""
            if resource and resource == f"acct:{self.actor_name}@{self.local_domain}":
                return JSONResponse(content=self.get_webfinger_data(resource))
            else:
                raise HTTPException(status_code=404, detail='Resource not found')
    
    def get_actor_data(self) -> Dict[str, Any]:
        """Generate the actor profile data."""
        return {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1"
            ],
            "id": self.actor_id,
            "type": "Person",
            "name": self.display_name,
            "preferredUsername": self.actor_name,
            "inbox": f"{self.actor_id}/inbox",
            "outbox": f"{self.actor_id}/outbox",
            "publicKey": {
                "id": f"{self.actor_id}#main-key",
                "owner": self.actor_id,
                "publicKeyPem": self.public_key_pem
            },
            "endpoints": {
                "id": f"{self.actor_id}#endpoints",
                "uploadMedia": f"{self.actor_id}/endpoints/uploadMedia"
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