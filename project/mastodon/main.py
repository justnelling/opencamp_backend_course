"""
Mastodon Server Module

Handles Mastodon-specific server functionality and API endpoints.
"""

import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import json
from PIL import Image
import aiofiles
import uuid
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from .client import MastodonClient

# Server configuration
LOCAL_DOMAIN = "127.0.0.1:8080"
MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# Generate cryptographic keys
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

public_key = private_key.public_key()
public_key_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

# Initialize Mastodon client with credentials
mastodon_client = MastodonClient(
    instance_url="https://mastodon.social",
    private_key=private_key,
    key_id=f"https://{LOCAL_DOMAIN}/users/beebo#main-key",
    domain=LOCAL_DOMAIN
)

# Create the FastAPI app
app = FastAPI()

# Mount static files directory for serving media
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

@app.post("/media")
async def upload_media(file: UploadFile = File(...)):
    """Handle media uploads."""
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(MEDIA_DIR, unique_filename)
    
    # Save the file
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    # Process image with Pillow
    with Image.open(file_path) as img:
        # Resize if too large (max 1200px)
        max_size = 1200
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            img.save(file_path, quality=85)
    
    # Create media URL
    media_url = f"/media/{unique_filename}"
    
    # Create ActivityPub media attachment
    attachment = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Image",
        "url": media_url,
        "mediaType": file.content_type,
        "name": file.filename
    }
    
    return JSONResponse(content=attachment)

@app.post("/status")
async def create_status(
    content: str = Form(...),
    media_ids: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None)
):
    """Create a new status with optional media and location."""
    # Parse media IDs if provided
    media_ids_list = json.loads(media_ids) if media_ids else None
    
    # Create location object if coordinates provided
    location = None
    if latitude is not None and longitude is not None:
        location = {
            "latitude": latitude,
            "longitude": longitude
        }
    
    # Create the note
    note = await mastodon_client.create_note(
        content=content,
        media_ids=media_ids_list,
        location=location
    )
    
    return JSONResponse(content=note)

@app.get("/timeline/user/{username}")
async def get_user_timeline(
    username: str,
    limit: int = 20,
    max_id: Optional[str] = None,
    since_id: Optional[str] = None
):
    """Fetch a user's timeline."""
    timeline = await mastodon_client.get_user_timeline(
        username=username,
        limit=limit,
        max_id=max_id,
        since_id=since_id
    )
    return mastodon_client.parse_timeline(timeline)

@app.get("/timeline/public")
async def get_public_timeline(
    limit: int = 20,
    max_id: Optional[str] = None,
    since_id: Optional[str] = None,
    local: bool = False
):
    """Fetch the public timeline."""
    timeline = await mastodon_client.get_public_timeline(
        limit=limit,
        max_id=max_id,
        since_id=since_id,
        local=local
    )
    return mastodon_client.parse_timeline(timeline)

@app.get("/timeline/hashtag/{hashtag}")
async def get_hashtag_timeline(
    hashtag: str,
    limit: int = 20,
    max_id: Optional[str] = None,
    since_id: Optional[str] = None,
    local: bool = False
):
    """Fetch the timeline for a specific hashtag."""
    timeline = await mastodon_client.get_hashtag_timeline(
        hashtag=hashtag,
        limit=limit,
        max_id=max_id,
        since_id=since_id,
        local=local
    )
    return mastodon_client.parse_timeline(timeline) 