from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from core.entities import Category, CategoryType, Transaction, TransactionLeg, Wallet
from core.exceptions import ClientError, NotFoundError
from core.protocols import (
    CategoryRepository,
    Clock,
    CurrencyRepository,
    IdGenerator,
    TopupLegsRule,
    TransactionRepository,
    WalletRepository,
    WorkspaceCurrencyReader,
)
from core.services.money_validation import validate_leg_amount
from core.services.transaction_kind import get_of_type

NOT_FOUND_MESSAGE = "Пополнение не найдено"
WORKSPACE_NOT_FOUND_MESSAGE = "Воркспейс не найден"
WALLET_NOT_FOUND_MESSAGE = "Кошелёк не найден"
CATEGORY_NOT_FOUND_MESSAGE = "Категория не найдена"


class TopupService:
    def __init__(
        self,
        transactions: TransactionRepository,
        wallets: WalletRepository,
        categories: CategoryRepository,
        currencies: CurrencyRepository,
        workspaces: WorkspaceCurrencyReader,
        legs_rules: Sequence[TopupLegsRule],
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._transactions = transactions
        self._wallets = wallets
        self._categories = categories
        self._currencies = currencies
        self._workspaces = workspaces
        self._legs_rules = legs_rules
        self._clock = clock
        self._ids = ids

    async def create_topup(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        legs: Sequence[TransactionLeg],
        occurred_at: datetime | None,
        comment: str | None = None,
    ) -> Transaction:
        await self._validate_topup_input(workspace_id, wallet_id=wallet_id, category_id=category_id, legs=legs)
        now = self._clock.now()
        topup = Transaction(
            id=self._ids.new(),
            workspace_id=workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=tuple(legs),
            occurred_at=occurred_at if occurred_at is not None else now,
            comment=comment,
            created_at=now,
        )
        return await self._transactions.add(topup)

    async def get_topup(self, topup_id: UUID, workspace_id: UUID) -> Transaction:
        topup = await get_of_type(self._transactions, self._categories, topup_id, workspace_id, CategoryType.INCOME)
        if topup is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return topup

    async def list_topups(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        category_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Transaction], int]:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ClientError("date_from не может быть позже date_to")
        items = await self._transactions.list(
            workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            type=CategoryType.INCOME,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        total = await self._transactions.count(
            workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            type=CategoryType.INCOME,
            date_from=date_from,
            date_to=date_to,
        )
        return items, total

    async def update_topup(
        self,
        topup_id: UUID,
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        legs: Sequence[TransactionLeg],
        occurred_at: datetime | None,
        comment: str | None = None,
    ) -> Transaction:
        await self.get_topup(topup_id, workspace_id)
        await self._validate_topup_input(workspace_id, wallet_id=wallet_id, category_id=category_id, legs=legs)
        now = self._clock.now()
        topup = await self._transactions.update(
            topup_id,
            workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=tuple(legs),
            occurred_at=occurred_at if occurred_at is not None else now,
            comment=comment,
            now=now,
        )
        if topup is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return topup

    async def delete_topup(self, topup_id: UUID, workspace_id: UUID) -> None:
        await self.get_topup(topup_id, workspace_id)
        deleted = await self._transactions.delete(topup_id, workspace_id)
        if not deleted:
            raise NotFoundError(NOT_FOUND_MESSAGE)

    async def _validate_topup_input(
        self, workspace_id: UUID, *, wallet_id: UUID, category_id: UUID, legs: Sequence[TransactionLeg]
    ) -> None:
        wallet = await self._wallets.get_by_id(wallet_id, workspace_id)
        if wallet is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        category = await self._categories.get_by_id(category_id, workspace_id)
        if category is None:
            raise NotFoundError(CATEGORY_NOT_FOUND_MESSAGE)
        self._ensure_income_category(category)
        await self._ensure_legs_match_currencies(workspace_id, wallet, legs)
        for leg in legs:
            await validate_leg_amount(self._currencies, leg.currency_id, leg.amount)

    @staticmethod
    def _ensure_income_category(category: Category) -> None:
        if category.type is not CategoryType.INCOME:
            raise ClientError("Пополнение возможно только с категорией дохода")

    async def _ensure_legs_match_currencies(
        self, workspace_id: UUID, wallet: Wallet, legs: Sequence[TransactionLeg]
    ) -> None:
        workspace_currency_id = await self._workspaces.get_currency_id(workspace_id)
        if workspace_currency_id is None:
            raise NotFoundError(WORKSPACE_NOT_FOUND_MESSAGE)
        leg_currency_ids = [leg.currency_id for leg in legs]
        if len(leg_currency_ids) != len(set(leg_currency_ids)):
            raise ClientError("Валюта в пополнении указана более одного раза")
        rule = next(rule for rule in self._legs_rules if rule.applies(workspace_currency_id, wallet.currency_id))
        required = rule.required_currency_ids(workspace_currency_id, wallet.currency_id)
        actual = frozenset(leg_currency_ids)
        if actual == required:
            return
        parts = []
        if required - actual:
            parts.append(f"отсутствуют ноги для валют: {await self._currency_codes_text(required - actual)}")
        if actual - required:
            parts.append(f"лишние валюты в ногах: {await self._currency_codes_text(actual - required)}")
        raise ClientError("; ".join(parts))

    async def _currency_codes_text(self, currency_ids: frozenset[UUID]) -> str:
        codes = []
        for currency_id in currency_ids:
            currency = await self._currencies.get_by_id(currency_id)
            codes.append(currency.code if currency is not None else str(currency_id))
        return ", ".join(sorted(codes))
