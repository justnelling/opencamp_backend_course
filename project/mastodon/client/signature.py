"""
Client-side HTTP Signature Generation

This module handles the generation of HTTP signatures for outgoing requests
to Mastodon instances. It implements the HTTP Signatures specification
for client-side authentication.
"""

import base64
import hashlib
from typing import Dict, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key

def generate_client_signature(
    method: str,
    path: str,
    body: Optional[bytes] = None,
    private_key: str = None,
    key_id: str = None,
    domain: str = None
) -> Dict[str, str]:
    """
    Generate HTTP signature headers for client request.
    
    Args:
        method: HTTP method (e.g., GET, POST)
        path: Request path
        body: Optional request body
        private_key: PEM-encoded private key
        key_id: Key ID for signature
        domain: Domain for signature
        
    Returns:
        Dict containing signature headers
    """
    # Create digest of body if present
    digest = None
    if body:
        digest = base64.b64encode(
            hashlib.sha256(body).digest()
        ).decode()
        
    # Create signature string
    signature_string = f"(request-target): {method.lower()} {path}\n"
    signature_string += f"host: {domain}\n"
    if digest:
        signature_string += f"digest: SHA-256={digest}\n"
    signature_string += f"date: {key_id}"
    
    # Load private key
    key = load_pem_private_key(
        private_key.encode(),
        password=None
    )
    
    # Sign the string
    signature = key.sign(
        signature_string.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    # Base64 encode signature
    signature_b64 = base64.b64encode(signature).decode()
    
    # Create headers
    headers = {
        'Host': domain,
        'Date': key_id,
        'Signature': (
            f'keyId="{key_id}",algorithm="rsa-sha256",'
            f'headers="(request-target) host date'
        )
    }
    
    if digest:
        headers['Digest'] = f'SHA-256={digest}'
        headers['Signature'] += ' digest",'
    else:
        headers['Signature'] += '"'
        
    headers['Signature'] += f',signature="{signature_b64}"'
    
    return headers 