"""JWT verification for Core service tokens"""

import os
import jwt
from typing import Optional, Dict
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

logger = structlog.get_logger()

# Get JWT public key from environment
JWT_PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "RS256")

security = HTTPBearer()


def verify_jwt(token: str) -> Dict:
    """
    Verify JWT token from Core service.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload with user_id, scopes, etc.
        
    Raises:
        HTTPException: If token is invalid, expired, or missing required claims
    """
    if not JWT_PUBLIC_KEY:
        logger.error("jwt_public_key_missing")
        raise HTTPException(
            status_code=500,
            detail="JWT verification not configured"
        )
    
    try:
        # Decode and verify token
        payload = jwt.decode(
            token,
            JWT_PUBLIC_KEY,
            algorithms=[JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": False,  # Adjust based on Core service requirements
            }
        )
        
        # Validate required claims
        if "user_id" not in payload:
            logger.warning("jwt_missing_user_id", payload_keys=list(payload.keys()))
            raise HTTPException(
                status_code=401,
                detail="Token missing required claim: user_id"
            )
        
        logger.info("jwt_verified", user_id=payload.get("user_id"))
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("jwt_expired")
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning("jwt_invalid", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error("jwt_verification_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Token verification failed"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict:
    """
    FastAPI dependency to get current authenticated user from JWT.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        Decoded JWT payload with user information
    """
    token = credentials.credentials
    return verify_jwt(token)

