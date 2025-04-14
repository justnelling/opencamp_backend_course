"""
Authentication Models

This module defines the data models for authentication.
"""

from pydantic import BaseModel

class Token(BaseModel):
    """Model for JWT token response."""
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    """Model for login request."""
    username: str
    password: str

class AccountCreate(BaseModel):
    """Model for account creation request."""
    username: str
    password: str
    email: str 