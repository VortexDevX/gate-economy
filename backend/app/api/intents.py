from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_player, get_db
from app.models.intent import Intent, IntentStatus
from app.models.player import Player
from app.schemas.intent import IntentCreate, IntentResponse

router = APIRouter(tags=["intents"])


@router.post(
    "/intents",
    response_model=IntentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_intent(
    intent_in: IntentCreate,
    player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
) -> Intent:
    """Submit a player intent for processing in the next simulation tick."""
    intent = Intent(
        player_id=player.id,
        intent_type=intent_in.intent_type,
        payload=intent_in.payload,
        status=IntentStatus.QUEUED,
    )
    db.add(intent)
    await db.commit()
    await db.refresh(intent)
    return intent