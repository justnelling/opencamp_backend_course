'''
ActivityPub POC

Sets up an ActivityPub server with a local domain and hosts a single Actor.

This server has the ability to receive text-based post uploads from the Actor in its outbox. 

Adapted the implementation from: https://blog.joinmastodon.org/2018/06/how-to-implement-a-basic-activitypub-server/
'''

import datetime
import hashlib
import base64
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding
from contextlib import asynccontextmanager

# Actor config (local)
local_domain = "127.0.0.1:8080"  # Match the port we're running on
actor_name = "beebo"
actor_id = f"https://{local_domain}/users/{actor_name}"
display_name = "Beebo Baggins"

# dummy db: var to store our post
last_activity = None

'''
Crytography setup

- AP uses public/private keys to sign and verify messages
- Messages are signed to verify authenticity of the sender
- Public key is shared with other servers 
- Private key is used to sign outgoing messages
'''
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

class Activity(BaseModel):
    type: str
    object: Optional[Dict[str, Any]] = None

async def generate_http_signature(request: Request, private_key, key_id: str) -> Dict[str, str]:
    """Generates a simplified HTTP Signature with basic padding."""
    
    headers_to_sign = ["(request-target)", "host", "date", "digest"]
    request_target = f"{request.method.lower()} {request.url.path}"
    host = request.headers.get("host", local_domain)
    date = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Calculate hash of the request body
    body = await request.body()
    sha256_hash = hashlib.sha256(body).digest()
    digest = f"SHA-256={base64.b64encode(sha256_hash).decode('utf-8')}"

    # Combine headers into a single signed string
    signed_string = f"(request-target): {request_target}\nhost: {host}\ndate: {date}\ndigest: {digest}"
    message = signed_string.encode("utf-8")

    # Sign the string with the private key 
    signature = private_key.sign(
        message,
        asymmetric_padding.PKCS1v15(), 
        hashes.SHA256(),  
    )

    signature_b64 = base64.b64encode(signature).decode("utf-8")
    headers = f'keyId="{key_id}",headers="{" ".join(headers_to_sign)}",signature="{signature_b64}"'

    return {"Date": date, "Digest": digest, "Signature": headers}

async def test_activitypub():
    """Test ActivityPub functionality after server is ready."""
    try:
        print("\nTesting ActivityPub functionality...")
        # Create a test post
        activity = await send_text_post("Hello ActivityPub!")
        print("Post created successfully!")
        
        # Check outbox
        print("\nChecking outbox...")
        response = await outbox_get()
        print(f"Outbox content retrieved successfully!")
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

@app.get(f"/users/{actor_name}")
async def actor():
    '''Returns the actor's profile'''
    actor_data = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1"
        ],
        "id": actor_id,
        "type": "Person",
        "name": display_name,
        "preferredUsername": actor_name,
        "inbox": f"{actor_id}/inbox",
        "outbox": f"{actor_id}/outbox",
        "publicKey": {
            "id": f"{actor_id}#main-key",
            "owner": actor_id,
            "publicKeyPem": public_key_pem
        }
    }
    return JSONResponse(content=actor_data)

@app.post(f"/users/{actor_name}/inbox")
async def inbox(activity: Activity):
    '''Handles incoming activities from rest of world -> our Actor'''
    if activity.type == 'Create':
        print(f"Received note: {activity.object['content']}")
        return JSONResponse(content={'message': 'Activity Received'}, status_code=202)
    else:
        raise HTTPException(status_code=400, detail='Activity type not supported')

@app.post(f"/users/{actor_name}/outbox")
async def outbox(request: Request):
    '''
    Handles outgoing activities from our Actor -> rest of the world
    +
    Defines activity created by our Actor in this server 
    '''
    activity = await request.json()

    # write to our dummy db
    global last_activity
    last_activity = activity

    headers = await generate_http_signature(request, private_key, f"{actor_id}#main-key")
    
    response = JSONResponse(
        content=activity,
        status_code=202,
    )
    for key, value in headers.items():
        response.headers[key] = value
    
    return response

@app.get(f"/users/{actor_name}/outbox")
async def outbox_get():
    '''Simulates fetching from outbox
    
    for simplicity we're just reading from `last_activity` global var instead of an actual DB
    '''
    global last_activity
    if last_activity:
        content = last_activity['object']['content']
        print("Content from outbox:", content)
        return JSONResponse(content=last_activity)
    else:
        raise HTTPException(status_code=404, detail='Outbox is empty')

@app.get("/.well-known/webfinger")
async def webfinger(resource: str):
    '''
    webfinger serves as a routing protocol / naming convention for activitypub

    This is the endpoint other servers would call to find our server's Actor / users
    '''
    if resource and resource == f"acct:{actor_name}@{local_domain}":
        webfinger_response = {
            'subject': resource,
            'links': [
                {
                    'rel': 'self',
                    'type': 'application/activity+json',
                    'href': actor_id
                }
            ],
        }
        return JSONResponse(content=webfinger_response)
    else:
        raise HTTPException(status_code=404, detail='Resource not found')

async def send_text_post(content: str):
    '''Creates and sends a text-based post (Create activity)'''
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

    # Directly update the global variable instead of making an HTTP request
    global last_activity
    last_activity = activity
    return activity


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)