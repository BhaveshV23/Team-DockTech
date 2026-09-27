from typing import Any, Dict
import httpx
import jwt
from app.core.config import settings


class SupabaseAuthError(Exception):
    """Custom exception for Supabase Auth errors."""

    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SupabaseAuthVerifier:
    """Verifies Supabase JWT tokens strictly via HMAC signature or Supabase Auth REST API."""

    @property
    def jwt_secret(self) -> str:
        return settings.SUPABASE_JWT_SECRET

    @property
    def supabase_url(self) -> str:
        return settings.SUPABASE_URL

    @property
    def anon_key(self) -> str:
        return settings.SUPABASE_ANON_KEY

    def verify_token(self, token: str) -> Dict[str, Any]:
        if not token or not token.strip():
            raise SupabaseAuthError("Missing authorization token", status_code=401)

        # 1. Local HMAC Signature Verification via SUPABASE_JWT_SECRET if configured
        if self.jwt_secret:
            try:
                payload = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                auth_user_id = payload.get("sub")
                if not auth_user_id:
                    raise SupabaseAuthError(
                        "Invalid token payload: missing sub claim", status_code=401
                    )
                return {
                    "auth_user_id": auth_user_id,
                    "email": payload.get("email", ""),
                    "claims": payload,
                }
            except jwt.ExpiredSignatureError:
                raise SupabaseAuthError(
                    "Authorization token has expired", status_code=401
                )
            except jwt.InvalidTokenError as e:
                raise SupabaseAuthError(
                    f"Invalid authorization token: {str(e)}", status_code=401
                )

        # 2. Verification via Supabase Auth REST API if SUPABASE_URL & ANON_KEY are configured
        if self.supabase_url and self.anon_key:
            headers = {
                "Authorization": f"Bearer {token}",
                "apikey": self.anon_key,
            }
            url = f"{self.supabase_url.rstrip('/')}/auth/v1/user"
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        user_data = resp.json()
                        auth_user_id = user_data.get("id")
                        if not auth_user_id:
                            raise SupabaseAuthError(
                                "Invalid user object returned from Supabase Auth",
                                status_code=401,
                            )
                        return {
                            "auth_user_id": auth_user_id,
                            "email": user_data.get("email", ""),
                            "claims": user_data,
                        }
                    else:
                        raise SupabaseAuthError(
                            "Invalid or expired authorization token", status_code=401
                        )
            except httpx.RequestError as e:
                raise SupabaseAuthError(
                    f"Authentication service unreachable: {str(e)}", status_code=503
                )

        # 3. Reject unconfigured authentication safely (Never accept unverified tokens)
        raise SupabaseAuthError(
            "Authentication system unconfigured: missing verification secret or Supabase URL",
            status_code=401,
        )


auth_verifier = SupabaseAuthVerifier()
