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
│   └── queue/            # Background task processing
├── cockroachdb_setup/    # Database setup and initialization
│   ├── cockroachdb.py    # Database schema and initialization
│   └── README.md         # Database documentation
├── frontend/             # Streamlit frontend applications
│   ├── app_our_server.py # UI for interacting with our server
│   └── app_client.py     # UI for reading from public Mastodon instances
└── media/                # Media storage directory
```

## Components

### Server Implementation

Our custom Mastodon server implementation provides a Mastodon-compatible API with ActivityPub federation support:

1. **Run the Server**

   ```bash
   uvicorn project.mastodon.server.main:app --reload
   ```

2. **Server Architecture**

   - **API Layer**: RESTful endpoints following Mastodon API conventions
   - **ActivityPub**: Implementation of the ActivityPub protocol for federation
   - **Authentication**: JWT-based authentication system
   - **Database**: CockroachDB integration for persistent storage
   - **Media Handling**: Support for media attachments in posts
   - **Queue System**: Background processing for federation tasks

3. **Available Endpoints**
   - `/api/v1/media` - Upload media files
   - `/api/v1/statuses` - Create and fetch statuses
   - `/api/v1/timelines/public` - Public timeline
   - `/api/v1/timelines/tag/{hashtag}` - Hashtag timeline
   - `/api/v1/accounts/{username}/statuses` - User timeline
   - `/.well-known/webfinger` - Instance discovery
   - `/users/{username}` - User profiles
   - `/inbox` - ActivityPub inbox for federation
   - `/outbox` - ActivityPub outbox for federation

### Database Setup

The server uses CockroachDB for persistent storage:

1. **Start CockroachDB**

   ```bash
   cockroach start-single-node --insecure --listen-addr=localhost:26257
   ```

2. **Initialize the Database**

   ```bash
   python project/mastodon/cockroachdb_setup/cockroachdb.py
   ```

3. **Database Schema**
   - Users table: Account information and authentication
   - Statuses table: Posts with content and metadata
   - Media attachments: Files associated with posts
   - Relationships: Following/follower connections
   - Hashtags: Tag information and associations

### Frontend Applications

The project includes two Streamlit applications:

1. **Our Server UI** (`app_our_server.py`)

   - Create and manage posts
   - Upload media attachments
   - View timelines and user profiles
   - Run with: `streamlit run project/mastodon/frontend/app_our_server.py`

2. **Client UI** (`app_client.py`)
   - Read from public Mastodon instances
   - View public timelines
   - Search hashtags
   - Run with: `streamlit run project/mastodon/frontend/app_client.py`

## Dependencies

- FastAPI - Web framework for the server
- Streamlit - Frontend applications
- aiohttp - Async HTTP client
- cryptography - HTTP signature handling
- geopy - Location lookup
- httpx - HTTP client for frontend
- CockroachDB - Distributed SQL database
- PyJWT - JWT authentication

## Development

1. Install dependencies:

   ```bash
   pip install -r project/requirements.txt
   ```

2. Start the database:

   ```bash
   cockroach start-single-node --insecure --listen-addr=localhost:26257
   ```

3. Initialize the database:

   ```bash
   python project/mastodon/cockroachdb_setup/cockroachdb.py
   ```

4. Run the server:

   ```bash
   uvicorn project.mastodon.server.main:app --reload
   ```

5. Run the frontend:

   ```bash
   # For interacting with our server
   streamlit run project/mastodon/frontend/app_our_server.py

   # For reading from public Mastodon instances
   streamlit run project/mastodon/frontend/app_client.py
   ```

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
- Custom post creation
- Hashtag support
- Following/follower relationships

## Security

- HTTP signatures for authentication
- Secure media handling
- Input validation
- CORS support
- JWT-based authentication

## Testing the Implementation

You can test the Mastodon server implementation using curl commands. Here's a step-by-step guide:

### 1. Create a New User

```bash
curl -X POST http://localhost:8000/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

### 2. Get Access Token

```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpassword123"
  }'
```

Save the access token from the response for use in subsequent requests:

```bash
export ACCESS_TOKEN="your_access_token_here"
```

### 3. Create a Status with Location Check-in

You can create a status with a location check-in by providing a place name:

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

The server will automatically find the coordinates for the place name and include them in the status.

You can also provide coordinates directly if you have them:

```bash
curl -X POST http://localhost:8000/api/v1/statuses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "status": "Posting from a specific location! #location",
    "visibility": "public",
    "latitude": 37.7749,
    "longitude": -122.4194
  }'
```

### 4. Upload Media

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

### 5. View Timelines

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

### 6. Get Account Information

```bash
curl http://localhost:8000/api/v1/accounts/testuser
```

### 7. WebFinger Discovery

```bash
curl "http://localhost:8000/.well-known/webfinger?resource=acct:testuser@example.com"
```

### Query Parameters

The timeline endpoints support the following query parameters:

- `limit`: Number of statuses to fetch (default: 20)
- `since_id`: Return only statuses newer than this ID
- `max_id`: Return only statuses older than this ID

Example:

```bash
curl "http://localhost:8000/api/v1/timelines/public?limit=5"
```

## Future Improvements

1. Enhanced federation capabilities
2. Real-time updates
3. Media processing and optimization
4. Rate limiting
5. Caching
6. Advanced search functionality
7. Notification system
8. Improved location search with autocomplete
