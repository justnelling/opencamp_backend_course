"""
Streamlit Frontend - Public Mastodon Client (Read-Only)

Displays public, hashtag, and user timelines fetched from a public 
Mastodon instance (e.g., mastodon.social).
"""

import streamlit as st
import asyncio
import sys
import os
from pathlib import Path

# Page config must be the first Streamlit command
st.set_page_config(layout="wide")

# --- Path Setup & Client Import ---
frontend_dir = Path(__file__).parent.resolve()
mastodon_dir = frontend_dir.parent
project_root = mastodon_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the client that interacts with public Mastodon instances
try:
    from mastodon.client import MastodonClient
except ImportError as e:
    st.error(f"Failed to import MastodonClient: {e}. Ensure it exists and path is correct.")
    st.stop()

# --- Configuration ---
DEFAULT_INSTANCE_URL = "https://mastodon.social"
DEFAULT_HASHTAG = "fediverse"
DEFAULT_USER = "Gargron@mastodon.social"
MAX_STATUSES = 20

# --- Initialize Public Client ---
@st.cache_resource
def get_mastodon_public_client():
    print(f"Initializing Public MastodonClient for {DEFAULT_INSTANCE_URL}...")
    return MastodonClient(instance_url=DEFAULT_INSTANCE_URL)

public_client = get_mastodon_public_client()

# --- Data Fetching Functions (Public Client) ---
async def _fetch_public_timeline_data_async(limit: int):
    return await public_client.get_public_timeline(limit=limit)

async def _fetch_hashtag_timeline_data_async(hashtag: str, limit: int):
    return await public_client.get_hashtag_timeline(hashtag=hashtag, limit=limit)

async def _fetch_user_timeline_data_async(username: str, limit: int):
    # This uses the Mastodon API endpoint via the client
    return await public_client.get_user_timeline(username=username, limit=limit)

# Synchronous wrappers for Streamlit caching
@st.cache_data(ttl=300)
def get_public_timeline_data(limit: int):
    try:
        return asyncio.run(_fetch_public_timeline_data_async(limit))
    except Exception as e:
        st.error(f"Error fetching public timeline: {e}", icon="🚨")
        return []

@st.cache_data(ttl=300)
def get_hashtag_timeline_data(hashtag: str, limit: int):
    if not hashtag:
        return []
    try:
        return asyncio.run(_fetch_hashtag_timeline_data_async(hashtag, limit))
    except Exception as e:
        st.error(f"Error fetching timeline for #{hashtag}: {e}", icon="🚨")
        return []

@st.cache_data(ttl=300)
def get_user_timeline_data(username: str, limit: int):
    if not username:
        return []
    try:
        # Client already handles username format for lookup
        return asyncio.run(_fetch_user_timeline_data_async(username, limit))
    except Exception as e:
        st.error(f"Error fetching timeline for {username}: {e}", icon="🚨")
        return []

# --- UI Display Functions ---
def display_status(status: dict):
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

    st.markdown(content_html, unsafe_allow_html=True)
    media = status.get('media_attachments', [])
    if media:
        cols = st.columns(len(media))
        for i, attachment in enumerate(media):
            if attachment.get('type') == 'image' and attachment.get('preview_url'):
                with cols[i]:
                    st.image(attachment['preview_url'])
    st.divider()

# --- Streamlit App Layout ---
st.title(f"Public Mastodon Feed Explorer ({DEFAULT_INSTANCE_URL})")

tab_view_public, tab_view_hashtag, tab_view_user = st.tabs([
    "🌐 Public Timeline",
    "#️⃣ Hashtag Search",
    "👤 User Timeline"
])

# --- Public Timeline Tab ---
with tab_view_public:
    st.header(f"🌐 Public Timeline")
    with st.spinner("Fetching public posts..."):
        public_timeline = get_public_timeline_data(limit=MAX_STATUSES)
        if public_timeline:
            for status in public_timeline:
                display_status(status)
        else:
            st.write("No public posts found or error fetching.")

# --- Hashtag Timeline Tab ---
with tab_view_hashtag:
    st.header("#️⃣ Hashtag Search")
    hashtag = st.text_input("Enter hashtag (without #):", value=DEFAULT_HASHTAG, key="hashtag_search")
    if hashtag:
        st.write(f"Showing the latest posts tagged with #{hashtag} from {DEFAULT_INSTANCE_URL}...")
        with st.spinner(f"Fetching #{hashtag} posts..."):
            hashtag_timeline = get_hashtag_timeline_data(hashtag=hashtag, limit=MAX_STATUSES)
            if hashtag_timeline:
                for status in hashtag_timeline:
                    display_status(status)
            else:
                st.write(f"No posts found for #{hashtag} or error fetching.")

# --- User Timeline Tab ---
with tab_view_user:
    st.header("👤 User Timeline")
    username = st.text_input(f"Enter username@{DEFAULT_INSTANCE_URL.split('//')[1]} (or user@otherdomain):", value=DEFAULT_USER, key="user_search")
    if username:
        st.write(f"Showing the latest posts from {username}...")
        with st.spinner(f"Fetching {username}'s posts..."):
            user_timeline = get_user_timeline_data(username=username, limit=MAX_STATUSES)
            if user_timeline:
                for status in user_timeline:
                    display_status(status)
            else:
                st.write(f"No posts found for {username} or error fetching.")

st.sidebar.markdown("---")
st.sidebar.info(f"This app displays public data fetched from {DEFAULT_INSTANCE_URL}.") 