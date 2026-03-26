from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends ,HTTPException,status
from typing import Annotated

from sqlalchemy import select
from hash import decode_acces_token
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from jwt import  PyJWTError
from models import AuthUserSchema
from database.db import get_db
from database.schema import UserSchema
from sqlalchemy.orm import Session
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def authenticate_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> AuthUserSchema:
    """
    Authenticate user by validating JWT token and fetching user from database
    """
    print(f"🔐 Authenticating token: {token[:20]}...")
    
    try:
        # Verify environment variables are set
        if not os.getenv("SECRET_KEY"):
            print("❌ ERROR: SECRET_KEY not set in environment")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error"
            )
        
        # Decode token
        try:
            payload = decode_acces_token(token)
            print(f"✅ Token decoded successfully: {payload.keys()}")
        except ExpiredSignatureError:
            print("❌ Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            print(f"❌ Token decode error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract user_id from payload
        user_id = payload.get("id")
        if user_id is None:
            print(f"❌ User ID not in token. Payload: {payload}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user id"
            )

        print(f"🔍 Looking up user with ID: {user_id}")

        # Fetch user from DB
        stmt = select(UserSchema).where(UserSchema.id == user_id)
        user = db.execute(stmt).scalar_one_or_none()

        if user is None:
            print(f"❌ User not found in database: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in database"
            )

        print(f"✅ User authenticated: {user.username}")

        return AuthUserSchema(
            id=user.id,
            username=user.username,
            email=user.email
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except PyJWTError as e:
        print(f"❌ JWT Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"❌ Unexpected auth error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
