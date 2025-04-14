# CockroachDB Setup for Mastodon

This project sets up and manages the CockroachDB database for the Mastodon server implementation.
It provides the necessary tables and structure for storing Mastodon data.

## Project Structure

```
database/
├── cockroachdb.py    # Database setup and table definitions
└── README.md         # This file
```

## Prerequisites

1. CockroachDB installed locally

   ```bash
   # On macOS with Homebrew
   brew install cockroach
   ```

2. Python dependencies
   ```bash
   pip3 install psycopg2-binary
   ```

## Setup Instructions

1. Create a data directory for CockroachDB

   ```bash
   mkdir -p /Users/<your-username>/cockroach-data
   ```

2. Start CockroachDB in single-node mode

   ```bash
   cockroach start-single-node --insecure --store=/Users/<your-username>/cockroach-data
   ```

3. Verify the database is running

   ```bash
   cockroach node status --insecure
   ```

4. Run the database setup script
   ```bash
   python3 project/database/cockroachdb.py
   ```

## Database Schema

The setup script creates the following tables:

1. **users**

   - Stores user profiles and account information
   - Primary key: UUID
   - Fields: username, display_name, bio, avatar_url, etc.

2. **statuses**

   - Stores posts and status updates
   - Primary key: UUID
   - Foreign key: user_id references users(id)
   - Fields: content, visibility, sensitive, location, etc.

3. **media_attachments**

   - Stores media files associated with statuses
   - Primary key: UUID
   - Foreign key: status_id references statuses(id)
   - Fields: file_path, file_type, description, etc.

4. **relationships**

   - Stores user relationships (follows, blocks)
   - Primary key: UUID
   - Foreign keys: follower_id, following_id reference users(id)
   - Fields: relationship_type, created_at, etc.

5. **hashtags**

   - Stores hashtag information
   - Primary key: UUID
   - Fields: name, created_at

6. **status_hashtags**

   - Junction table linking statuses and hashtags
   - Composite primary key: (status_id, hashtag_id)
   - Foreign keys reference statuses(id) and hashtags(id)

7. **mentions**
   - Stores user mentions in statuses
   - Primary key: UUID
   - Foreign keys: status_id, mentioned_user_id
   - Fields: created_at

## Connection Details

The database connection string is:

```
postgresql://root@localhost:26257/defaultdb?sslmode=disable
```

Components:

- Protocol: postgresql://
- User: root (default, no password in insecure mode)
- Host: localhost
- Port: 26257 (default CockroachDB port)
- Database: defaultdb
- SSL Mode: disabled (required for insecure mode)

## Viewing the Database

1. Using the SQL shell:

   ```bash
   cockroach sql --insecure
   ```

2. Common SQL commands:

   ```sql
   -- List all tables
   SHOW TABLES;

   -- View table structure
   \d table_name;

   -- View table contents
   SELECT * FROM table_name;
   ```

3. Using the Admin UI:
   - Open http://localhost:8080 in your browser
   - Provides a graphical interface for database management

## Security Note

This setup uses insecure mode for development purposes only. For production:

1. Enable TLS/SSL
2. Set up proper authentication
3. Configure secure networking
4. Use proper user permissions

## Development

The `cockroachdb.py` script includes:

1. Table creation functions
2. Test data insertion
3. Basic query examples

Run the script to set up the database:

```bash
python3 project/database/cockroachdb.py
```

## Future Improvements

1. Add database migrations
2. Implement connection pooling
3. Add backup and restore functionality
4. Set up proper user authentication
5. Add database monitoring
6. Implement data validation
7. Add database indexes for performance
