"""
Mastodon Test Server

Simulates a Mastodon server for testing client interactions
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

app = FastAPI()

# Test data storage
test_users: Dict[str, Dict[str, Any]] = {}
test_statuses: List[Dict[str, Any]] = []
test_hashtags: Dict[str, List[str]] = {}

def create_test_data():
    """Create initial test data."""
    # Create test users
    test_users["beebo"] = {
        "id": "1",
        "username": "beebo",
        "acct": "beebo@test.mastodon",
        "display_name": "Beebo Baggins",
        "locked": False,
        "bot": False,
        "discoverable": True,
        "group": False,
        "created_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
        "note": "Just a test user",
        "url": "https://test.mastodon/@beebo",
        "avatar": None,
        "avatar_static": None,
        "header": None,
        "header_static": None,
        "followers_count": 100,
        "following_count": 50,
        "statuses_count": 20,
        "last_status_at": datetime.utcnow().isoformat(),
        "emojis": [],
        "fields": [],
        "source": {
            "privacy": "public",
            "sensitive": False,
            "language": "en",
            "note": "Just a test user",
            "fields": [],
            "follow_requests_count": 0
        }
    }
    
    # Create test statuses
    for i in range(10):
        status_id = str(uuid.uuid4())
        created_at = datetime.utcnow() - timedelta(hours=i)
        status = {
            "id": status_id,
            "uri": f"https://test.mastodon/statuses/{status_id}",
            "url": f"https://test.mastodon/@beebo/statuses/{status_id}",
            "content": f"Test status {i}",
            "text": f"Test status {i}",
            "created_at": created_at.isoformat(),
            "account": test_users["beebo"],
            "media_attachments": [],
            "emojis": [],
            "tags": [],
            "visibility": "public",
            "favourited": False,
            "reblogged": False,
            "muted": False,
            "bookmarked": False,
            "pinned": False
        }
        test_statuses.append(status)
    
    # Create test hashtags
    test_hashtags["python"] = [
        status for status in test_statuses 
        if "python" in status["content"].lower()
    ]

@app.on_event("startup")
async def startup_event():
    """Initialize test data on server startup."""
    create_test_data()

@app.get("/.well-known/webfinger")
async def webfinger(resource: str):
    """Webfinger protocol implementation."""
    username = resource.split(":")[1].split("@")[0]
    if username in test_users:
        return {
            "subject": resource,
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": f"https://test.mastodon/users/{username}"
                }
            ]
        }
    raise HTTPException(status_code=404, detail="Resource not found")

@app.get("/api/v1/accounts/{username}")
async def get_account(username: str):
    """Get account information."""
    if username in test_users:
        return test_users[username]
    raise HTTPException(status_code=404, detail="Account not found")

@app.get("/api/v1/statuses")
async def get_statuses():
    """Get all statuses."""
    return test_statuses

@app.get("/api/v1/timelines/public")
async def get_public_timeline(
    limit: int = 20,
    max_id: Optional[str] = None,
    since_id: Optional[str] = None,
    local: bool = False
):
    """Get public timeline."""
    statuses = test_statuses
    if max_id:
        statuses = [s for s in statuses if s["id"] < max_id]
    if since_id:
        statuses = [s for s in statuses if s["id"] > since_id]
    return statuses[:limit]

@app.get("/api/v1/timelines/tag/{hashtag}")
async def get_hashtag_timeline(
    hashtag: str,
    limit: int = 20,
    max_id: Optional[str] = None,
    since_id: Optional[str] = None,
    local: bool = False
):
    """Get hashtag timeline."""
    if hashtag in test_hashtags:
        statuses = test_hashtags[hashtag]
        if max_id:
            statuses = [s for s in statuses if s["id"] < max_id]
        if since_id:
            statuses = [s for s in statuses if s["id"] > since_id]
        return statuses[:limit]
    return []

@app.post("/api/v1/statuses")
async def create_status(request: Request):
    """Create a new status."""
    form_data = await request.form()
    content = form_data.get("status", "")
    media_ids = form_data.getlist("media_ids[]")
    
    status_id = str(uuid.uuid4())
    status = {
        "id": status_id,
        "uri": f"https://test.mastodon/statuses/{status_id}",
        "url": f"https://test.mastodon/@beebo/statuses/{status_id}",
        "content": content,
        "text": content,
        "created_at": datetime.utcnow().isoformat(),
        "account": test_users["beebo"],
        "media_attachments": [
            {"id": media_id, "type": "image", "url": f"https://test.mastodon/media/{media_id}"}
            for media_id in media_ids
        ],
        "emojis": [],
        "tags": [],
        "visibility": "public",
        "favourited": False,
        "reblogged": False,
        "muted": False,
        "bookmarked": False,
        "pinned": False
    }
    
    test_statuses.insert(0, status)
    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8081) 