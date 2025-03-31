"""
Server-side HTTP Signature Verification

This module handles the verification of HTTP signatures for incoming requests
to the Mastodon server. It implements the HTTP Signatures specification
for server-side authentication.
"""

import base64
import hashlib
from typing import Dict, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

def verify_server_signature(
    method: str,
    path: str,
    headers: Dict[str, str],
    body: Optional[bytes] = None,
    public_key: str = None
) -> bool:
    """
    Verify HTTP signature for incoming request.
    
    Args:
        method: HTTP method
        path: Request path
        headers: Request headers
        body: Optional request body
        public_key: PEM-encoded public key
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Get signature header
        signature_header = headers.get('Signature')
        if not signature_header:
            return False
            
        # Parse signature header
        signature_parts = {}
        for part in signature_header.split(','):
            key, value = part.split('=', 1)
            signature_parts[key] = value.strip('"')
            
        # Get required parts
        key_id = signature_parts.get('keyId')
        algorithm = signature_parts.get('algorithm')
        headers_list = signature_parts.get('headers', '').split()
        signature = base64.b64decode(signature_parts.get('signature', ''))
        
        if not all([key_id, algorithm, headers_list, signature]):
            return False
            
        # Create signature string
        signature_string = ''
        for header in headers_list:
            if header == '(request-target)':
                signature_string += f"(request-target): {method.lower()} {path}\n"
            else:
                value = headers.get(header, '')
                signature_string += f"{header}: {value}\n"
                
        # Remove trailing newline
        signature_string = signature_string.rstrip()
        
        # Load public key
        key = load_pem_public_key(public_key.encode())
        
        # Verify signature
        key.verify(
            signature,
            signature_string.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        return True
        
    except Exception as e:
        return False 