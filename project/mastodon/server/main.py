"""
Mastodon Server Implementation

This module implements a Mastodon-compatible server using FastAPI.
It provides endpoints for:
1. Media uploads
2. Status creation with location check-ins
3. Timeline fetching
4. HTTP signature verification
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import uvicorn
import re
from jose import JWTError, jwt
import uuid

from server.activitypub import Actor, Inbox, Outbox, verify_server_signature
from server.database import db
from server.auth import Token, LoginRequest, AccountCreate, create_access_token, get_current_user
from server.location import LocationService

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

# Mount media directory
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# Initialize components
actor = Actor()
inbox = Inbox()
outbox = Outbox()
location_service = LocationService()

class StatusCreate(BaseModel):
    """Model for status creation request."""
    status: str
    media_ids: Optional[List[str]] = None
    media_ids_: Optional[List[str]] = Field(None, alias="media_ids[]")  # Add support for media_ids[] format
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_name: Optional[str] = None
    visibility: str = "public"

def format_account(user: dict) -> dict:
    """
    Format user data into a Mastodon account object.
    
    Args:
        user: User data from database
        
    Returns:
        Formatted account dict
    """
    return {
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
        "followers_count": len(db.get_followers(user['id'])) if 'id' in user else 0,
        "following_count": len(db.get_following(user['id'])) if 'id' in user else 0,
        "statuses_count": len(db.get_user_statuses(user['id'], limit=20, since_id=None, max_id=None)) if 'id' in user else 0,
        "last_status_at": None,
        "emojis": [],
        "fields": []
    }

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
        # Generate a unique ID for the media
        media_id = str(uuid.uuid4())
        
        # Save file with the media_id as the filename
        file_extension = os.path.splitext(file.filename)[1]
        file_path = MEDIA_DIR / f"{media_id}{file_extension}"
        
        # Ensure media directory exists
        os.makedirs(MEDIA_DIR, exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # Create media attachment in the database without a status_id
        attachment = db.create_media_attachment(
            file_path=f"/media/{file_path.name}",
            file_type=file.content_type or "image/jpeg",
            description=description
        )
        
        if not attachment:
            raise HTTPException(status_code=500, detail="Failed to create media attachment")
        
        # Return response in Mastodon format
        return {
            "id": attachment['id'],
            "type": "image",
            "url": f"/media/{file_path.name}",
            "preview_url": f"/media/{file_path.name}",
            "remote_url": None,
            "text_url": None,
            "description": description,
            "blurhash": None
        }
        
    except Exception as e:
        logger.error(f"Error uploading media: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/token", response_model=Token)
async def login(login_data: LoginRequest):
    """Login endpoint to get access token."""
    user = db.verify_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user['username']}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/statuses")
async def create_status(
    status: StatusCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create new status.
    
    Args:
        status: Status creation data
        current_user: Currently authenticated user
        
    Returns:
        Created status dict
    """
    try:
        # If place_name is provided but coordinates are not, search for the place
        if status.place_name and (status.latitude is None or status.longitude is None):
            logger.info(f"Searching for place: {status.place_name}")
            place = await location_service.search_place(status.place_name)
            
            if place:
                status.latitude = place['latitude']
                status.longitude = place['longitude']
                # Update place_name with the full address from the search
                status.place_name = place['name']
                logger.info(f"Found coordinates for {status.place_name}: {status.latitude}, {status.longitude}")
            else:
                logger.warning(f"Could not find coordinates for place: {status.place_name}")
        
        # Create status in database directly
        db_status = db.create_status(
            user_id=current_user['id'],
            content=status.status,
            visibility=status.visibility,
            sensitive=False,
            spoiler_text="",
            latitude=status.latitude,
            longitude=status.longitude
        )
        
        if not db_status:
            raise HTTPException(status_code=500, detail="Failed to create status")
            
        # Extract and add hashtags
        hashtags = re.findall(r'#(\w+)', status.status)
        for hashtag_name in hashtags:
            hashtag = db.create_hashtag(hashtag_name)
            if hashtag:
                db.link_status_to_hashtag(db_status['id'], hashtag['id'])
                
        # Add media attachments if present
        media_ids = status.media_ids or status.media_ids_  # Try both formats
        if media_ids:
            for media_id in media_ids:
                # Update the media attachment with the new status ID
                updated_media = db.update_media_status(media_id, db_status['id'])
                if not updated_media:
                    logger.warning(f"Could not update media attachment {media_id} with status {db_status['id']}")
                    
        # Create response in Mastodon format
        status_data = {
            "id": db_status['id'],
            "created_at": db_status['created_at'].isoformat(),
            "content": db_status['content'],
            "visibility": db_status['visibility'],
            "sensitive": db_status['sensitive'],
            "spoiler_text": db_status['spoiler_text'] or "",
            "account": format_account(current_user),
            "media_attachments": [],
            "mentions": [],
            "tags": [],
            "emojis": [],
            "reblogs_count": 0,
            "favourites_count": 0,
            "reblogged": False,
            "favourited": False,
            "muted": False,
            "bookmarked": False,
            "pinned": False
        }
        
        # Add location if present
        if db_status['latitude'] is not None and db_status['longitude'] is not None:
            # Get place name from coordinates using search_place
            location_info = await location_service.search_place(f"{db_status['latitude']}, {db_status['longitude']}")
            
            status_data["check_in"] = {
                "name": location_info['name'] if location_info else f"{db_status['latitude']}, {db_status['longitude']}",
                "latitude": db_status['latitude'],
                "longitude": db_status['longitude']
            }
            
        # Add media attachments
        media_attachments = db.get_status_media(db_status['id'])
        if media_attachments:
            status_data["media_attachments"] = [
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
            ]
        
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
        List of statuses
    """
    try:
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
                "account": format_account(user),
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
                "mentions": [],
                "tags": [],
                "emojis": [],
                "reblogs_count": 0,
                "favourites_count": 0,
                "reblogged": False,
                "favourited": False,
                "muted": False,
                "bookmarked": False,
                "pinned": False
            }
            
            # Add location if present
            if db_status['latitude'] is not None and db_status['longitude'] is not None:
                # Get place name from coordinates
                location_info = await location_service.get_location_info(
                    db_status['latitude'],
                    db_status['longitude']
                )
                
                status["location"] = {
                    "name": location_info['address'] if location_info else f"{db_status['latitude']}, {db_status['longitude']}",
                    "type": "Point",
                    "coordinates": [db_status['longitude'], db_status['latitude']]
                }
            
            statuses.append(status)
            
        return statuses
        
    except Exception as e:
        logger.error(f"Error getting public timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/timelines/tag/{hashtag}")
async def get_hashtag_timeline(
    hashtag: str,
    limit: int = 20,
    since_id: Optional[str] = None,
    max_id: Optional[str] = None
):
    """
    Get timeline for a hashtag.
    
    Args:
        hashtag: Hashtag to search for
        limit: Number of statuses to fetch
        since_id: Return only statuses newer than this ID
        max_id: Return only statuses older than this ID
        
    Returns:
        List of statuses
    """
    try:
        # Get statuses from database
        db_statuses = db.get_hashtag_timeline(hashtag, limit, since_id, max_id)
        
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
                "account": format_account(user),
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
                "mentions": [],
                "tags": [],
                "emojis": [],
                "reblogs_count": 0,
                "favourites_count": 0,
                "reblogged": False,
                "favourited": False,
                "muted": False,
                "bookmarked": False,
                "pinned": False
            }
            
            # Add location if present
            if db_status['latitude'] is not None and db_status['longitude'] is not None:
                # Get place name from coordinates
                location_info = await location_service.get_location_info(
                    db_status['latitude'],
                    db_status['longitude']
                )
                
                status["location"] = {
                    "name": location_info['address'] if location_info else f"{db_status['latitude']}, {db_status['longitude']}",
                    "type": "Point",
                    "coordinates": [db_status['longitude'], db_status['latitude']]
                }
            
            statuses.append(status)
            
        return statuses
        
    except Exception as e:
        logger.error(f"Error getting hashtag timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/accounts/{username}/statuses")
async def get_user_timeline(
    username: str,
    limit: int = 20,
    since_id: Optional[str] = None,
    max_id: Optional[str] = None
):
    """
    Get timeline for a user.
    
    Args:
        username: Username to fetch statuses for
        limit: Number of statuses to fetch
        since_id: Return only statuses newer than this ID
        max_id: Return only statuses older than this ID
        
    Returns:
        List of statuses
    """
    try:
        # Get user
        user = db.get_user(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Get statuses from database
        db_statuses = db.get_user_statuses(user['id'], limit, since_id, max_id)
        
        # Convert to Mastodon format
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
                "account": format_account(user),
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
                "mentions": [],
                "tags": [],
                "emojis": [],
                "reblogs_count": 0,
                "favourites_count": 0,
                "reblogged": False,
                "favourited": False,
                "muted": False,
                "bookmarked": False,
                "pinned": False
            }
            
            # Add location if present
            if db_status['latitude'] is not None and db_status['longitude'] is not None:
                # Get place name from coordinates
                location_info = await location_service.get_location_info(
                    db_status['latitude'],
                    db_status['longitude']
                )
                
                status["location"] = {
                    "name": location_info['address'] if location_info else f"{db_status['latitude']}, {db_status['longitude']}",
                    "type": "Point",
                    "coordinates": [db_status['longitude'], db_status['latitude']]
                }
            
            statuses.append(status)
            
        return statuses
        
    except Exception as e:
        logger.error(f"Error getting user timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/accounts/{username}")
async def get_account(username: str):
    """
    Get account information.
    
    Args:
        username: Username to fetch
        
    Returns:
        Account information
    """
    try:
        # Get user
        user = db.get_user(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Format account
        return format_account(user)
        
    except Exception as e:
        logger.error(f"Error getting account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/.well-known/webfinger")
async def webfinger(resource: str):
    """
    WebFinger endpoint for instance discovery.
    
    Args:
        resource: Resource to look up
        
    Returns:
        WebFinger response
    """
    try:
        # Parse resource
        if not resource.startswith("acct:"):
            raise HTTPException(status_code=400, detail="Invalid resource format")
            
        username, domain = resource[5:].split("@")
        
        # Get user
        user = db.get_user(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Create response
        return {
            "subject": resource,
            "aliases": [
                f"https://example.com/users/{username}",
                f"https://example.com/@{username}"
            ],
            "links": [
                {
                    "rel": "http://webfinger.net/rel/profile-page",
                    "type": "text/html",
                    "href": f"https://example.com/users/{username}"
                },
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": f"https://example.com/users/{username}"
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in WebFinger: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/accounts")
async def create_account(account: AccountCreate):
    """
    Create new account.
    
    Args:
        account: Account creation data
        
    Returns:
        Created account information
    """
    try:
        # Check if username exists
        existing_user = db.get_user(account.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
            
        # Create user
        user = db.create_user(
            username=account.username,
            password_hash=account.password,  # In production, hash the password
            email=account.email
        )
        
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")
            
        # Format account
        return format_account(user)
        
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 