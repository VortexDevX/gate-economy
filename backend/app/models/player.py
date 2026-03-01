import uuid

from sqlalchemy import BigInteger, Boolean, CheckConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Player(TimestampMixin, Base):
    __tablename__ = "players"
    __table_args__ = (
        CheckConstraint("balance_micro >= 0", name="ck_players_balance_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    balance_micro: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    is_ai: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )