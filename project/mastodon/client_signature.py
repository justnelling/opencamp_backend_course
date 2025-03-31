"""
Mastodon Client Signature Module

Handles HTTP signature generation for Mastodon client requests
"""

import base64
import hashlib
from typing import Dict, Any
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

def generate_client_signature(
    method: str,
    path: str,
    body: bytes,
    private_key: Any,
    key_id: str,
    domain: str
) -> Dict[str, str]:
    """Generate HTTP signature headers for Mastodon client requests.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        body: Request body
        private_key: RSA private key
        key_id: The key ID (usually actor URL + #main-key)
        domain: The server's domain
        
    Returns:
        Dictionary of signature headers
    """
    # Calculate body digest
    body_digest = base64.b64encode(hashlib.sha256(body).digest()).decode('utf-8')
    
    # Create signature string
    date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    signature_string = f"(request-target): {method.lower()} {path}\n"
    signature_string += f"host: {domain}\n"
    signature_string += f"date: {date}\n"
    signature_string += f"digest: SHA-256={body_digest}\n"
    
    # Sign the string
    signature = private_key.sign(
        signature_string.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    # Base64 encode the signature
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    
    # Create headers
    headers = {
        'Date': date,
        'Host': domain,
        'Digest': f'SHA-256={body_digest}',
        'Signature': f'keyId="{key_id}",algorithm="rsa-sha256",headers="(request-target) host date digest",signature="{signature_b64}"'
    }
    
    return headers 