import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.ledger import AccountEntityType, EntryType
from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount
from app.services.transfer import transfer

log = structlog.get_logger()


class AuthError(Exception):
    """Raised on authentication/registration failures."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


async def _get_treasury(session: AsyncSession) -> SystemAccount:
    """Load the treasury account."""
    result = await session.execute(
        select(SystemAccount).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    treasury = result.scalar_one_or_none()
    if treasury is None:
        raise RuntimeError("Treasury account not found — seed not run?")
    return treasury


async def register(
    session: AsyncSession,
    username: str,
    email: str,
    password: str,
) -> Player:
    """
    Register a new player and grant starting balance from treasury.
    Both operations happen in the same DB transaction.
    """
    # Check uniqueness
    existing = await session.execute(
        select(Player).where(
            (Player.username == username) | (Player.email == email)
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise AuthError("Username or email already taken")

    # Create player with zero balance
    player = Player(
        id=uuid.uuid4(),
        username=username,
        email=email,
        password_hash=hash_password(password),
        balance_micro=0,
        is_ai=False,
    )
    session.add(player)
    # Flush so player row exists for the transfer FK
    await session.flush()

    # Grant starting balance from treasury
    treasury = await _get_treasury(session)
    await transfer(
        session=session,
        from_type=AccountEntityType.SYSTEM,
        from_id=treasury.id,
        to_type=AccountEntityType.PLAYER,
        to_id=player.id,
        amount=settings.starting_balance_micro,
        entry_type=EntryType.STARTING_GRANT,
        memo=f"Starting grant for {username}",
    )

    await session.commit()
    await session.refresh(player)

    log.info("player_registered", player_id=str(player.id), username=username)
    return player


async def login(
    session: AsyncSession,
    email: str,
    password: str,
) -> dict:
    """Authenticate player, return access + refresh tokens."""
    result = await session.execute(
        select(Player).where(Player.email == email)
    )
    player = result.scalar_one_or_none()

    if player is None or not verify_password(password, player.password_hash):
        raise AuthError("Invalid email or password")

    return {
        "access_token": create_access_token(player.id),
        "refresh_token": create_refresh_token(player.id),
        "token_type": "bearer",
    }


async def refresh_access_token(
    session: AsyncSession,
    refresh_token: str,
) -> dict:
    """Validate refresh token and issue a new access token."""
    from jose import JWTError

    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise AuthError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise AuthError("Token is not a refresh token")

    player_id = payload.get("sub")
    if player_id is None:
        raise AuthError("Invalid token payload")

    result = await session.execute(
        select(Player).where(Player.id == uuid.UUID(player_id))
    )
    player = result.scalar_one_or_none()
    if player is None:
        raise AuthError("Player not found")

    return {
        "access_token": create_access_token(player.id),
        "token_type": "bearer",
    }