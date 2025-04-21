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
if 'is_checkin_mode' not in st.session_state:
    st.session_state.is_checkin_mode = False
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

# --- Helper Functions for Server Interaction ---

async def _login_async(username, password):
    """Login to the server and get an access token."""
    client = httpx.AsyncClient(base_url=LOCAL_SERVER_URL, timeout=30.0)
    try:
        response = await client.post("/token", json={"username": username, "password": password})
        response.raise_for_status()
        return response.json()
    finally:
        await client.aclose()

async def _upload_image_async(image_file):
    """Uploads image bytes to the local server's media endpoint."""
    files = {'file': (image_file.name, image_file.getvalue(), image_file.type)}
    client = httpx.AsyncClient(base_url=LOCAL_SERVER_URL, timeout=30.0)
    try:
        response = await client.post("/api/v1/media", files=files)
        response.raise_for_status()
        media_data = response.json()
        media_id = media_data.get("id")
        media_url = media_data.get("url")
        if not media_id:
            raise ValueError("Media ID not found in server response")
        return media_id, media_url
    finally:
        await client.aclose()

async def _post_status_async(payload):
    """Posts a new status to the local server."""
    client = httpx.AsyncClient(base_url=LOCAL_SERVER_URL, timeout=30.0)
    try:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        response = await client.post("/api/v1/statuses", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    finally:
        await client.aclose()

# --- Streamlit App Layout ---
st.title(f"Local Server Poster ({LOCAL_SERVER_URL})")

# --- Login Section ---
st.header("🔑 Login")
username = st.text_input("Username:", key="username")
password = st.text_input("Password:", type="password", key="password")

if st.button("Login", key="login_btn"):
    with st.spinner("Logging in..."):
        try:
            token_data = asyncio.run(_login_async(username, password))
            st.session_state.access_token = token_data.get("access_token")
            st.session_state.is_logged_in = True
            st.success("Login successful!")
        except Exception as e:
            st.error(f"Login failed: {e}")
            st.session_state.is_logged_in = False
            st.session_state.access_token = None

# --- Create Post / Check-in Section ---
if st.session_state.get("is_logged_in", False):
    st.header("✏️ Create Post")
    
    # Toggle between regular post and check-in
    post_type = st.radio("Post Type:", ["Regular Post", "Check-in"], key="post_type")
    st.session_state.is_checkin_mode = (post_type == "Check-in")
    
    if st.session_state.is_checkin_mode:
        # Check-in mode
        st.subheader("📍 Check-in")
        place_name = st.text_input("Where are you?", placeholder="e.g., Eiffel Tower, Paris", key="place_name")
        
        if st.button("Find Location", key="find_location_btn"):
            if place_name:
                st.session_state.found_location = None  # Reset previous search
                with st.spinner(f"Finding '{place_name}'..."):
                    try:
                        geolocator = get_geolocator()
                        location = geolocator.geocode(place_name, timeout=10)
                        if location:
                            st.session_state.found_location = location
                            st.success(f"Found: {location.address}")
                            st.info(f"Coordinates: Lat={location.latitude}, Lon={location.longitude}")
                        else:
                            st.error(f"Could not find '{place_name}'. Try a more specific location.")
                    except GeocoderTimedOut:
                        st.error("Search timed out. Try again or simplify the query.")
                    except GeocoderServiceError as e:
                        st.error(f"Service error: {e}")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")
            else:
                st.warning("Please enter a place name.")
        
        # Display currently selected location (if any)
        if st.session_state.found_location:
            loc = st.session_state.found_location
            st.markdown(f"**Selected Location:** {loc.address}")
            if st.button("Clear Location", key="clear_loc_btn"):
                st.session_state.found_location = None
                st.rerun()
    else:
        # Regular post mode
        st.subheader("Regular Post")
    
    # Post Content & Image Upload Section (common to both modes)
    st.subheader("Post Content")
    status_text = st.text_area("What's on your mind?", key="status_text")
    uploaded_images = st.file_uploader("Upload Images (Optional):", type=["png", "jpg", "jpeg", "gif", "webp"], accept_multiple_files=True, key="img_upload")
    
    if uploaded_images:
        for i, img in enumerate(uploaded_images):
            st.image(img, caption=f"Image {i+1}", width=200)
    
    # Submit Section
    st.subheader("Submit")
    if st.button("Post", key="post_btn"):
        # Reset previous upload attempt state
        st.session_state.upload_media_id = None
        st.session_state.upload_media_url = None
        error_occurred = False
        media_ids = []

        # Check if text or image or location is provided
        if not status_text and not uploaded_images and not st.session_state.found_location:
            st.warning("Please provide status text, images, or a location to check-in.")
            st.stop()

        with st.spinner("Processing post..."):
            # Step 1: Upload images if any
            for img in uploaded_images:
                try:
                    media_id, media_url = asyncio.run(_upload_image_async(img))
                    media_ids.append(media_id)
                    st.success(f"Uploaded image: {img.name}")
                except Exception as e:
                    st.error(f"Failed to upload {img.name}: {e}")
                    error_occurred = True

            # Step 2: Prepare and send status
            if not error_occurred:
                post_payload = {}
                post_payload["status"] = status_text
                
                # Add location if in check-in mode and location is found
                if st.session_state.is_checkin_mode and st.session_state.found_location:
                    loc = st.session_state.found_location
                    post_payload["latitude"] = str(loc.latitude)
                    post_payload["longitude"] = str(loc.longitude)
                    post_payload["place_name"] = loc.address
                
                # Add media IDs if any
                if media_ids:
                    post_payload["media_ids[]"] = media_ids

                if not post_payload.get("status") and not post_payload.get("media_ids[]") and not post_payload.get("latitude"):
                    st.warning("Nothing to post (no text, images, or location).")
                else:
                    try:
                        st.write("Creating status...")
                        status_data = asyncio.run(_post_status_async(post_payload))
                        st.success(f"Status posted successfully!")
                        st.json(status_data)
                        st.session_state.found_location = None
                        st.session_state.upload_media_id = None
                        st.session_state.upload_media_url = None
                    except (httpx.RequestError, httpx.HTTPStatusError, Exception) as e:
                        st.error(f"Status creation failed: {e}")
                        if isinstance(e, httpx.HTTPStatusError):
                            st.error(f"Response: {e.response.text}")

st.sidebar.markdown("---")
st.sidebar.info(f"This app interacts with the local server at {LOCAL_SERVER_URL}.") 