"""
ActivityPub POC

Sets up an ActivityPub server with a local domain and hosts a single Actor.
This server has the ability to receive text-based post uploads from the Actor in its outbox.

Adapted from: https://blog.joinmastodon.org/2018/06/how-to-implement-a-basic-activitypub-server/
"""

import datetime
import uuid
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from typing import Optional
from PIL import Image
import aiofiles

# Import our modules
from .actor import ActorManager
from .inbox_outbox import InboxOutboxManager
from .signature import generate_http_signature

# Server configuration
LOCAL_DOMAIN = "127.0.0.1:8080"
ACTOR_NAME = "beebo"
DISPLAY_NAME = "Beebo Baggins"

# Media storage configuration
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

# Create actor and inbox/outbox managers
actor_id = f"https://{LOCAL_DOMAIN}/users/{ACTOR_NAME}"
actor_manager = ActorManager(LOCAL_DOMAIN, ACTOR_NAME, DISPLAY_NAME, public_key_pem)
inbox_outbox_manager = InboxOutboxManager(actor_id, ACTOR_NAME, LOCAL_DOMAIN, private_key)

############################################
# ActivityPub endpoints
############################################

async def send_text_post(content: str):
    """Creates and sends a text-based post (Create activity)"""
    post_id = f"{actor_id}/post/example-post"
    activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": post_id,
        "type": "Create",
        "actor": actor_id,
        "object": {
            "id": post_id,
            "type": "Note",
            "content": content,
            "published": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "attributedTo": actor_id,
            "to": ["https://www.w3.org/ns/activitystreams#Public"]  # everyone can see
        }
    }

    # Send the activity to the outbox
    response = await inbox_outbox_manager.handle_outbox(activity)
    
    return activity

async def upload_media(file_data: bytes, filename: str, content_type: str):
    """
    Handle media upload according to ActivityPub protocol
    
    Args:
        file_data: Binary data of the file
        filename: Name of the file
        content_type: MIME type of the file
        
    Returns:
        URL to the uploaded media
    """
    # Generate a unique ID for the media
    media_id = str(uuid.uuid4())
    
    # Create directory for this media item
    media_path = os.path.join(MEDIA_DIR, media_id)
    os.makedirs(media_path, exist_ok=True)
    
    # Save the file
    file_path = os.path.join(media_path, filename)
    with open(file_path, "wb") as f:
        f.write(file_data)
    
    # Return a URL that would serve this file
    media_url = f"https://{LOCAL_DOMAIN}/media/{media_id}/{filename}"
    
    return {
        "id": f"{actor_id}/media/{media_id}",
        "url": media_url,
        "mediaType": content_type
    }

async def send_check_in(content: str, latitude: float, longitude: float, image_data, location_name: Optional[str] = None):
    """
    Creates and sends a check-in post with location and image (Create activity)
    
    Args:
        content: Text content of the check-in
        latitude: GPS latitude coordinate
        longitude: GPS longitude coordinate
        image_data: Dictionary with image information (from upload_media)
        location_name: Optional name of the location
    """
    # Generate a unique ID for this post
    post_uuid = str(uuid.uuid4())
    post_id = f"{actor_id}/post/{post_uuid}"
    
    # Create the location object
    location = {
        "type": "Place",
        "longitude": longitude,
        "latitude": latitude
    }
    
    # Add location name if provided
    if location_name:
        location["name"] = location_name
    
    # Create the full activity
    activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": post_id,
        "type": "Create",
        "actor": actor_id,
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "object": {
            "type": "Note",
            "id": f"{post_id}/object",
            "content": content,
            "published": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "attributedTo": actor_id,
            "location": location,
            "attachment": [
                {
                    "type": "Image",
                    "id": image_data["id"],
                    "url": image_data["url"],
                    "mediaType": image_data["mediaType"]
                }
            ],
            "to": ["https://www.w3.org/ns/activitystreams#Public"]
        }
    }

    # Send the activity to the outbox
    response = await inbox_outbox_manager.handle_outbox(activity)
    
    return activity

async def test_activitypub():
    """Test ActivityPub functionality after server is ready."""
    try:
        print("\nTesting ActivityPub functionality...")
        # Create a test post
        activity = await send_text_post("Hello ActivityPub!")
        print("Post created successfully!")
        
        # Check outbox
        print("\nChecking outbox...")
        response = await inbox_outbox_manager.handle_outbox_get()
        print("Outbox content retrieved successfully!")
        
        # Upload a test media file
        try:
            media_file = b"Hello World!"
            filename = "test.txt"
            content_type = "text/plain"
            image_data = await upload_media(media_file, filename, content_type)
            print("Media file uploaded successfully!")
            
            # Create a test check-in post
            activity = await send_check_in("Checking in at The Shire", 37.7749, -122.4194, image_data, "The Shire")
            print("Check-in post created successfully!")
        except Exception as e:
            print(f"Media/check-in test error: {e}")
    except Exception as e:
        print(f"Test error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    
    # Run test after server is ready
    await test_activitypub()
    
    # Shutdown
    print("Shutting down...")

# Create the FastAPI app
app = FastAPI(lifespan=lifespan)

# Mount static files directory for serving media
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# Register routes
actor_manager.register_routes(app)
inbox_outbox_manager.register_routes(app)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)