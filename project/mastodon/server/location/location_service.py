#!/usr/bin/env python3
"""
Location service for handling geolocation functionality.
This module provides functions for searching places using the geopy library.
"""

import asyncio
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from typing import Dict, Optional, Union

class LocationService:
    """Service for handling geolocation functionality."""
    
    def __init__(self):
        """Initialize the location service with a geocoder."""
        self.geocoder = Nominatim(user_agent="mastodon_location_service")
    
    async def search_place(self, query: str) -> Optional[Dict[str, Union[str, float, Dict]]]:
        """
        Search for a place by name or address.
        
        Args:
            query: The place name or address to search for.
            
        Returns:
            A dictionary containing place information or None if not found.
        """
        try:
            # Run geocoding in a thread pool to avoid blocking
            location = await asyncio.get_event_loop().run_in_executor(
                None, self.geocoder.geocode, query
            )
            
            if location:
                return {
                    'name': location.address,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'raw': location.raw
                }
            return None
            
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            print(f"Geocoding error: {e}")
            return None 