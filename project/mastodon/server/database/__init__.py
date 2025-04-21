"""
Database Module

This module provides database functionality for the Mastodon server.
"""

from server.database.connection import Database

# Initialize database connection
db = Database()

__all__ = ['db'] 