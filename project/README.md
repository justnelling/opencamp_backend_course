# Opencamp Assignment

Proof of concept for a decentralised social media app where users can do:

1. upload photos of their location
2. upload GPS coordinates of their location

check-ins similar to swarm / foursquare

## Project Structure

The project contains several implementations exploring different aspects of the ActivityPub protocol:

### `/project/activitypub`

A vanilla ActivityPub server implementation that focuses on the core protocol without additional features. This implementation explores the fundamental concepts of ActivityPub including actors, objects, and activities.

### `/project/mastodon_client`

A client implementation that reads from a public Mastodon instance. This demonstrates how to interact with existing Mastodon servers using their API.

### `/project/mastodon`

Our main implementation that builds a Mastodon-compatible server with the following components:

- `/server` - Core server implementation with:
  - FastAPI endpoints
  - ActivityPub protocol implementation
  - Queue system for federation
  - Database integration
- `/frontend` - Streamlit-based web interface
- `/cockroachdb_setup` - Database initialization and schema

## Core Components

### ActivityPub Architecture

- Actor: fundamental primitive component of the social web (think like traditional 'account', but buffed)
- Defines a core 'distributed event log' architectural model for the open social web
- Server-to-Server (S2S) protocol for distributing Objects and Activities
- Client-to-Server (C2S) protocol for client software interaction
- ActivityStreams 2 (AS2) core data model
- Linked Data (JSON-LD) for data model extensions

### Queue System

The server implements a RabbitMQ-based queue system for handling ActivityPub federation:

- Three main queues:
  - `activitypub_outbox`: New activities waiting to be processed
  - `activitypub_processing`: Activities currently being processed
  - `activitypub_failed`: Failed activities for retry
- Features:
  - Durable queues (survive RabbitMQ restarts)
  - Message persistence
  - Automatic retry mechanism (up to 3 attempts)
  - Fair distribution of work

### Database Integration

The server uses CockroachDB for persistent storage with:

- User accounts and authentication
- Status storage with media attachments
- Hashtag support
- Follower/Following relationships
- Media attachments for posts

#### Database Setup

1. Start CockroachDB:

```bash
cockroach start-single-node --insecure --listen-addr=localhost:26257
```

2. Initialize the database:

```bash
python project/database/cockroachdb.py
```

This will create the necessary tables:

- users (username, password_hash, display_name, bio, etc.)
- statuses (content, visibility, location, etc.)
- media_attachments (file_path, file_type, description)
- hashtags and status_hashtags
- relationships (followers/following)

## Authentication

The server implements JWT-based authentication:

1. Create an account:

```bash
curl -X POST "http://localhost:8000/api/v1/accounts" \
-H "Content-Type: application/json" \
-d '{
  "username": "alice",
  "password": "password123",
  "email": "alice@example.com"
}'
```

2. Login to get a token:

```bash
curl -X POST "http://localhost:8000/token" \
-H "Content-Type: application/json" \
-d '{
  "username": "alice",
  "password": "password123"
}'
```

3. Use the token for authenticated requests:

```bash
curl -X POST "http://localhost:8000/api/v1/statuses" \
-H "Authorization: Bearer YOUR_TOKEN" \
-H "Content-Type: application/json" \
-d '{
  "status": "Hello, Mastodon!",
  "visibility": "public"
}'
```

## API Endpoints

### Authentication

- POST `/token` - Login and get access token
- POST `/api/v1/accounts` - Create new account

### Accounts

- GET `/api/v1/accounts/{username}` - Get account information
- GET `/api/v1/accounts/{username}/statuses` - Get user's statuses

### Statuses

- POST `/api/v1/statuses` - Create new status
- GET `/api/v1/timelines/public` - Get public timeline
- GET `/api/v1/timelines/tag/{hashtag}` - Get hashtag timeline

### Media

- POST `/api/v1/media` - Upload media attachment

### ActivityPub

- GET `/.well-known/webfinger` - WebFinger endpoint for instance discovery

## Development

The server is built with:

- FastAPI for the web framework
- CockroachDB for the database
- RabbitMQ for the queue system
- PyJWT for authentication
- Python 3.x

### Running the Server

1. Start RabbitMQ:

```bash
rabbitmq-server
```

2. Start the server:

```bash
uvicorn project.mastodon.server.main:app --reload
```

### Testing

See the testing documentation in `/project/mastodon/README.md` for detailed instructions on testing the implementation using curl commands.
