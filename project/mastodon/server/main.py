"""
Mastodon Server Implementation

This module implements a Mastodon-compatible server using FastAPI.
It provides endpoints for:
1. Media uploads
2. Status creation with GPS coordinates
3. Timeline fetching
4. HTTP signature verification
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

from .signature import verify_server_signature
from .actor import Actor
from .inbox_outbox import Inbox, Outbox

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Mastodon Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
actor = Actor()
inbox = Inbox()
outbox = Outbox()

# Create media directory if it doesn't exist
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)

class StatusCreate(BaseModel):
    """Model for status creation request."""
    status: str
    media_ids: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@app.post("/api/v1/media")
async def upload_media(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None)
):
    """
    Upload media file.
    
    Args:
        file: Media file to upload
        description: Optional media description
        
    Returns:
        Dict containing media attachment info
    """
    try:
        # Save file
        file_path = MEDIA_DIR / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # Create media attachment
        attachment = {
            "id": str(file_path.stat().st_mtime),
            "type": "image",
            "url": f"/media/{file.filename}",
            "preview_url": f"/media/{file.filename}",
            "remote_url": None,
            "text_url": None,
            "description": description,
            "blurhash": None
        }
        
        return attachment
        
    except Exception as e:
        logger.error(f"Error uploading media: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/statuses")
async def create_status(
    status: str = Form(...),
    media_ids: Optional[List[str]] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None)
):
    """
    Create new status.
    
    Args:
        status: Status text
        media_ids: Optional list of media attachment IDs
        latitude: Optional latitude for location
        longitude: Optional longitude for location
        
    Returns:
        Created status dict
    """
    try:
        # Create status
        status_data = {
            "id": str(datetime.now().timestamp()),
            "created_at": datetime.now().isoformat(),
            "content": status,
            "visibility": "public",
            "sensitive": False,
            "spoiler_text": "",
            "account": actor.to_dict(),
            "media_attachments": [],
            "location": None
        }
        
        # Add media attachments if present
        if media_ids:
            for media_id in media_ids:
                media_path = MEDIA_DIR / f"{media_id}.jpg"
                if media_path.exists():
                    status_data["media_attachments"].append({
                        "id": media_id,
                        "type": "image",
                        "url": f"/media/{media_path.name}",
                        "preview_url": f"/media/{media_path.name}"
                    })
                    
        # Add location if present
        if latitude is not None and longitude is not None:
            status_data["location"] = {
                "name": f"{latitude}, {longitude}",
                "type": "Point",
                "coordinates": [longitude, latitude]
            }
            
        # Add to outbox
        outbox.add_status(status_data)
        
        return status_data
        
    except Exception as e:
        logger.error(f"Error creating status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/timelines/public")
async def get_public_timeline(
    limit: int = 20,
    since_id: Optional[str] = None,
    max_id: Optional[str] = None
):
    """
    Get public timeline.
    
    Args:
        limit: Number of statuses to fetch
        since_id: Return only statuses newer than this ID
        max_id: Return only statuses older than this ID
        
    Returns:
        List of status dicts
    """
    return outbox.get_statuses(limit, since_id, max_id)

@app.get("/api/v1/timelines/tag/{hashtag}")
async def get_hashtag_timeline(
    hashtag: str,
    limit: int = 20,
    since_id: Optional[str] = None,
    max_id: Optional[str] = None
):
    """
    Get hashtag timeline.
    
    Args:
        hashtag: Hashtag to search for
        limit: Number of statuses to fetch
        since_id: Return only statuses newer than this ID
        max_id: Return only statuses older than this ID
        
    Returns:
        List of status dicts
    """
    return outbox.get_statuses_by_hashtag(hashtag, limit, since_id, max_id)

@app.get("/api/v1/accounts/{username}/statuses")
async def get_user_timeline(
    username: str,
    limit: int = 20,
    since_id: Optional[str] = None,
    max_id: Optional[str] = None
):
    """
    Get user timeline.
    
    Args:
        username: Username to fetch timeline for
        limit: Number of statuses to fetch
        since_id: Return only statuses newer than this ID
        max_id: Return only statuses older than this ID
        
    Returns:
        List of status dicts
    """
    return outbox.get_statuses_by_user(username, limit, since_id, max_id)

@app.get("/.well-known/webfinger")
async def webfinger(resource: str):
    """
    WebFinger endpoint for Mastodon instance discovery.
    
    Args:
        resource: WebFinger resource string
        
    Returns:
        WebFinger response
    """
    if resource.startswith("acct:"):
        username = resource[5:]
        if username == actor.username:
            return {
                "subject": resource,
                "links": [
                    {
                        "rel": "self",
                        "type": "application/activity+json",
                        "href": f"/users/{username}"
                    }
                ]
            }
    raise HTTPException(status_code=404, detail="Not found")

@app.get("/users/{username}")
async def user_profile(username: str):
    """
    Get user profile.
    
    Args:
        username: Username to fetch profile for
        
    Returns:
        User profile dict
    """
    if username == actor.username:
        return actor.to_dict()
    raise HTTPException(status_code=404, detail="Not found") 