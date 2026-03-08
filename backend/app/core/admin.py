from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_player
from app.models.player import Player, PlayerRole


async def require_admin(
    current_player: Player = Depends(get_current_player),
) -> Player:
    """Dependency that ensures the authenticated player has ADMIN role."""
    if current_player.role != PlayerRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_player


AdminPlayer = Annotated[Player, Depends(require_admin)]