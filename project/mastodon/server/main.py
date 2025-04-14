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
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from pathlib import Path
import uvicorn
import re
from jose import JWTError, jwt

from signature import verify_server_signature
from actor import Actor
from inbox_outbox import Inbox, Outbox
from database import db

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

# Add JWT configuration
SECRET_KEY = "your-secret-key"  # In production, use a secure secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        user = db.get_user(username)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

class StatusCreate(BaseModel):
    """Model for status creation request."""
    status: str
    media_ids: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    visibility: str = "public"

class AccountCreate(BaseModel):
    """Model for account creation request."""
    username: str
    password: str
    email: str

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
        "statuses_count": len(db.get_user_statuses(user['id'])) if 'id' in user else 0,
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
        if status.media_ids:
            for media_id in status.media_ids:
                media_path = MEDIA_DIR / f"{media_id}.jpg"
                if media_path.exists():
                    db.create_media_attachment(
                        status_id=db_status['id'],
                        file_path=f"/media/{media_path.name}",
                        file_type="image/jpeg",
                        description=""
                    )
        
        # Create response in Mastodon format
        status_data = {
            "id": db_status['id'],
            "created_at": db_status['created_at'].isoformat(),
            "content": db_status['content'],
            "visibility": db_status['visibility'],
            "sensitive": db_status['sensitive'],
            "spoiler_text": db_status['spoiler_text'] or "",
            "account": {
                "id": f"/users/{current_user['username']}",
                "username": current_user['username'],
                "acct": current_user['username'],
                "display_name": current_user['display_name'] or current_user['username'],
                "locked": False,
                "bot": False,
                "discoverable": True,
                "group": False,
                "created_at": current_user['created_at'].isoformat(),
                "note": current_user['bio'] or "",
                "url": f"https://example.com/users/{current_user['username']}",
                "avatar": current_user['avatar_url'] or "https://example.com/avatar.jpg",
                "avatar_static": current_user['avatar_url'] or "https://example.com/avatar.jpg",
                "header": current_user['header_url'] or "https://example.com/header.jpg",
                "header_static": current_user['header_url'] or "https://example.com/header.jpg",
                "followers_count": len(db.get_followers(current_user['id'])),
                "following_count": len(db.get_following(current_user['id'])),
                "statuses_count": len(db.get_user_statuses(current_user['id'])),
                "last_status_at": None,
                "emojis": [],
                "fields": []
            },
            "media_attachments": [],
            "location": None
        }
        
        # Add location if present
        if db_status['latitude'] is not None and db_status['longitude'] is not None:
            status_data["location"] = {
                "name": f"{db_status['latitude']}, {db_status['longitude']}",
                "type": "Point",
                "coordinates": [db_status['longitude'], db_status['latitude']]
            }
            
        # Get media attachments
        media_attachments = db.get_status_media(db_status['id'])
        status_data["media_attachments"] = [
            {
                "id": media['id'],
                "type": media['file_type'],
                "url": media['file_path'],
                "preview_url": media['file_path'],
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
        List of status dicts
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
                        "url": media['file_path'],
                        "preview_url": media['file_path'],
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

@app.get("/api/v1/accounts/{username}")
async def get_account(username: str):
    """
    Get account information.
    
    Args:
        username: Username to fetch account for
        
    Returns:
        Account dict
    """
    user = db.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="Not Found")
        
    return format_account(user)

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
        user = db.get_user(username)
        if user:
            return {
                "subject": resource,
                "links": [
                    {
                        "rel": "self",
                        "type": "application/activity+json",
                        "href": f"/api/v1/accounts/{username}"
                    }
                ]
            }
    raise HTTPException(status_code=404, detail="Not found")

@app.post("/api/v1/accounts")
async def create_account(account: AccountCreate):
    """
    Create new account.
    
    Args:
        account: Account creation data
        
    Returns:
        Created account dict
    """
    try:
        # Create user in database
        user = db.create_user(
            username=account.username,
            password=account.password,
            display_name=account.username,
            bio="",
            avatar_url=None,
            header_url=None
        )
        
        if not user:
            raise HTTPException(status_code=400, detail="Username already taken")
            
        return format_account(user)
        
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add server startup code
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 