"""
ActivityPub Inbox/Outbox Module

Handles inbox and outbox functionality for ActivityPub
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from signature import generate_http_signature

class Activity(BaseModel):
    type: str
    object: Optional[Dict[str, Any]] = None

class InboxOutboxManager:
    def __init__(self, actor_id: str, actor_name: str, local_domain: str, private_key):
        """Initialize the inbox/outbox manager.
        
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
        self.last_activity = None
    
    def register_routes(self, app: FastAPI):
        """Register inbox/outbox routes with the FastAPI app."""
        
        @app.post(f"/users/{self.actor_name}/inbox")
        async def inbox(activity: Activity):
            """Handle incoming activities."""
            return await self.handle_inbox(activity)
        
        @app.post(f"/users/{self.actor_name}/outbox")
        async def outbox(request: Request):
            """Handle outgoing activities."""
            return await self.handle_outbox(request)
        
        @app.get(f"/users/{self.actor_name}/outbox")
        async def outbox_get():
            """Get the contents of the outbox."""
            return await self.handle_outbox_get()
    
    async def handle_inbox(self, activity: Activity):
        """Process incoming activities from other actors."""
        if activity.type == 'Create':
            print(f"Received note: {activity.object['content']}")
            return JSONResponse(content={'message': 'Activity Received'}, status_code=202)
        else:
            raise HTTPException(status_code=400, detail='Activity type not supported')
    
    async def handle_outbox(self, request_or_activity):
        """Process outgoing activities from this actor.
        
        Args:
            request_or_activity: Either a FastAPI Request object or an activity dictionary
        """
        # Determine if we received a Request object or an activity dictionary
        if hasattr(request_or_activity, 'json'):
            # It's a Request object
            activity = await request_or_activity.json()
            request = request_or_activity
        else:
            # It's an activity dictionary
            activity = request_or_activity
            request = None
        
        # Store the activity
        self.last_activity = activity
        
        # If we have a request, sign the response
        if request:
            headers = await generate_http_signature(
                request, 
                self.private_key, 
                f"{self.actor_id}#main-key",
                self.local_domain
            )
            
            # Create and return the response with signatures
            response = JSONResponse(content=activity, status_code=202)
            for key, value in headers.items():
                response.headers[key] = value
            
            return response
        else:
            # No request, just return the activity
            return JSONResponse(content=activity, status_code=202)
    
    async def handle_outbox_get(self):
        """Retrieve the latest activity from the outbox."""
        if self.last_activity:
            content = self.last_activity['object']['content']
            print("Content from outbox:", content)
            return JSONResponse(content=self.last_activity)
        else:
            raise HTTPException(status_code=404, detail='Outbox is empty')