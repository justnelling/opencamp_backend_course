# W3 assignment

## Core ActivityPub architecture:

- Actor: fundamental primitive component of the social web (think like traditional 'account', but buffed)

- Defines a core 'distributed event log' architectural model for the open social web: to model any social interaction, use an extensible Object, wrapped in an Activity.

- Defines a Server-to-Server (S2S) protocol for distributing Objects and Activities to interested parties

- Defines a Client-to-Server (C2S) protocol for client software to interact with Actors and their data

- Uses the ActivityStreams 2 (AS2) core data model to describesome commonly used social web activities, and the corresponding ActivityStreams Vocabulary that describes common extensions to AS2

- Uses Linked Data (JSON-LD) as decentralized mechanism for publishing data model extensions

## Why ActivityPub?

- Supports image uploads + location uploads out of the box

- Comprehensive documentation, even if a little messy

- JSON-LD format is familiar and intuitive to implement

## Learnings while building PoC

- Outbox serves to both register Activities on the server (for internal purposes) as well as to communicate with other servers

- Similar to JWT, ActivityPub uses HTTP Signatures for auth and verification:
  - (request-target): HTTP method and path ('post /users/beebo/outbox')
  - host: server's hostname
  - date: current timestamp
  - digest: SHA256 hash of request body

## Implementation

### Current System

#### Inputs

1. User-generated content:
   - Text posts (via send_text_post)
   - Check-ins with location data (via send_check_in) (dummy data)
   - Image uploads (via upload_media) (dummy data)
2. HTTP Requests:
   - POST requests to outbox
   - GET requests to actor profiles
   - POST requests to media upload endpoints

#### Outputs

1. ActivityPub Activities:
   - JSON-LD formatted activities
   - HTTP responses with proper signatures
2. Media Files:
   - Stored in local filesystem
   - Served via static file middleware
3. Actor Information:
   - Actor profiles
   - Webfinger responses

#### Handling GPS / image

- currently storing GPS coordinates + image as part of single "Note" object.
  - "location" field with GPS coordinates
  - "attachment" array with the image information

### To-do

1. Current implementation uses dummy data. Need to figure out how to get in actual GPS / image data from users.

2. Database

   - CockroachDB
   - Postgresql compatible
   - Built-in support for JSON

3. Auth

4. Frontend

   - streamlit, or lightweight frontend

5. Hosting options
   - AWS (really want to try)
   - Digital Ocean
