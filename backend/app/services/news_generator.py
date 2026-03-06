"""News generator — creates news items from tick activity."""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.event import Event, EventType
from app.models.gate import Gate, GateRank
from app.models.market import Trade
from app.models.news import News, NewsCategory

logger = structlog.get_logger()

RANK_IMPORTANCE: dict[GateRank, int] = {
    GateRank.E: 1,
    GateRank.D: 1,
    GateRank.C: 2,
    GateRank.B: 2,
    GateRank.A: 3,
    GateRank.S: 4,
    GateRank.S_PLUS: 5,
}


def _rank_importance(rank: GateRank) -> int:
    return RANK_IMPORTANCE.get(rank, 1)


def _news_from_event(event: Event, tick_id: int) -> News:
    payload = event.payload or {}

    headlines = {
        EventType.STABILITY_SURGE: (
            f"Stability surge! Gate {payload.get('rank', '?')}"
            f" reinforced (+{payload.get('change', '?')})"
        ),
        EventType.STABILITY_CRISIS: (
            f"Crisis! Gate {payload.get('rank', '?')}"
            f" destabilized (-{payload.get('change', '?')})"
        ),
        EventType.YIELD_BOOM: (
            f"Yield boom! Gate {payload.get('rank', '?')}"
            f" produces {payload.get('multiplier', '?')}\u00d7 bonus yield"
        ),
        EventType.MARKET_SHOCK: (
            f"Market shock! {payload.get('affected_count', '?')}"
            f" gates destabilized"
        ),
        EventType.DISCOVERY_SURGE: (
            f"Discovery surge! {payload.get('count', '?')}"
            f" new gates appeared"
        ),
    }

    importance_map = {
        EventType.STABILITY_SURGE: 3,
        EventType.STABILITY_CRISIS: 3,
        EventType.YIELD_BOOM: 3,
        EventType.MARKET_SHOCK: 4,
        EventType.DISCOVERY_SURGE: 3,
    }

    category = (
        NewsCategory.WORLD
        if event.event_type in (EventType.MARKET_SHOCK, EventType.DISCOVERY_SURGE)
        else NewsCategory.GATE
    )

    return News(
        tick_id=tick_id,
        headline=headlines[event.event_type],
        category=category,
        importance=importance_map[event.event_type],
        related_entity_type="gate" if event.target_id else None,
        related_entity_id=event.target_id,
    )


async def generate_tick_news(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    events: list[Event],
) -> list[News]:
    """Scan tick activity and create News rows."""
    news_items: list[News] = []

    # 1. News from events
    for event in events:
        news_items.append(_news_from_event(event, tick_id))

    # 2. Gate spawns this tick
    result = await session.execute(
        select(Gate).where(Gate.spawned_at_tick == tick_number)
    )
    spawned_gates = list(result.scalars().all())
    for gate in spawned_gates:
        news_items.append(
            News(
                tick_id=tick_id,
                headline=f"A Rank-{gate.rank.value} Gate has appeared!",
                category=NewsCategory.GATE,
                importance=_rank_importance(gate.rank),
                related_entity_type="gate",
                related_entity_id=gate.id,
            )
        )

    # 3. Gate collapses this tick
    result = await session.execute(
        select(Gate).where(Gate.collapsed_at_tick == tick_number)
    )
    collapsed_gates = list(result.scalars().all())
    for gate in collapsed_gates:
        news_items.append(
            News(
                tick_id=tick_id,
                headline=f"Rank-{gate.rank.value} Gate has collapsed!",
                body="All shares are now worthless. Orders have been cancelled.",
                category=NewsCategory.GATE,
                importance=max(3, _rank_importance(gate.rank)),
                related_entity_type="gate",
                related_entity_id=gate.id,
            )
        )

    # 4. Large trades this tick
    result = await session.execute(
        select(Trade).where(Trade.tick_id == tick_id)
    )
    trades = list(result.scalars().all())
    for trade in trades:
        value = trade.quantity * trade.price_micro
        if value >= settings.news_large_trade_threshold_micro:
            news_items.append(
                News(
                    tick_id=tick_id,
                    headline=(
                        f"Large trade: {trade.quantity} shares"
                        f" at {trade.price_micro} per share"
                    ),
                    category=NewsCategory.MARKET,
                    importance=2,
                    related_entity_type="trade",
                    related_entity_id=trade.id,
                )
            )

    session.add_all(news_items)
    return news_items