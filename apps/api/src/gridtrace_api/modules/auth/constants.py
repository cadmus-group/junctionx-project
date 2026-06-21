"""Shared demo login credentials (seeded by migration 0004 and bootstrap)."""

from __future__ import annotations

DEMO_OPERATOR_ID = "user-12345"
DEMO_OPERATOR_USERNAME = "demo_operator"
DEMO_OPERATOR_NAME = "Demo Operator"
DEMO_OPERATOR_ROLE = "operator"

# bcrypt hash for password "SuperSecret123!" (rounds=12)
DEMO_OPERATOR_PASSWORD_HASH = (
    "$2b$12$uJVI9cBy.BaJVjpkZx6LU.ZWrZC.PYiec4tkK2eB7yjnPb8tl2DRO"
)
