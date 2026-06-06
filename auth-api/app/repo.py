"""Repository functions: all DB access happens here."""
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .db import User, PasskeyCredential


async def get_user_by_email(s: AsyncSession, email: str) -> Optional[User]:
    r = await s.execute(
        select(User).where(User.email == email).options(selectinload(User.credentials))
    )
    return r.scalar_one_or_none()


async def get_user_by_id(s: AsyncSession, uid: str) -> Optional[User]:
    r = await s.execute(
        select(User).where(User.id == uid).options(selectinload(User.credentials))
    )
    return r.scalar_one_or_none()


async def get_or_create_user(s: AsyncSession, email: str) -> User:
    user = await get_user_by_email(s, email)
    if user:
        return user
    user = User(
        id=f"usr_{secrets.token_hex(8)}",
        email=email,
        created_at=datetime.now(timezone.utc),
        passkey_enabled=False,
    )
    s.add(user)
    await s.commit()
    await s.refresh(user)
    return user


async def list_credentials(s: AsyncSession, user_id: str) -> list[PasskeyCredential]:
    r = await s.execute(
        select(PasskeyCredential).where(PasskeyCredential.user_id == user_id)
    )
    return list(r.scalars())


async def get_credential_by_id(s: AsyncSession, cred_id: str) -> Optional[PasskeyCredential]:
    r = await s.execute(
        select(PasskeyCredential).where(PasskeyCredential.credential_id == cred_id)
    )
    return r.scalar_one_or_none()


async def add_credential(s: AsyncSession, user_id: str,
                          credential_id: str, public_key: bytes, sign_count: int):
    cred = PasskeyCredential(
        user_id=user_id, credential_id=credential_id,
        public_key=public_key, sign_count=sign_count,
    )
    s.add(cred)
    # Also flip the user flag
    user = await get_user_by_id(s, user_id)
    if user:
        user.passkey_enabled = True
    await s.commit()
    return cred


async def update_sign_count(s: AsyncSession, cred: PasskeyCredential, new_count: int):
    cred.sign_count = new_count
    await s.commit()
