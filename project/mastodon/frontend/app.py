"""
Streamlit Frontend for Mastodon Client (Read-Only)

Displays public, hashtag, and user timelines from mastodon.social.
"""

import streamlit as st
import asyncio
import sys
import os
from pathlib import Path

# Page config must be the first Streamlit command
st.set_page_config(layout="wide")

# Adjust path to import MastodonClient using absolute path from project root
# Get the absolute path of the current script's directory (frontend)
frontend_dir = Path(__file__).parent.resolve()
# Get the absolute path of the parent directory (mastodon)
mastodon_dir = frontend_dir.parent
# Get the absolute path of the project root directory (one level above mastodon)
project_root = mastodon_dir.parent
# Add the project root to sys.path if it's not already there
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now we can import using the full path from the project root
from mastodon.client import MastodonClient

# --- Configuration ---
DEFAULT_INSTANCE_URL = "https://mastodon.social"
DEFAULT_HASHTAG = "fediverse"
DEFAULT_USER = "Gargron@mastodon.social"
MAX_STATUSES = 20 # Max number of statuses to fetch/display per timeline

# --- Mastodon Client Initialization ---
# Initialize without credentials for read-only public access
# Use st.singleton to create the client instance only once
@st.cache_resource
def get_mastodon_client():
    print("Initializing MastodonClient...") # Debug print
    return MastodonClient(instance_url=DEFAULT_INSTANCE_URL)

client = get_mastodon_client()

# --- Data Fetching Functions ---

# Define the actual async fetching logic separately
async def _fetch_public_timeline_data_async(limit: int):
    return await client.get_public_timeline(limit=limit)

async def _fetch_hashtag_timeline_data_async(hashtag: str, limit: int):
    return await client.get_hashtag_timeline(hashtag=hashtag, limit=limit)

async def _fetch_user_timeline_data_async(username: str, limit: int):
    return await client.get_user_timeline(username=username, limit=limit)

# Create synchronous wrappers for Streamlit caching
@st.cache_data(ttl=300) # Cache for 5 minutes
def get_public_timeline_data(limit: int):
    """Fetches and caches public timeline data."""
    try:
        # Run the async function and return the result
        return asyncio.run(_fetch_public_timeline_data_async(limit))
    except Exception as e:
        st.error(f"Error fetching public timeline: {e}", icon="🚨")
        return []

@st.cache_data(ttl=300) # Cache for 5 minutes
def get_hashtag_timeline_data(hashtag: str, limit: int):
    """Fetches and caches hashtag timeline data."""
    if not hashtag:
        return []
    try:
        # Run the async function and return the result
        return asyncio.run(_fetch_hashtag_timeline_data_async(hashtag, limit))
    except Exception as e:
        st.error(f"Error fetching timeline for #{hashtag}: {e}", icon="🚨")
        return []

@st.cache_data(ttl=300) # Cache for 5 minutes
def get_user_timeline_data(username: str, limit: int):
    """Fetches and caches user timeline data."""
    if not username:
        return []
    try:
        # Ensure username format is handled (basic check)
        if '@' not in username:
            st.warning("Username should be in format user@domain for reliable lookup.", icon="⚠️")
        # Run the async function and return the result
        return asyncio.run(_fetch_user_timeline_data_async(username, limit))
    except Exception as e:
        st.error(f"Error fetching timeline for {username}: {e}", icon="🚨")
        return []

# --- UI Display Functions ---

def display_status(status: dict):
    """Displays a single status in a consistent format."""
    account = status.get('account', {})
    author_name = account.get('display_name', 'Unknown User')
    author_handle = account.get('acct', 'unknown')
    avatar_url = account.get('avatar_static')
    content_html = status.get('content', '[No Content]')
    created_at = status.get('created_at', '')
    status_url = status.get('url', '#')

    col1, col2 = st.columns([1, 9])
    with col1:
        if avatar_url:
            st.image(avatar_url, width=48)
    with col2:
        st.markdown(f"""
        **{author_name}** <small>(@{author_handle})</small> · <small>[{created_at}]({status_url})</small>
        """, unsafe_allow_html=True)

    st.markdown(content_html, unsafe_allow_html=True) # Display rendered HTML content
    # Display media attachments if any
    media = status.get('media_attachments', [])
    if media:
        cols = st.columns(len(media))
        for i, attachment in enumerate(media):
            if attachment.get('type') == 'image' and attachment.get('preview_url'):
                with cols[i]:
                    st.image(attachment['preview_url'])
            # TODO: Add handling for other media types (video, gifv, audio)
    st.divider()


# --- Streamlit App Layout ---

st.title(f"Mastodon Feed Explorer ({DEFAULT_INSTANCE_URL})")

tab1, tab2, tab3 = st.tabs(["🌐 Public Timeline", "#️⃣ Hashtag Search", "👤 User Timeline"])

# --- Public Timeline Tab ---
with tab1:
    st.header("🌐 Public Timeline")
    st.write(f"Showing the latest public posts from {DEFAULT_INSTANCE_URL}.")
    with st.spinner("Fetching public posts..."):
        # Call the synchronous cached function directly
        public_timeline = get_public_timeline_data(limit=MAX_STATUSES)
        if public_timeline:
            for status in public_timeline:
                display_status(status)
        else:
            st.write("No public posts found or error fetching.")

# --- Hashtag Timeline Tab ---
with tab2:
    st.header("#️⃣ Hashtag Search")
    hashtag = st.text_input("Enter hashtag (without #):", value=DEFAULT_HASHTAG)
    if hashtag:
        st.write(f"Showing the latest posts tagged with #{hashtag}...")
        with st.spinner(f"Fetching #{hashtag} posts..."):
            # Call the synchronous cached function directly
            hashtag_timeline = get_hashtag_timeline_data(hashtag=hashtag, limit=MAX_STATUSES)
            if hashtag_timeline:
                for status in hashtag_timeline:
                    display_status(status)
            else:
                st.write(f"No posts found for #{hashtag} or error fetching.")

# --- User Timeline Tab ---
with tab3:
    st.header("👤 User Timeline")
    username = st.text_input("Enter username (e.g., user@domain):", value=DEFAULT_USER)
    if username:
        st.write(f"Showing the latest posts from {username}...")
        with st.spinner(f"Fetching {username}'s posts..."):
            # Call the synchronous cached function directly
            user_timeline = get_user_timeline_data(username=username, limit=MAX_STATUSES)
            if user_timeline:
                for status in user_timeline:
                    display_status(status)
            else:
                st.write(f"No posts found for {username} or error fetching.")

st.sidebar.markdown("---")
st.sidebar.info("This app displays public data from a Mastodon instance using its API. No authentication is used.") 