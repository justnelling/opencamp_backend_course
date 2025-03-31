"""
Streamlit Frontend - Local Mastodon-Style Server Client

Allows creating posts with check-ins (via geopy lookup) and image uploads 
to the local server running from project/mastodon/main.py.
"""

import streamlit as st
import asyncio
import sys
import os
from pathlib import Path
import io # For handling file uploads

# --- Dependency Imports ---
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
except ImportError:
    st.error("Missing dependency: Please run `pip install geopy`")
    st.stop()

try:
    import httpx
except ImportError:
    st.error("Missing dependency: Please run `pip install httpx`")
    st.stop()

# Page config must be the first Streamlit command
st.set_page_config(layout="wide")

# --- Configuration ---
LOCAL_SERVER_URL = "http://localhost:8000" # URL of our main.py server
USER_AGENT = "mastodon-streamlit-app/1.0" # User agent for geopy

# --- Initialize Clients ---

# Geopy Geolocator
@st.cache_resource
def get_geolocator():
    print("Initializing Nominatim Geolocator...")
    return Nominatim(user_agent=USER_AGENT)

geolocator = get_geolocator()

# HTTP Client for Local Server
@st.cache_resource
def get_local_server_client():
     print("Initializing HTTPX Client for Local Server...")
     return httpx.AsyncClient(base_url=LOCAL_SERVER_URL, timeout=30.0)

local_http_client = get_local_server_client()

# --- Session State Initialization ---
if 'found_location' not in st.session_state:
    st.session_state.found_location = None
if 'upload_media_id' not in st.session_state:
    st.session_state.upload_media_id = None
if 'upload_media_url' not in st.session_state:
    st.session_state.upload_media_url = None

# --- Helper Functions for Server Interaction ---

async def _upload_image_async(image_file):
    """Uploads image bytes to the local server's media endpoint."""
    files = {'file': (image_file.name, image_file.getvalue(), image_file.type)}
    async with get_local_server_client() as client:
        response = await client.post("/api/v2/media", files=files)
        response.raise_for_status()
        media_data = response.json()
        media_id = media_data.get("id")
        media_url = media_data.get("url")
        if not media_id:
            raise ValueError("Media ID not found in server response")
        return media_id, media_url

async def _post_status_async(payload):
    """Posts status data to the local server's status endpoint."""
    async with get_local_server_client() as client:
        response = await client.post("/api/v1/statuses", data=payload)
        response.raise_for_status()
        return response.json()

# --- Streamlit App Layout ---
st.title(f"Local Server Poster ({LOCAL_SERVER_URL})")

# --- Create Post / Check-in Section ---
# This is the main section for this app

st.header("✏️ Create Post / Check-in")
st.markdown(f"Posts will be created on the local server: `{LOCAL_SERVER_URL}`")

# --- Location Search Section ---
st.subheader("1. Find Location (Optional Check-in)")
location_query = st.text_input("Enter place name to find coordinates:", key="loc_query")
if st.button("Search Location", key="search_loc_btn"):
    if location_query:
        st.session_state.found_location = None # Reset previous search
        with st.spinner(f"Geocoding '{location_query}'..."):
            try:
                location = geolocator.geocode(location_query, timeout=10)
                if location:
                    st.session_state.found_location = location
                    st.success(f"Found: {location.address}")
                    st.info(f"Coordinates: Lat={location.latitude}, Lon={location.longitude}")
                else:
                    st.error(f"Could not find coordinates for '{location_query}'.")
            except GeocoderTimedOut:
                st.error("Geocoder timed out. Try again or simplify the query.")
            except GeocoderServiceError as e:
                st.error(f"Geocoder service error: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred during geocoding: {e}")
    else:
        st.warning("Please enter a place name to search.")

# Display currently selected location (if any)
if st.session_state.found_location:
    loc = st.session_state.found_location
    st.markdown(f"**Selected Check-in:** {loc.address} (`{loc.latitude:.4f}, {loc.longitude:.4f}`)")
    if st.button("Clear Location", key="clear_loc_btn"):
        st.session_state.found_location = None
        st.rerun()

st.divider()

# --- Post Content & Image Upload Section ---
st.subheader("2. Compose Post")
status_text = st.text_area("Status Content:", key="status_text")
uploaded_image = st.file_uploader("Upload Image (Optional):", type=["png", "jpg", "jpeg", "gif", "webp"], key="img_upload")

if uploaded_image:
     st.image(uploaded_image, caption="Image to Upload", width=200)

st.divider()

# --- Submit Section ---
st.subheader("3. Submit Post")
if st.button("Post Status", key="post_btn"):
    # Reset previous upload attempt state
    st.session_state.upload_media_id = None
    st.session_state.upload_media_url = None
    error_occurred = False

    # Check if text or image or location is provided
    if not status_text and not uploaded_image and not st.session_state.found_location:
        st.warning("Please provide status text, an image, or a location to check-in.")
        st.stop()

    with st.spinner("Processing post..."):
        media_id_to_post = None
        # Step 1: Upload image if present (using asyncio.run)
        if uploaded_image is not None:
            try:
                st.write("Uploading image...")
                media_id_to_post, uploaded_media_url = asyncio.run(_upload_image_async(uploaded_image))
                st.session_state.upload_media_id = media_id_to_post
                st.session_state.upload_media_url = uploaded_media_url
                st.write(f":white_check_mark: Image uploaded (ID: {media_id_to_post})")
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError, Exception) as e:
                st.error(f"Media upload failed: {e}")
                if isinstance(e, httpx.HTTPStatusError):
                    st.error(f"Response: {e.response.text}")
                error_occurred = True

        # Step 2: Prepare and send status if no upload error
        if not error_occurred:
             post_payload = {}
             post_payload["status"] = status_text
             if st.session_state.found_location:
                  loc = st.session_state.found_location
                  post_payload["latitude"] = str(loc.latitude)
                  post_payload["longitude"] = str(loc.longitude)
             if media_id_to_post:
                  post_payload["media_ids[]"] = [media_id_to_post]

             if not post_payload.get("status") and not post_payload.get("media_ids[]") and not post_payload.get("latitude"):
                  st.warning("Nothing to post (no text, image, or location).")
             else:
                try:
                    st.write("Creating status...")
                    status_data = asyncio.run(_post_status_async(post_payload))
                    st.success(f"Status posted successfully!")
                    st.json(status_data)
                    st.session_state.found_location = None
                    st.session_state.upload_media_id = None
                    st.session_state.upload_media_url = None
                    # Don't rerun automatically, let user see the success message/JSON
                except (httpx.RequestError, httpx.HTTPStatusError, Exception) as e:
                    st.error(f"Status creation failed: {e}")
                    if isinstance(e, httpx.HTTPStatusError):
                         st.error(f"Response: {e.response.text}")

st.sidebar.markdown("---")
st.sidebar.info(f"This app interacts with the local server at {LOCAL_SERVER_URL}.") 