import enum
import uuid

from sqlalchemy import BigInteger, CheckConstraint, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AccountType(str, enum.Enum):
    TREASURY = "TREASURY"


class SystemAccount(TimestampMixin, Base):
    __tablename__ = "system_accounts"
    __table_args__ = (
        CheckConstraint(
            "balance_micro >= 0",
            name="ck_system_accounts_balance_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="accounttype"),
        unique=True,
        nullable=False,
    )
    balance_micro: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )