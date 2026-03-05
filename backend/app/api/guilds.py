"""Guild API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.guild import (
    Guild,
    GuildGateHolding,
    GuildMember,
    GuildShare,
    GuildStatus,
)
from app.schemas.guild import (
    GuildDetailResponse,
    GuildGateHoldingOut,
    GuildListResponse,
    GuildMemberOut,
    GuildResponse,
)

router = APIRouter(prefix="/guilds", tags=["guilds"])


@router.get("", response_model=GuildListResponse)
async def list_guilds(
    status: str | None = Query(None, description="Filter by status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List guilds with optional status filter and pagination."""
    query = select(Guild)
    count_query = select(func.count(Guild.id))

    if status is not None:
        try:
            status_enum = GuildStatus(status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")
        query = query.where(Guild.status == status_enum)
        count_query = count_query.where(Guild.status == status_enum)

    result = await db.execute(count_query)
    total = result.scalar_one()

    result = await db.execute(
        query.order_by(Guild.created_at_tick.desc())
        .offset(offset)
        .limit(limit)
    )
    guilds = result.scalars().all()

    return GuildListResponse(
        guilds=[GuildResponse.model_validate(g) for g in guilds],
        total=total,
    )


@router.get("/{guild_id}", response_model=GuildDetailResponse)
async def get_guild(
    guild_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get guild detail including members, gate holdings, and shareholder count."""
    result = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild = result.scalar_one_or_none()
    if guild is None:
        raise HTTPException(404, "Guild not found")

    # Members
    result = await db.execute(
        select(GuildMember).where(GuildMember.guild_id == guild_id)
    )
    members = [
        GuildMemberOut(
            player_id=m.player_id,
            role=m.role.value,
            joined_at_tick=m.joined_at_tick,
        )
        for m in result.scalars().all()
    ]

    # Gate holdings
    result = await db.execute(
        select(GuildGateHolding).where(
            GuildGateHolding.guild_id == guild_id,
            GuildGateHolding.quantity > 0,
        )
    )
    gate_holdings = [
        GuildGateHoldingOut(gate_id=h.gate_id, quantity=h.quantity)
        for h in result.scalars().all()
    ]

    # Shareholder count (exclude guild self-held shares)
    result = await db.execute(
        select(func.count(GuildShare.player_id)).where(
            GuildShare.guild_id == guild_id,
            GuildShare.player_id != guild_id,
            GuildShare.quantity > 0,
        )
    )
    shareholder_count = result.scalar_one()

    return GuildDetailResponse(
        id=guild.id,
        name=guild.name,
        founder_id=guild.founder_id,
        treasury_micro=guild.treasury_micro,
        total_shares=guild.total_shares,
        public_float_pct=float(guild.public_float_pct),
        dividend_policy=guild.dividend_policy.value,
        auto_dividend_pct=(
            float(guild.auto_dividend_pct)
            if guild.auto_dividend_pct is not None
            else None
        ),
        status=guild.status.value,
        created_at_tick=guild.created_at_tick,
        maintenance_cost_micro=guild.maintenance_cost_micro,
        members=members,
        gate_holdings=gate_holdings,
        shareholder_count=shareholder_count,
    )