"""
ActivityPub HTTP Signature Module

Handles cryptographic operations for ActivityPub protocol
"""

import hashlib
import base64
import datetime
from typing import Dict
from fastapi import Request
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding

async def generate_http_signature(request: Request, private_key, key_id: str, local_domain: str) -> Dict[str, str]:
    """Generates a simplified HTTP Signature with basic padding.
    
    Args:
        request: The FastAPI request object
        private_key: RSA private key for signing
        key_id: Key identifier string
        local_domain: The server's domain
        
    Returns:
        Dict containing Date, Digest and Signature headers
    """
    headers_to_sign = ["(request-target)", "host", "date", "digest"]
    request_target = f"{request.method.lower()} {request.url.path}"
    host = request.headers.get("host", local_domain)
    date = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Calculate hash of the request body
    body = await request.body()
    sha256_hash = hashlib.sha256(body).digest()
    digest = f"SHA-256={base64.b64encode(sha256_hash).decode('utf-8')}"

    # Combine headers into a single signed string
    signed_string = f"(request-target): {request_target}\nhost: {host}\ndate: {date}\ndigest: {digest}"
    message = signed_string.encode("utf-8")

    # Sign the string with the private key 
    signature = private_key.sign(
        message,
        asymmetric_padding.PKCS1v15(), 
        hashes.SHA256(),  
    )

    signature_b64 = base64.b64encode(signature).decode("utf-8")
    headers = f'keyId="{key_id}",headers="{" ".join(headers_to_sign)}",signature="{signature_b64}"'

    return {"Date": date, "Digest": digest, "Signature": headers}