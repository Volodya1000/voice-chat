# repositories/user_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User
import hashlib
from typing import Optional

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, username: str, password: str | None = None) -> User:
        pw_hash = self._hash(password) if password else None
        user = User(username=username, password=pw_hash)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_username(self, username: str) -> Optional[User]:
        q = await self.session.execute(select(User).where(User.username == username))
        return q.scalars().first()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        q = await self.session.execute(select(User).where(User.id == user_id))
        return q.scalars().first()

    async def ensure_user(self, username: str, password: str | None = None) -> User:
        existing = await self.get_by_username(username)
        if existing:
            return existing
        return await self.create_user(username, password)

    def _hash(self, raw: str) -> str:
        # простая хеш-функция; для продакшна используйте passlib/bcrypt
        if raw is None:
            return None
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
