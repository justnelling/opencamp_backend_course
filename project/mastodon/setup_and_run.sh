#!/bin/bash

# Mastodon Setup and Run Script
# This script sets up the CockroachDB database, creates a test user,
# and starts both the server and frontend.

set -e  # Exit immediately if a command exits with a non-zero status

echo "===== Mastodon Setup and Run Script ====="
echo "This script will set up the database and start the application."
echo "Press Ctrl+C at any time to stop the script."
echo ""

# Function to check if CockroachDB is running
check_cockroachdb() {
    if ! cockroach sql --insecure --host=localhost --port=26257 -e "SELECT 1" &> /dev/null; then
        return 1
    fi
    return 0
}

# Start CockroachDB if it's not running
if ! check_cockroachdb; then
    echo "Starting CockroachDB..."
    cockroach start-single-node --insecure --background
    echo "Waiting for CockroachDB to start..."
    sleep 5
    
    # Check if CockroachDB started successfully
    if ! check_cockroachdb; then
        echo "❌ Failed to start CockroachDB. Please check the logs."
        exit 1
    fi
    echo "✅ CockroachDB started successfully."
else
    echo "✅ CockroachDB is already running."
fi

# Create the mastodon database if it doesn't exist
echo "Creating mastodon database if it doesn't exist..."
cockroach sql --insecure --host=localhost --port=26257 -e "CREATE DATABASE IF NOT EXISTS mastodon;"
echo "✅ Database created or already exists."

# Run the database setup script
echo "Running database setup script..."
cd "$(dirname "$0")"  # Change to the script's directory
python3 -m cockroachdb_setup.cockroachdb
echo "✅ Database setup completed."

# Create a test user if it doesn't exist
echo "Creating test user if it doesn't exist..."
cockroach sql --insecure --host=localhost --port=26257 --database=mastodon -e "
INSERT INTO users (username, password_hash, email, display_name)
VALUES ('testuser', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'test@example.com', 'Test User')
ON CONFLICT (username) DO NOTHING;
"
echo "✅ Test user created or already exists."
echo "Username: testuser"
echo "Password: password"

# Start the server in the background
echo "Starting the server..."
python3 -m server.main &
SERVER_PID=$!
echo "✅ Server started with PID: $SERVER_PID"

# Wait for the server to start
echo "Waiting for the server to start..."
sleep 5

# Start the frontend
echo "Starting the frontend..."
echo "The frontend will be available at http://localhost:8501"
echo "You can log in with the test user credentials:"
echo "Username: testuser"
echo "Password: password"
echo ""
echo "Press Ctrl+C to stop both the server and frontend."
echo ""

# Start the frontend
streamlit run frontend/app_our_server.py

# Cleanup function
cleanup() {
    echo "Stopping the server..."
    kill $SERVER_PID
    echo "Stopping CockroachDB..."
    cockroach quit --insecure --host=localhost --port=26257
    echo "✅ All processes stopped."
    exit 0
}

# Set up trap to catch Ctrl+C
trap cleanup SIGINT SIGTERM

# Keep the script running
wait 