# Mastodon Implementation

This project implements two distinct components:

1. A Mastodon client for reading public data from any Mastodon instance
2. A custom Mastodon server for creating and managing posts

## Project Structure

```
mastodon/
├── client/                 # Mastodon client for reading public data
│   ├── __init__.py
│   ├── client.py          # Client class for reading from Mastodon instances
│   └── signature.py       # Client-side HTTP signature generation
├── server/                # Custom Mastodon server implementation
│   ├── __init__.py
│   ├── main.py           # FastAPI server implementation
│   ├── signature.py      # Server-side HTTP signature verification
│   ├── actor.py          # Actor model for user profiles
│   └── inbox_outbox.py   # Inbox/outbox for activities
├── frontend/             # Streamlit frontend applications
│   ├── mastodon_reader.py  # UI for reading from public Mastodon instances
│   └── mastodon_writer.py  # UI for posting to our custom Mastodon server
└── tests/               # Test files
    └── __init__.py
```

## Components

### 1. Mastodon Client (Read-Only)

The client implementation allows you to read public data from any Mastodon instance:

1. **View Public Data**
   - Browse public timelines
   - Search hashtags
   - View user profiles
   - Run with: `streamlit run project/mastodon/frontend/mastodon_reader.py`

This component is read-only and doesn't require authentication. It's useful for browsing and viewing public Mastodon content.

### 2. Custom Mastodon Server

Our custom Mastodon server implementation provides a Mastodon-compatible API for creating and managing posts:

1. **Run the Server**

   ```bash
   uvicorn project.mastodon.server.main:app --reload
   ```

2. **Create Posts**

   - Upload media
   - Create statuses with GPS coordinates
   - Run with: `streamlit run project/mastodon/frontend/mastodon_writer.py`

3. **Available Endpoints**
   - `/api/v1/media` - Upload media files
   - `/api/v1/statuses` - Create and fetch statuses
   - `/api/v1/timelines/public` - Public timeline
   - `/api/v1/timelines/tag/{hashtag}` - Hashtag timeline
   - `/api/v1/accounts/{username}/statuses` - User timeline
   - `/.well-known/webfinger` - Instance discovery
   - `/users/{username}` - User profiles

This component allows you to create and manage posts on your own Mastodon server.

## Dependencies

- FastAPI - Web framework for the server
- Streamlit - Frontend applications
- aiohttp - Async HTTP client
- cryptography - HTTP signature handling
- geopy - Location lookup
- httpx - HTTP client for frontend

## Development

1. Install dependencies:

   ```bash
   pip install fastapi uvicorn streamlit aiohttp cryptography geopy httpx
   ```

2. Run the server:

   ```bash
   uvicorn project.mastodon.server.main:app --reload
   ```

3. Run the frontend:

   ```bash
   # For reading from public Mastodon instances
   streamlit run project/mastodon/frontend/mastodon_reader.py

   # For posting to our custom server
   streamlit run project/mastodon/frontend/mastodon_writer.py
   ```

## Features

### Client Features (Read-Only)

- View public timelines from any Mastodon instance
- Search hashtags
- View user profiles
- No authentication required

### Server Features

- Mastodon-compatible API
- HTTP signature verification
- Media upload handling
- Timeline management
- User profiles
- WebFinger support
- GPS coordinate support
- Custom post creation

## Security

- HTTP signatures for authentication
- Secure media handling
- Input validation
- CORS support

## Future Improvements

1. Database integration for persistent storage
2. User authentication and authorization
3. ActivityPub federation
4. Real-time updates
5. Media processing and optimization
6. Rate limiting
7. Caching
