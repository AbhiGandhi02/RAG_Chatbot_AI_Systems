import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.database import get_db
from backend.db.crud import get_user, create_user
from backend.db.models import User

# Optional fallback logic for local testing without Firebase
MOCK_TEST_USER_ID = "mock_test_user_123"

# Start the Firebase client
from backend.auth.firebase_client import verify_token, init_firebase
init_firebase()

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to verify the Firebase ID token in the Authorization header.
    If the user doesn't exist in our PostgreSQL database yet, it automatically creates them.
    """
    token = credentials.credentials
    
    try:
        # Decode the Firebase token
        decoded_token = verify_token(token)
        uid = decoded_token.get("uid")
        email = decoded_token.get("email", "")
        
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
            
        # Get or create the user in our PostgreSQL database
        db_user = await get_user(db, user_id=uid)
        if not db_user:
            db_user = await create_user(db, user_id=uid, email=email)
            print(f"Created new database user: {email} ({uid})")
            
        return db_user
        
    except ValueError as e:
        # Check if we're in a specific bypass mode for local CLI eval-harness testing
        if os.getenv("TEST_MODE") == "True" and token == "test-token":
             db_user = await get_user(db, user_id=MOCK_TEST_USER_ID)
             if not db_user:
                 db_user = await create_user(db, user_id=MOCK_TEST_USER_ID, email="test@local.dev")
             return db_user
             
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
