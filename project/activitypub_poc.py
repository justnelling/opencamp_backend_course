'''
ActivityPub POC

Sets up an ActivityPub server with a local domain and hosts a single Actor.

This server has the ability to receive text-based post uploads from the Actor in its outbox. 


Adapted the implementation from: https://blog.joinmastodon.org/2018/06/how-to-implement-a-basic-activitypub-server/
'''

import json, datetime, hashlib, base64
from flask import Flask, request, jsonify 
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding

app = Flask(__name__)

# Actor config (local)
local_domain = "127.0.0.1:5000"
actor_name = "beebo"
actor_id = f"https://{local_domain}/users/{actor_name}"
display_name = "Beebo Baggins"

# dummy db: var to store our post
last_activity = None

'''
Crytography setup

- AP uses public/private keys to sign and verify messages
- Messages are signed to verify authenticity of the sender
- Public key is shared with other servers 
- Private key is used to sign outgoing messages
'''
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

public_key = private_key.public_key()
public_key_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

def generate_http_signature(request, private_key, key_id):
    """Generates a simplified HTTP Signature with basic padding."""

    headers_to_sign = ["(request-target)", "host", "date", "digest"]
    request_target = f"{request.method.lower()} {request.path}"
    host = request.headers["Host"]
    date = datetime.datetime.now(datetime.UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Calculate hash of the request body
    sha256_hash = hashlib.sha256(request.data).digest()
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

@app.route(f"/users/{actor_name}", methods=["GET"])
def actor():
    '''Returns the actor's profile'''
    actor_data = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
		    "https://w3id.org/security/v1"
        ],
        "id": actor_id,
        "type": "Person",
        "name": display_name,
        "preferredUsername": actor_name,
        "inbox": f"{actor_id}/inbox",
        "outbox": f"{actor_id}/outbox",
        "publicKey": {
            "id": f"{actor_id}#main-key",
            "owner": actor_id,
            "publicKeyPem": public_key_pem
        }
    }

    return jsonify(actor_data) 

@app.route(f"/users/{actor_name}/inbox", methods=["POST"])
def inbox():
    '''Handles incoming activities from rest of world -> our Actor'''
    activity = request.get_json()
    if activity['type'] == 'Create':
        print(f"Received note: {activity['object']['content']}")
        return jsonify({'message': 'Activity Received'}), 202
    else:
        return jsonify({'message': 'Activity type not supported'}), 400

@app.route(f"/users/{actor_name}/outbox", methods=["POST"])
def outbox():
    '''
    Handles outgoing activities from our Actor -> rest of the world
    +
    Defines activity created by our Actor in this server 
    '''
    activity = request.get_json()

    # write to our dummy db
    global last_activity
    last_activity = activity

    headers = generate_http_signature(request, private_key, f"{actor_id}#main-key")

    response = app.response_class(
        response=json.dumps(activity),
        status=202,
        mimetype='application/activity+json'
    )
    for key, value in headers.items():
        response.headers[key] = value
    
    return response

@app.route(f"/users/{actor_name}/outbox", methods=["GET"])
def outbox_get():
    '''Simulates fetching from outbox
    
    for simplicity we're just reading from `last_activity` global var instead of an actual DB
    '''
    global last_activity
    if last_activity:
        content = last_activity['object']['content']
        print("Content from outbox:", content)
        return jsonify(last_activity)
    else:
        return jsonify({'message': 'Outbox is empty'}), 404

@app.route("/.well-known/webfinger")
def webfinger():
    '''
    webfinger serves as a routing protocol / naming convention for activitypub

    This is the endpoint other servers would call to find our server's Actor / users
    '''
    resource = request.args.get('resource')
    if resource and resource == f"acct:{actor_name}@{local_domain}":
        webfinger_response = {
            'subject': resource,
            'links': [
                {
                    'rel': 'self',
                    'type': 'application/activity+json',
                    'href': actor_id
                }
            ],
        }
        return jsonify(webfinger_response)
    else:
        return jsonify({'error': 'Resource not found'}), 404
    
def send_text_post(content):
    '''Creates and sends a text-basedpost (Create activity)'''

    post_id = f"{actor_id}/post/example-post"
    activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": post_id,
        "type": "Create",
        "actor": actor_id,
        "object": {
            "id": post_id,
            "type": "Note",
            "content": content,
            "published": datetime.datetime.now(datetime.UTC).isoformat(),
            "attributedTo": actor_id,
            "to": ["https://www.w3.org/ns/activitystreams#Public"] # everyone can see
        }
    }

    with app.test_client() as client:
        response = client.post(f"/users/{actor_name}/outbox", json=activity) 
        print(f"Post sent. Response: {response.status_code}")
    
if __name__ == "__main__":
    app.run(debug=True, port=5000)
    send_text_post("Hello world")
     # need to push app context to use jsonify
    with app.app_context():
        print(outbox_get())