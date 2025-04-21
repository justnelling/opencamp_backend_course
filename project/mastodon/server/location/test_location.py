"""
Test script for the location service.
"""

import asyncio
from location_service import LocationService

async def test_location_service():
    """Test the location service functionality."""
    location_service = LocationService()
    
    # Test place search
    print("\nTesting place search:")
    place = await location_service.search_place("Eiffel Tower, Paris")
    
    if place:
        print("\nLocation details:")
        print(f"Name: {place['name']}")
        print(f"Coordinates: {place['latitude']}, {place['longitude']}")
        print("\nRaw data:")
        for key, value in place['raw'].items():
            print(f"{key}: {value}")
    else:
        print("No place found")

if __name__ == "__main__":
    asyncio.run(test_location_service()) 