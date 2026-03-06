"""News API — paginated news feed."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.news import News, NewsCategory
from app.schemas.news import NewsListResponse, NewsResponse

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=NewsListResponse)
async def list_news(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: NewsCategory | None = Query(None),
    min_importance: int = Query(1, ge=1, le=5),
) -> NewsListResponse:
    """Return paginated news, newest first."""
    base = select(News).where(News.importance >= min_importance)
    count_base = select(func.count(News.id)).where(
        News.importance >= min_importance
    )

    if category is not None:
        base = base.where(News.category == category)
        count_base = count_base.where(News.category == category)

    # Total count
    total_result = await db.execute(count_base)
    total = total_result.scalar_one()

    # Paginated items
    stmt = base.order_by(News.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = [
        NewsResponse.model_validate(row) for row in result.scalars().all()
    ]

    return NewsListResponse(
        items=items, total=total, limit=limit, offset=offset
    )