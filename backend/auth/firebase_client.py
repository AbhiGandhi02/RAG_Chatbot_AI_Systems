import firebase_admin
from firebase_admin import credentials, auth
import os

def init_firebase():
    """Initialize the Firebase Admin SDK using the serviceAccountKey.json"""
    # The default path is the root of the project
    cred_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "serviceAccountKey.json")
    
    # Try environment variable first, then fallback to local file
    cred_file = os.getenv("FIREBASE_CREDENTIALS", cred_path)
    
    if not firebase_admin._apps:
        if os.path.exists(cred_file):
            cred = credentials.Certificate(cred_file)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK initialized successfully.")
        else:
            print(f"⚠️ Warning: Firebase credentials not found at {cred_file}")
            print("Authentication will fail until serviceAccountKey.json is provided.")

def verify_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded payload."""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise ValueError(f"Invalid Firebase ID token: {str(e)}")
