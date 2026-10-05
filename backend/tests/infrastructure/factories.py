from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Currency
from repositories.currency import CurrencyRepository


async def make_workspace_currency(db_session: AsyncSession) -> Currency:
    """Создаёт валюту для `workspaces.currency_id` с уникальным кодом, чтобы не пересекаться со справочником."""
    currency = Currency(id=uuid4(), code=f"W{uuid4().hex[:8].upper()}", name="Валюта воркспейса", decimal_places=2)
    await CurrencyRepository(db_session).upsert_many([currency])
    await db_session.flush()
    return currency
