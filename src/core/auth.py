import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from pydantic import BaseModel

class APIKey(BaseModel):
    key: str
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    rate_limit_per_minute: int = 100
    rate_limit_per_hour: int = 1000

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests: Dict[str, List[datetime]] = {}
    
    def check_rate_limit(self, api_key: str, per_minute: int, per_hour: int) -> bool:
        """Check if request is within rate limits"""
        current_time = datetime.utcnow()
        
        if api_key not in self.requests:
            self.requests[api_key] = []
        
        # Clean old requests
        self.requests[api_key] = [
            req_time for req_time in self.requests[api_key]
            if current_time - req_time < timedelta(hours=1)
        ]
        
        # Count recent requests
        minute_ago = current_time - timedelta(minutes=1)
        hour_ago = current_time - timedelta(hours=1)
        
        recent_minute = len([
            req_time for req_time in self.requests[api_key]
            if req_time > minute_ago
        ])
        
        recent_hour = len([
            req_time for req_time in self.requests[api_key]
            if req_time > hour_ago
        ])
        
        # Check limits
        if recent_minute >= per_minute or recent_hour >= per_hour:
            return False
        
        # Record this request
        self.requests[api_key].append(current_time)
        return True

class AuthManager:
    """Manage API keys and authentication"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.api_keys: Dict[str, APIKey] = {}
        self.rate_limiter = RateLimiter()
        
        # Create a default API key for testing
        self._create_default_api_key()
    
    def _create_default_api_key(self):
        """Create a default API key for testing"""
        default_key = "tesseracts_demo_key_12345"
        self.api_keys[default_key] = APIKey(
            key=default_key,
            name="Demo API Key",
            created_at=datetime.utcnow(),
            rate_limit_per_minute=200,
            rate_limit_per_hour=2000
        )
    
    def generate_api_key(self, name: str, rate_limit_per_minute: int = 100) -> str:
        """Generate a new API key"""
        # Generate secure random key
        raw_key = secrets.token_urlsafe(32)
        api_key = f"tw_{raw_key}"
        
        # Store key info
        self.api_keys[api_key] = APIKey(
            key=api_key,
            name=name,
            created_at=datetime.utcnow(),
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_hour=rate_limit_per_minute * 10
        )
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> APIKey:
        """Validate an API key and return key info"""
        if not api_key or api_key not in self.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        key_info = self.api_keys[api_key]
        
        if not key_info.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is disabled"
            )
        
        # Check rate limits
        if not self.rate_limiter.check_rate_limit(
            api_key, 
            key_info.rate_limit_per_minute,
            key_info.rate_limit_per_hour
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Update last used time
        key_info.last_used = datetime.utcnow()
        
        return key_info
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        if api_key in self.api_keys:
            self.api_keys[api_key].is_active = False
            return True
        return False
    
    def list_api_keys(self) -> List[Dict[str, Any]]:
        """List all API keys (without the actual key values)"""
        return [
            {
                "name": key_info.name,
                "created_at": key_info.created_at.isoformat(),
                "last_used": key_info.last_used.isoformat() if key_info.last_used else None,
                "is_active": key_info.is_active,
                "rate_limit_per_minute": key_info.rate_limit_per_minute
            }
            for key_info in self.api_keys.values()
        ]
    
    def get_usage_stats(self, api_key: str) -> Dict[str, Any]:
        """Get usage statistics for an API key"""
        if api_key not in self.requests:
            return {"total_requests": 0, "requests_last_hour": 0, "requests_last_minute": 0}
        
        current_time = datetime.utcnow()
        requests = self.rate_limiter.requests.get(api_key, [])
        
        minute_ago = current_time - timedelta(minutes=1)
        hour_ago = current_time - timedelta(hours=1)
        
        return {
            "total_requests": len(requests),
            "requests_last_hour": len([r for r in requests if r > hour_ago]),
            "requests_last_minute": len([r for r in requests if r > minute_ago])
        }
    
    def create_jwt_token(self, api_key: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT token for an API key"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=30)
        
        payload = {
            "api_key": api_key,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_jwt_token(self, token: str) -> str:
        """Verify a JWT token and return the API key"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            api_key = payload.get("api_key")
            
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            return api_key
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate token"
            )
