"""
ActivityPub Signature Verification

This module handles HTTP signature verification for ActivityPub.
"""

import re
import logging
from typing import Dict, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_signature_header(header: str) -> Dict[str, str]:
    """
    Parse HTTP signature header.
    
    Args:
        header: Signature header value
        
    Returns:
        Dictionary of signature parameters
    """
    params = {}
    for param in header.split(','):
        key, value = param.split('=', 1)
        params[key.strip()] = value.strip('"')
    return params

def get_public_key(key_id: str) -> Optional[bytes]:
    """
    Get public key from key ID.
    
    Args:
        key_id: Key ID URL
        
    Returns:
        Public key bytes
    """
    try:
        response = requests.get(key_id)
        if response.status_code == 200:
            data = response.json()
            return data['publicKey']['publicKeyPem'].encode()
        return None
    except Exception as e:
        logger.error(f"Failed to get public key: {e}")
        return None

def verify_server_signature(request_body: bytes, signature_header: str,
                          date_header: str) -> bool:
    """
    Verify HTTP signature.
    
    Args:
        request_body: Request body bytes
        signature_header: Signature header value
        date_header: Date header value
        
    Returns:
        bool: True if signature is valid
    """
    try:
        # Parse signature header
        params = parse_signature_header(signature_header)
        
        # Get required parameters
        key_id = params.get('keyId')
        signature = params.get('signature')
        algorithm = params.get('algorithm')
        headers = params.get('headers', '').split(' ')
        
        if not all([key_id, signature, algorithm, headers]):
            logger.error("Missing required signature parameters")
            return False
            
        # Get public key
        public_key_pem = get_public_key(key_id)
        if not public_key_pem:
            logger.error("Failed to get public key")
            return False
            
        # Load public key
        public_key = serialization.load_pem_public_key(public_key_pem)
        
        # Create signature string
        signature_string = ''
        for header in headers:
            if header == '(request-target)':
                signature_string += '(request-target): post /inbox\n'
            elif header == 'date':
                signature_string += f'date: {date_header}\n'
            elif header == 'host':
                signature_string += f'host: example.com\n'
            elif header == 'content-type':
                signature_string += 'content-type: application/activity+json\n'
            elif header == 'digest':
                # Calculate digest
                digest = hashes.Hash(hashes.SHA256())
                digest.update(request_body)
                digest_value = digest.finalize()
                signature_string += f'digest: SHA-256={digest_value.hex()}\n'
                
        # Remove trailing newline
        signature_string = signature_string.rstrip('\n')
        
        # Verify signature
        try:
            public_key.verify(
                bytes.fromhex(signature),
                signature_string.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False 