"""
Mastodon Client Module

Handles interactions with Mastodon instances
"""

import httpx
from typing import Dict, Any, Optional, List
import json
from datetime import datetime
from urllib.parse import urlencode, urlparse

from .client_signature import generate_client_signature

class MastodonClient:
    def __init__(self, instance_url: str = "https://mastodon.social", 
                 private_key: Any = None,
                 key_id: str = None,
                 domain: str = None):
        """Initialize the Mastodon client.
        
        Args:
            instance_url: URL of the Mastodon instance
            private_key: RSA private key for signing requests
            key_id: The key ID (usually actor URL + #main-key)
            domain: The client's domain
        """
        self.instance_url = instance_url
        self.private_key = private_key
        self.key_id = key_id
        self.domain = domain
        self.client = httpx.Client()
    
    async def get_actor(self, username: str) -> Dict[str, Any]:
        """Fetch actor information from a Mastodon instance."""
        # First try webfinger
        webfinger_url = f"{self.instance_url}/.well-known/webfinger"
        params = {"resource": f"acct:{username}@{self.instance_url.replace('https://', '')}"}
        
        async with httpx.AsyncClient() as client:
            print(f"[Debug] Requesting Webfinger: {webfinger_url} with params {params}") # Debug
            response = await client.get(webfinger_url, params=params)
            print(f"[Debug] Webfinger Response Status: {response.status_code}") # Debug
            if response.status_code != 200:
                print(f"[Debug] Webfinger Response Body: {response.text}") # Debug
                raise Exception(f"Failed to fetch actor via Webfinger: {response.status_code}")
            
            webfinger_data = response.json()
            print(f"[Debug] Webfinger Response Data: {webfinger_data}") # Debug
            
            try:
                actor_url = next(link["href"] for link in webfinger_data["links"] 
                               if link["rel"] == "self" and link["type"] == "application/activity+json")
            except StopIteration:
                print("[Debug] Could not find ActivityPub link in Webfinger response") # Debug
                raise Exception("Could not find ActivityPub link in Webfinger response")
                
            print(f"[Debug] Found Actor URL: {actor_url}") # Debug
            
            # Now fetch the actor data with correct Accept header
            actor_headers = {
                'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams", application/activity+json'
            }
            # Add signature headers only if credentials are provided
            if self.private_key and self.key_id and self.domain:
                parsed_url = urlparse(actor_url)
                path = parsed_url.path
                if parsed_url.query:
                    path += "?" + parsed_url.query
                    
                signature_headers = generate_client_signature(
                    method="GET",
                    path=path, 
                    body=b"",
                    private_key=self.private_key,
                    key_id=self.key_id,
                    domain=self.domain
                )
                actor_headers.update(signature_headers)

            print(f"[Debug] Requesting Actor URL: {actor_url} with headers {actor_headers}") # Debug
            response = await client.get(actor_url, headers=actor_headers) # Pass headers here
            print(f"[Debug] Actor Response Status: {response.status_code}") # Debug
            if response.status_code != 200:
                print(f"[Debug] Actor Response Body: {response.text}") # Debug
                raise Exception(f"Failed to fetch actor data: {response.status_code}")
            
            return response.json()
    
    async def _get_account_id_from_username(self, username: str) -> str:
        """Lookup Mastodon account ID via API."""
        # Username should be in format user@domain
        if '@' not in username:
            # Assume it's a local user on the instance_url
            domain = urlparse(self.instance_url).netloc
            acct = f"{username}@{domain}"
        else:
            acct = username
            
        lookup_url = f"{self.instance_url}/api/v1/accounts/lookup"
        params = {"acct": acct}
        
        async with httpx.AsyncClient() as client:
            print(f"[Debug] Requesting Account Lookup: {lookup_url} with params {params}") # Debug
            # No signature needed for public lookup typically
            response = await client.get(lookup_url, params=params, follow_redirects=True)
            print(f"[Debug] Account Lookup Response Status: {response.status_code}") # Debug
            if response.status_code != 200:
                print(f"[Debug] Account Lookup Response Body: {response.text}") # Debug
                raise Exception(f"Failed to lookup account ID: {response.status_code}")
            
            account_data = response.json()
            print(f"[Debug] Account Lookup Response Data: {account_data}") # Debug
            account_id = account_data.get("id")
            if not account_id:
                raise Exception("Could not find account ID in lookup response")
            return account_id

    async def create_note(self, content: str, 
                         media_ids: Optional[list[str]] = None,
                         location: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Create a note with optional media and location."""
        note = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Note",
            "content": content,
            "published": datetime.utcnow().isoformat(),
        }
        
        if media_ids:
            note["attachment"] = [
                {"type": "Image", "url": media_id} for media_id in media_ids
            ]
        
        if location:
            note["location"] = {
                "type": "Place",
                "name": "Location",
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "accuracy": 0.0,
                "units": "m"
            }
        
        return note

    async def get_user_timeline(self, username: str, 
                              limit: int = 20,
                              max_id: Optional[str] = None,
                              since_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch a user's timeline from their outbox."""
        # --- OLD METHOD (Using ActivityPub Outbox - often restricted) ---
        # actor = await self.get_actor(username)
        # outbox_url = actor.get("outbox")
        # 
        # if not outbox_url:
        #     raise Exception("Actor has no outbox URL")
        # path = f"{outbox_url}?{urlencode(params)}"
        
        # --- NEW METHOD (Using Mastodon API) ---
        try:
            # Username format for lookup is user@domain or just user for local instance
            account_id = await self._get_account_id_from_username(username)
            print(f"[Debug] Found Account ID: {account_id} for user {username}")
        except Exception as e:
             print(f"[Debug] Failed to get account ID for {username}: {e}")
             # Fallback or re-raise? For now, let's re-raise.
             raise Exception(f"Could not get Mastodon account ID for {username}: {e}") from e

        params = {
            "limit": limit
        }
        if max_id:
            params["max_id"] = max_id
        if since_id:
            params["since_id"] = since_id
            
        # Use the Mastodon API endpoint
        timeline_url = f"{self.instance_url}/api/v1/accounts/{account_id}/statuses"
        path = f"{timeline_url}?{urlencode(params)}" # Path needed for signing if enabled
        body = b""
        
        # Generate signature headers if credentials are provided
        headers = {}
        if self.private_key and self.key_id and self.domain:
            headers = generate_client_signature(
                method="GET",
                path=path,
                body=body,
                private_key=self.private_key,
                key_id=self.key_id,
                domain=self.domain
            )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(path, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch timeline: {response.status_code}")
            
            return response.json()

    async def get_public_timeline(self,
                                limit: int = 20,
                                max_id: Optional[str] = None,
                                since_id: Optional[str] = None,
                                local: bool = False) -> Dict[str, Any]:
        """Fetch the public timeline."""
        params = {
            "limit": limit,
            "local": str(local).lower()
        }
        if max_id:
            params["max_id"] = max_id
        if since_id:
            params["since_id"] = since_id
            
        path = f"{self.instance_url}/api/v1/timelines/public?{urlencode(params)}"
        body = b""
        
        # Generate signature headers if credentials are provided
        headers = {}
        if self.private_key and self.key_id and self.domain:
            headers = generate_client_signature(
                method="GET",
                path=path,
                body=body,
                private_key=self.private_key,
                key_id=self.key_id,
                domain=self.domain
            )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(path, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch public timeline: {response.status_code}")
            
            return response.json()

    async def get_hashtag_timeline(self, hashtag: str,
                                 limit: int = 20,
                                 max_id: Optional[str] = None,
                                 since_id: Optional[str] = None,
                                 local: bool = False) -> Dict[str, Any]:
        """Fetch the timeline for a specific hashtag."""
        params = {
            "limit": limit,
            "local": str(local).lower()
        }
        if max_id:
            params["max_id"] = max_id
        if since_id:
            params["since_id"] = since_id
            
        path = f"{self.instance_url}/api/v1/timelines/tag/{hashtag}?{urlencode(params)}"
        body = b""
        
        # Generate signature headers if credentials are provided
        headers = {}
        if self.private_key and self.key_id and self.domain:
            headers = generate_client_signature(
                method="GET",
                path=path,
                body=body,
                private_key=self.private_key,
                key_id=self.key_id,
                domain=self.domain
            )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(path, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch hashtag timeline: {response.status_code}")
            
            return response.json()

    def parse_timeline(self, timeline_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse timeline data into a consistent format."""
        parsed_posts = []
        
        # Handle both ActivityPub collections and Mastodon API responses
        items = timeline_data.get("orderedItems", timeline_data)
        
        for item in items:
            # Handle both ActivityPub activities and Mastodon statuses
            if isinstance(item, dict):
                if item.get("type") == "Create":
                    # ActivityPub format
                    note = item.get("object", {})
                    parsed_posts.append({
                        "id": note.get("id"),
                        "content": note.get("content"),
                        "author": item.get("actor"),
                        "published": note.get("published"),
                        "attachments": note.get("attachment", []),
                        "location": note.get("location"),
                        "tags": note.get("tag", [])
                    })
                else:
                    # Mastodon API format
                    parsed_posts.append({
                        "id": item.get("id"),
                        "content": item.get("content"),
                        "author": item.get("account"),
                        "published": item.get("created_at"),
                        "attachments": item.get("media_attachments", []),
                        "location": item.get("location"),
                        "tags": item.get("tags", [])
                    })
        
        return parsed_posts 