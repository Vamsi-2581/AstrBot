from datetime import UTC, datetime
from typing import cast

from sqlalchemy import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select, update

from astrbot.core.db.po.shares import ConversationShare
from astrbot.core.db.stores.mixin import DatabaseStoreMixin, store_session


class ConversationShareStoreMixin(DatabaseStoreMixin):
    async def create_conversation_share(
        self,
        *,
        token_hash: str,
        session_id: str,
        creator: str,
        expires_at: datetime | None = None,
    ) -> ConversationShare:
        """Create a conversation share row for one hashed token."""
        async with store_session(self) as session:
            session: AsyncSession
            async with session.begin():
                share = ConversationShare(
                    token_hash=token_hash,
                    session_id=session_id,
                    creator=creator,
                    expires_at=expires_at,
                )
                session.add(share)
                await session.flush()
                await session.refresh(share)
                return share

    async def get_conversation_share_by_token_hash(
        self,
        token_hash: str,
    ) -> ConversationShare | None:
        """Return the share for a token hash, including revoked or expired rows."""
        async with store_session(self) as session:
            session: AsyncSession
            result = await session.execute(
                select(ConversationShare).where(
                    col(ConversationShare.token_hash) == token_hash
                )
            )
            return result.scalar_one_or_none()

    async def get_conversation_share(
        self,
        share_id: str,
    ) -> ConversationShare | None:
        """Return one share row by its public share id."""
        async with store_session(self) as session:
            session: AsyncSession
            result = await session.execute(
                select(ConversationShare).where(
                    col(ConversationShare.share_id) == share_id
                )
            )
            return result.scalar_one_or_none()

    async def list_conversation_shares(
        self,
        *,
        session_id: str,
        creator: str,
    ) -> list[ConversationShare]:
        """List every share owned by a creator for one session."""
        async with store_session(self) as session:
            session: AsyncSession
            result = await session.execute(
                select(ConversationShare)
                .where(
                    col(ConversationShare.session_id) == session_id,
                    col(ConversationShare.creator) == creator,
                )
                .order_by(col(ConversationShare.created_at).desc())
            )
            return list(result.scalars().all())

    async def revoke_conversation_share(self, share_id: str) -> bool:
        """Mark a share revoked. Returns whether an active share was updated."""
        async with store_session(self) as session:
            session: AsyncSession
            async with session.begin():
                result = cast(
                    CursorResult,
                    await session.execute(
                        update(ConversationShare)
                        .where(
                            col(ConversationShare.share_id) == share_id,
                            col(ConversationShare.revoked_at).is_(None),
                        )
                        .values(revoked_at=datetime.now(UTC))
                    ),
                )
                return bool(result.rowcount)
