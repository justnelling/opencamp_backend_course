# Mastodon Implementation

This project implements a custom Mastodon server for creating and managing posts, with ActivityPub federation support.

## Project Structure

```
mastodon/
├── __init__.py
├── server/                # Server implementation
│   ├── __init__.py
│   ├── main.py           # FastAPI server implementation with all API endpoints
│   ├── activitypub/      # ActivityPub protocol implementation
│   ├── auth/             # Authentication and authorization
│   ├── database/         # Database models and operations
│   ├── media/            # Media handling
│   ├── location/         # Location services and geocoding
│   └── queue/            # Background task processing
├── cockroachdb_setup/    # Database setup and initialization
│   ├── cockroachdb.py    # Database schema and initialization
│   └── README.md         # Database documentation
├── frontend/             # Streamlit frontend applications
│   ├── app_our_server.py # UI for interacting with our server
│   └── app_client.py     # UI for reading from public Mastodon instances
├── media/                # Media storage directory
└── setup_and_run.sh      # Consolidated setup and run script
```

## Quick Start

The project includes a consolidated setup script that handles all initialization and startup:

```bash
./setup_and_run.sh
```

This script will:

1. Install all required dependencies
2. Start CockroachDB
3. Initialize the database with test data
4. Start the FastAPI server
5. Launch the Streamlit frontend applications

### Test Credentials

For all testing and development, use these standard credentials:

- Username: `testuser`
- Password: `password`

## Components

### Server Implementation

Our custom Mastodon server implementation provides a Mastodon-compatible API with ActivityPub federation support:

1. **Server Architecture**

   - **API Layer**: RESTful endpoints following Mastodon API conventions
   - **ActivityPub**: Implementation of the ActivityPub protocol for federation
   - **Authentication**: JWT-based authentication system with SHA-256 password hashing
   - **Database**: CockroachDB integration for persistent storage
   - **Media Handling**: Support for media attachments in posts
   - **Location Services**: Geocoding and place search functionality
   - **Queue System**: Background processing for federation tasks

2. **Available Endpoints**
   - `/api/v1/media` - Upload media files
   - `/api/v1/statuses` - Create and fetch statuses
   - `/api/v1/timelines/public` - Public timeline
   - `/api/v1/timelines/tag/{hashtag}` - Hashtag timeline
   - `/api/v1/accounts/{username}/statuses` - User timeline
   - `/api/v1/places/search` - Search for places
   - `/.well-known/webfinger` - Instance discovery
   - `/users/{username}` - User profiles
   - `/inbox` - ActivityPub inbox for federation
   - `/outbox` - ActivityPub outbox for federation

### Database Schema

The server uses CockroachDB with the following schema:

- Users table: Account information and authentication
- Statuses table: Posts with content and metadata
- Media attachments: Files associated with posts
- Relationships: Following/follower connections
- Hashtags: Tag information and associations
- Places: Location information and coordinates

### Frontend Applications

The project includes two Streamlit applications:

1. **Our Server UI** (`app_our_server.py`)

   - Create and manage posts
   - Upload media attachments
   - View timelines and user profiles

2. **Client UI** (`app_client.py`)
   - Read from public Mastodon instances
   - View public timelines
   - Search hashtags

## Dependencies

- FastAPI - Web framework for the server
- Streamlit - Frontend applications
- aiohttp - Async HTTP client
- cryptography - HTTP signature handling
- geopy - Location lookup and geocoding
- httpx - HTTP client for frontend
- CockroachDB - Distributed SQL database
- PyJWT - JWT authentication

## Features

### Server Features

- Mastodon-compatible API
- ActivityPub federation
- HTTP signature verification
- Media upload handling
- Timeline management
- User profiles
- WebFinger support
- GPS coordinate support
- Location services with geocoding
- Custom post creation
- Hashtag support
- Following/follower relationships

## Security

- HTTP signatures for authentication
- Secure media handling
- Input validation
- CORS support
- JWT-based authentication
- SHA-256 password hashing

## Testing the Implementation

You can test the Mastodon server implementation using curl commands. Here's a step-by-step guide:

### 1. Get Access Token

```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password"
  }'
```

Save the access token from the response for use in subsequent requests:

```bash
export ACCESS_TOKEN="your_access_token_here"
```

### 2. Create a Status with Location Check-in

```bash
curl -X POST http://localhost:8000/api/v1/statuses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "status": "Check-in at Eiffel Tower! #checkin",
    "visibility": "public",
    "place_name": "Eiffel Tower, Paris"
  }'
```

### 3. Upload Media

```bash
curl -X POST http://localhost:8000/api/v1/media \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/path/to/your/image.jpg" \
  -F "description=My image description"
```

Create a status with media:

```bash
curl -X POST http://localhost:8000/api/v1/statuses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "status": "Check out this image! #media",
    "visibility": "public",
    "media_ids": ["MEDIA_ID_FROM_UPLOAD"]
  }'
```

### 4. View Timelines

Public timeline:

```bash
curl http://localhost:8000/api/v1/timelines/public
```

Hashtag timeline:

```bash
curl "http://localhost:8000/api/v1/timelines/tag/test"
```

User timeline:

```bash
curl "http://localhost:8000/api/v1/accounts/testuser/statuses"
```

## Recent Updates

- Added consolidated setup script (`setup_and_run.sh`)
- Added location services with geocoding support
- Improved media attachment handling
- Enhanced password verification security with SHA-256 hashing
- Added test scripts for location service
- Fixed authentication issues
- Updated database schema to support location data
