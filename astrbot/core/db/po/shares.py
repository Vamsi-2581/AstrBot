import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class ConversationShare(SQLModel, table=True):
    """A revocable, expiring read-only link to a conversation transcript.

    Only the token hash is stored; the raw token is returned once when the share
    is created and can never be recovered from the database.
    """

    __tablename__ = "conversation_shares"  # type: ignore

    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_column_kwargs={"autoincrement": True},
    )
    share_id: str = Field(
        max_length=36,
        nullable=False,
        unique=True,
        default_factory=lambda: str(uuid.uuid4()),
    )
    token_hash: str = Field(max_length=128, nullable=False, unique=True, index=True)
    session_id: str = Field(max_length=100, nullable=False, index=True)
    creator: str = Field(nullable=False, max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime,
    )
    expires_at: datetime | None = Field(default=None, sa_type=DateTime)
    revoked_at: datetime | None = Field(default=None, sa_type=DateTime)
