from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_player, get_db
from app.models.intent import Intent, IntentStatus
from app.models.player import Player
from app.schemas.intent import IntentCreate, IntentListResponse, IntentResponse

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


@router.get("/intents/me", response_model=IntentListResponse)
async def list_my_intents(
    player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List current player's intents, most recent first."""
    count_result = await db.execute(
        select(func.count(Intent.id)).where(Intent.player_id == player.id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Intent)
        .where(Intent.player_id == player.id)
        .order_by(Intent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    intents = list(result.scalars().all())

    return IntentListResponse(
        items=[IntentResponse.model_validate(i) for i in intents],
        total=total,
    )
