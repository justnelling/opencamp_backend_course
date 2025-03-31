"""
Mastodon Client Package

This package provides a Mastodon client implementation for interacting
with Mastodon instances.
"""

from .client import MastodonClient
from .signature import generate_client_signature

__all__ = ['MastodonClient', 'generate_client_signature'] 