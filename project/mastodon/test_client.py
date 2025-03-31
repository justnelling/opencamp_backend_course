"""
Mastodon Client Test Script

Demonstrates how to use the Mastodon client with a live server (read-only)
"""

import asyncio
from .client import MastodonClient
# Removed key generation imports as we are not signing
# from cryptography.hazmat.primitives import serialization
# from cryptography.hazmat.primitives.asymmetric import rsa
# import base64

# Removed key generation function
# async def generate_test_keys(): ...

async def main():
    """Main test function."""
    # Removed key generation call
    # private_key, public_pem = await generate_test_keys()
    
    # Initialize client with live server URL and NO credentials
    live_instance_url = "https://mastodon.social"
    target_user = "Gargron@mastodon.social" # User on the live instance
    target_user_short = "Gargron" # Username part for timeline
    
    client = MastodonClient(
        instance_url=live_instance_url
        # No private_key, key_id, or domain provided
    )
    
    print(f"--- Testing against live server: {live_instance_url} ---")
    
    try:
        # Test getting user information
        print(f"\nTesting user information retrieval for {target_user}...")
        try:
            user = await client.get_actor(target_user)
            print(f"Retrieved user: {user.get('name', 'N/A')} ({user.get('preferredUsername', 'N/A')})")
            print(f"Actor URL: {user.get('id')}")
        except Exception as e:
            print(f"Could not retrieve user info: {e}")

        # Test getting public timeline
        print("\nTesting public timeline retrieval...")
        try:
            timeline = await client.get_public_timeline(limit=5)
            print(f"Retrieved {len(timeline)} statuses from public timeline")
            for status in timeline:
                # Mastodon API returns content directly, ActivityPub might be nested
                content = status.get('content', status.get('object', {}).get('content', '[No Content]'))
                account = status.get('account', {})
                print(f"- @{account.get('acct', 'unknown')}: {content[:100]}...") # Shorten content
        except Exception as e:
            print(f"Could not retrieve public timeline: {e}")

        # Test getting hashtag timeline (e.g., #fediverse)
        test_hashtag = "fediverse"
        print(f"\nTesting hashtag timeline retrieval (#{test_hashtag})...")
        try:
            hashtag_timeline = await client.get_hashtag_timeline(test_hashtag, limit=5)
            print(f"Retrieved {len(hashtag_timeline)} statuses with #{test_hashtag}")
            # Similar display logic as public timeline
        except Exception as e:
            print(f"Could not retrieve hashtag timeline: {e}")

        # --- Authentication Required Tests (Commented Out) ---
        # print("\nSkipping status creation (requires auth)...")
        # # Test creating a new status (Requires Authentication - will fail)
        # # print("\nTesting status creation...")
        # # new_status = await client.create_note(
        # #     content="Hello from the test client! #python",
        # #     visibility="public"
        # # )
        # # print(f"Created new status: {new_status['content']}")
        
        print(f"\nAttempting user timeline retrieval for {target_user_short} (may require auth/fail)...")
        # Test getting user timeline (May require Authentication/Signatures depending on server config)
        try:
            # Note: Using the short username here assumes the client can resolve it
            # The client.get_user_timeline fetches the actor first, then the outbox.
            user_timeline = await client.get_user_timeline(target_user, limit=5) # Use full target_user here
            # The API now returns a list directly, not a dictionary
            print(f"Retrieved {len(user_timeline)} statuses from user timeline")
            # Iterate through the list of statuses
            for status in user_timeline:
                content = status.get('content', '[No Content]')
                account = status.get('account', {})
                print(f"- @{account.get('acct', 'unknown')}: {content[:100]}...")
        except Exception as e:
            print(f"Could not retrieve user timeline for {target_user}: {e}")
        
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 