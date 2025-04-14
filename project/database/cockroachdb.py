"""
CockroachDB Setup for Mastodon Server

This script sets up the necessary tables and structure for storing Mastodon data.
It creates tables for users, statuses, media attachments, and relationships.
"""

import psycopg2
from psycopg2 import OperationalError
from datetime import datetime

# --- Configuration ---
# Connection string for a local, single-node, insecure CockroachDB instance
# Using the default 'root' user and 'defaultdb' database.
CONNECTION_STRING = "postgresql://root@localhost:26257/defaultdb?sslmode=disable"

def drop_tables():
    """Drops all existing tables to allow for schema changes."""
    conn = None
    print("Dropping existing tables...")
    
    try:
        with psycopg2.connect(CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                # Drop tables in reverse order of dependencies
                cur.execute("DROP TABLE IF EXISTS mentions;")
                cur.execute("DROP TABLE IF EXISTS status_hashtags;")
                cur.execute("DROP TABLE IF EXISTS hashtags;")
                cur.execute("DROP TABLE IF EXISTS media_attachments;")
                cur.execute("DROP TABLE IF EXISTS relationships;")
                cur.execute("DROP TABLE IF EXISTS statuses;")
                cur.execute("DROP TABLE IF EXISTS users;")
                print("✅ All tables dropped successfully")
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def create_tables():
    """Creates all necessary tables for the Mastodon server."""
    conn = None
    print("Setting up Mastodon database tables...")
    
    try:
        with psycopg2.connect(CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                # Create users table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        username VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        display_name VARCHAR(255),
                        bio TEXT,
                        avatar_url TEXT,
                        header_url TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                print("✅ Created users table")

                # Create statuses table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS statuses (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID NOT NULL REFERENCES users(id),
                        content TEXT NOT NULL,
                        visibility VARCHAR(50) DEFAULT 'public',
                        sensitive BOOLEAN DEFAULT false,
                        spoiler_text TEXT,
                        latitude DECIMAL(10, 8),
                        longitude DECIMAL(11, 8),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        INDEX (user_id),
                        INDEX (created_at)
                    );
                """)
                print("✅ Created statuses table")

                # Create media_attachments table with simplified fields
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS media_attachments (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        status_id UUID NOT NULL REFERENCES statuses(id),
                        file_path TEXT NOT NULL,
                        file_type VARCHAR(50) NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        INDEX (status_id),
                        INDEX (created_at)
                    );
                """)
                print("✅ Created media_attachments table")

                # Create relationships table (for follows, blocks, etc.)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS relationships (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        follower_id UUID NOT NULL REFERENCES users(id),
                        following_id UUID NOT NULL REFERENCES users(id),
                        relationship_type VARCHAR(50) NOT NULL, -- 'follow', 'block', etc.
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (follower_id, following_id, relationship_type),
                        INDEX (follower_id),
                        INDEX (following_id)
                    );
                """)
                print("✅ Created relationships table")

                # Create hashtags table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS hashtags (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) UNIQUE NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        INDEX (name)
                    );
                """)
                print("✅ Created hashtags table")

                # Create status_hashtags junction table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS status_hashtags (
                        status_id UUID NOT NULL REFERENCES statuses(id),
                        hashtag_id UUID NOT NULL REFERENCES hashtags(id),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (status_id, hashtag_id),
                        INDEX (hashtag_id)
                    );
                """)
                print("✅ Created status_hashtags table")

                # Create mentions table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mentions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        status_id UUID NOT NULL REFERENCES statuses(id),
                        mentioned_user_id UUID NOT NULL REFERENCES users(id),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (status_id, mentioned_user_id),
                        INDEX (status_id),
                        INDEX (mentioned_user_id)
                    );
                """)
                print("✅ Created mentions table")

                # Commit all changes
                conn.commit()
                print("\n✨ All tables created successfully!")

    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print("   Check if your CockroachDB node is running and accessible.")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def test_tables():
    """Tests the created tables by inserting and querying sample data."""
    conn = None
    print("\nTesting tables with sample data...")
    
    try:
        with psycopg2.connect(CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                # Insert test user
                cur.execute("""
                    INSERT INTO users (username, password_hash, display_name, bio)
                    VALUES ('testuser', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User', 'Test user bio')
                    ON CONFLICT (username) DO NOTHING;
                """)
                
                # Insert test status
                cur.execute("""
                    INSERT INTO statuses (user_id, content, visibility)
                    SELECT id, 'Hello, Mastodon!', 'public'
                    FROM users WHERE username = 'testuser';
                """)
                
                # Insert test media attachment
                cur.execute("""
                    INSERT INTO media_attachments (
                        status_id, file_path, file_type, description
                    )
                    SELECT s.id, '/media/test.jpg', 'image/jpeg', 'Test image'
                    FROM statuses s
                    WHERE s.content = 'Hello, Mastodon!';
                """)
                
                # Insert test hashtag
                cur.execute("""
                    INSERT INTO hashtags (name)
                    VALUES ('test')
                    ON CONFLICT (name) DO NOTHING;
                """)
                
                # Link status to hashtag
                cur.execute("""
                    INSERT INTO status_hashtags (status_id, hashtag_id)
                    SELECT s.id, h.id
                    FROM statuses s, hashtags h
                    WHERE s.content LIKE '%Mastodon%'
                    AND h.name = 'test';
                """)
                
                # Query and display results
                print("\nSample data inserted. Querying results...")
                
                # Get user count
                cur.execute("SELECT COUNT(*) FROM users;")
                user_count = cur.fetchone()[0]
                print(f"Users in database: {user_count}")
                
                # Get status count
                cur.execute("SELECT COUNT(*) FROM statuses;")
                status_count = cur.fetchone()[0]
                print(f"Statuses in database: {status_count}")
                
                # Get media attachment count
                cur.execute("SELECT COUNT(*) FROM media_attachments;")
                media_count = cur.fetchone()[0]
                print(f"Media attachments in database: {media_count}")
                
                # Get hashtag count
                cur.execute("SELECT COUNT(*) FROM hashtags;")
                hashtag_count = cur.fetchone()[0]
                print(f"Hashtags in database: {hashtag_count}")
                
                conn.commit()
                print("\n✨ Test data inserted and verified successfully!")

    except Exception as e:
        print(f"❌ An error occurred during testing: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- Run the test ---
if __name__ == "__main__":
    # Drop existing tables first
    drop_tables()
    
    # Create tables
    create_tables()
    
    # Test tables with sample data
    test_tables()