"""Helpers for constructing tokens that follow Supabase's access-token contract."""

from time import time

import jwt

TEST_SUPABASE_URL = "https://docktech-test.supabase.co"
TEST_SUPABASE_ISSUER = f"{TEST_SUPABASE_URL}/auth/v1"


def supabase_test_claims(claims):
    return {
        **claims,
        "iss": TEST_SUPABASE_ISSUER,
        "aud": "authenticated",
        "exp": claims.get("exp", int(time()) + 3600),
    }


def supabase_test_token(secret, claims):
    return jwt.encode(supabase_test_claims(claims), secret, algorithm="HS256")
