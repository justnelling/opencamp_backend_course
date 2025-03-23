"""
ActivityPub POC

Sets up an ActivityPub server with a local domain and hosts a single Actor.
This server has the ability to receive text-based post uploads from the Actor in its outbox.

Adapted from: https://blog.joinmastodon.org/2018/06/how-to-implement-a-basic-activitypub-server/
"""

import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Import our modules
from actor import ActorManager
from inbox_outbox import InboxOutboxManager

# Server configuration
LOCAL_DOMAIN = "127.0.0.1:8080"
ACTOR_NAME = "beebo"
DISPLAY_NAME = "Beebo Baggins"

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

    # Directly update the last_activity in the inbox/outbox manager
    inbox_outbox_manager.last_activity = activity
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

# Register routes
actor_manager.register_routes(app)
inbox_outbox_manager.register_routes(app)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)