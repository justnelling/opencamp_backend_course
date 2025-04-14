# Opencamp Week 2 Assignment

Proof of concept for an ActivityPub server setup where we can upload 1 text-based post

## Project Structure

The project contains several implementations exploring different aspects of the ActivityPub protocol:

### `/project/activitypub`

A vanilla ActivityPub server implementation that focuses on the core protocol without additional features. This implementation explores the fundamental concepts of ActivityPub including actors, objects, and activities.

### `/project/mastodon/client`

A client implementation that reads from a public Mastodon instance. This demonstrates how to interact with existing Mastodon servers using their API.

### `/project/mastodon/server`

Our main implementation that builds a Mastodon-compatible server. This is integrated with:

- `/project/mastodon/frontend` - A web interface for interacting with the server
- `/project/database` - CockroachDB integration for persistent storage

This implementation combines Mastodon's features with our own database backend, providing a complete social media platform.

## Core ActivityPub architecture:

- Actor: fundamental primitive component of the social web (think like traditional 'account', but buffed)

- Defines a core 'distributed event log' architectural model for the open social web: to model any social interaction, use an extensible Object, wrapped in an Activity.

- Defines a Server-to-Server (S2S) protocol for distributing Objects and Activities to interested parties

- Defines a Client-to-Server (C2S) protocol for client software to interact with Actors and their data

- Uses the ActivityStreams 2 (AS2) core data model to describe commonly used social web activities, and the corresponding ActivityStreams Vocabulary that describes common extensions to AS2

- Uses Linked Data (JSON-LD) as decentralized mechanism for publishing data model extensions

## Database Integration

The server now uses CockroachDB for persistent storage. Key features:

- User accounts with password-based authentication
- Status storage with media attachments
- Hashtag support
- Follower/Following relationships
- Media attachments for posts

### Database Setup

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
- PyJWT for authentication
- Python 3.x

To run the server:

```bash
uvicorn project.mastodon.server.main:app --reload
```
