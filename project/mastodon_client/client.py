"""
Mastodon API Client Implementation

This module implements a Mastodon API client that can:
1. Fetch public timelines
2. Search for hashtags
3. Get user timelines
4. Upload media
5. Create statuses with GPS coordinates
6. Handle HTTP signatures for authentication

The client uses aiohttp for async HTTP requests and implements proper
HTTP signature generation for Mastodon API authentication.
"""

import aiohttp
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
from pathlib import Path
from urllib.parse import urljoin

from .signature import generate_client_signature

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MastodonClient:
    """Client for interacting with Mastodon API."""
    
    def __init__(
        self,
        instance_url: str,
        private_key: str,
        key_id: str,
        domain: str,
        user_agent: str = "MastodonClient/1.0"
    ):
        """
        Initialize Mastodon client.
        
        Args:
            instance_url: Base URL of the Mastodon instance
            private_key: Private key for signing requests
            key_id: Key ID for signing requests
            domain: Domain for signing requests
            user_agent: User agent string for requests
        """
        self.instance_url = instance_url.rstrip('/')
        self.private_key = private_key
        self.key_id = key_id
        self.domain = domain
        self.user_agent = user_agent
        self.session = None
        
    async def __aenter__(self):
        """Create aiohttp session when entering context."""
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': self.user_agent}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close aiohttp session when exiting context."""
        if self.session:
            await self.session.close()
            
    def _get_signature_headers(
        self,
        method: str,
        path: str,
        body: Optional[bytes] = None
    ) -> Dict[str, str]:
        """
        Generate HTTP signature headers for request.
        
        Args:
            method: HTTP method
            path: Request path
            body: Optional request body
            
        Returns:
            Dict containing signature headers
        """
        return generate_client_signature(
            method=method,
            path=path,
            body=body,
            private_key=self.private_key,
            key_id=self.key_id,
            domain=self.domain
        )
        
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None
    ) -> Dict:
        """
        Make authenticated request to Mastodon API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Form data
            files: File uploads
            
        Returns:
            API response as dict
        """
        if not self.session:
            raise RuntimeError("Client must be used as async context manager")
            
        url = urljoin(self.instance_url, endpoint)
        
        # Prepare request data
        body = None
        if data:
            body = json.dumps(data).encode()
            
        # Generate signature headers
        headers = self._get_signature_headers(method, endpoint, body)
        
        # Make request
        async with self.session.request(
            method,
            url,
            params=params,
            data=data,
            files=files,
            headers=headers
        ) as response:
            response.raise_for_status()
            return await response.json()
            
    async def get_public_timeline(
        self,
        limit: int = 20,
        since_id: Optional[str] = None,
        max_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get public timeline.
        
        Args:
            limit: Number of statuses to fetch
            since_id: Return only statuses newer than this ID
            max_id: Return only statuses older than this ID
            
        Returns:
            List of status dicts
        """
        params = {'limit': limit}
        if since_id:
            params['since_id'] = since_id
        if max_id:
            params['max_id'] = max_id
            
        return await self._make_request(
            'GET',
            '/api/v1/timelines/public',
            params=params
        )
        
    async def search_hashtag(
        self,
        hashtag: str,
        limit: int = 20,
        since_id: Optional[str] = None,
        max_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for hashtag.
        
        Args:
            hashtag: Hashtag to search for
            limit: Number of statuses to fetch
            since_id: Return only statuses newer than this ID
            max_id: Return only statuses older than this ID
            
        Returns:
            List of status dicts
        """
        params = {'limit': limit}
        if since_id:
            params['since_id'] = since_id
        if max_id:
            params['max_id'] = max_id
            
        return await self._make_request(
            'GET',
            f'/api/v1/timelines/tag/{hashtag}',
            params=params
        )
        
    async def get_user_timeline(
        self,
        username: str,
        limit: int = 20,
        since_id: Optional[str] = None,
        max_id: Optional[str] = None
    ) -> List[Dict]:
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
        params = {'limit': limit}
        if since_id:
            params['since_id'] = since_id
        if max_id:
            params['max_id'] = max_id
            
        return await self._make_request(
            'GET',
            f'/api/v1/accounts/{username}/statuses',
            params=params
        )
        
    async def upload_media(
        self,
        file_path: Union[str, Path],
        description: Optional[str] = None
    ) -> Dict:
        """
        Upload media file.
        
        Args:
            file_path: Path to media file
            description: Optional media description
            
        Returns:
            Media attachment dict
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")
            
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'image/jpeg')}
            data = {'description': description} if description else None
            
            return await self._make_request(
                'POST',
                '/api/v1/media',
                files=files,
                data=data
            )
            
    async def create_status(
        self,
        status: str,
        media_ids: Optional[List[str]] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict:
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
        data = {'status': status}
        if media_ids:
            data['media_ids'] = media_ids
        if latitude is not None:
            data['latitude'] = latitude
        if longitude is not None:
            data['longitude'] = longitude
            
        return await self._make_request(
            'POST',
            '/api/v1/statuses',
            data=data
        ) 