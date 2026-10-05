from uuid import UUID

from core.entities import CategoryType, Transaction
from core.protocols import CategoryRepository, TransactionRepository


async def get_of_type(
    transactions: TransactionRepository,
    categories: CategoryRepository,
    transaction_id: UUID,
    workspace_id: UUID,
    type: CategoryType,
) -> Transaction | None:
    """Операция воркспейса, чья категория имеет тип `type`; пополнение и расход различаются типом категории."""
    transaction = await transactions.get_by_id(transaction_id, workspace_id)
    if transaction is None:
        return None
    category = await categories.get_by_id(transaction.category_id, workspace_id)
    return transaction if category is not None and category.type is type else None
