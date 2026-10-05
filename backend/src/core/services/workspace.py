from uuid import UUID

from core.entities import Workspace
from core.exceptions import ClientError, ConflictError, NotFoundError
from core.protocols import Clock, CurrencyRepository, IdGenerator, WalletCounter, WorkspaceRepository

NOT_FOUND_MESSAGE = "Воркспейс не найден"
CURRENCY_LOCKED_MESSAGE = "Нельзя сменить валюту воркспейса, в котором есть кошельки"


class WorkspaceService:
    def __init__(
        self,
        workspaces: WorkspaceRepository,
        currencies: CurrencyRepository,
        wallets: WalletCounter,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._workspaces = workspaces
        self._currencies = currencies
        self._wallets = wallets
        self._clock = clock
        self._ids = ids

    async def create_workspace(self, user_id: UUID, *, name: str, currency_id: UUID) -> Workspace:
        await self._ensure_currency_exists(currency_id)
        workspace = Workspace(
            id=self._ids.new(), user_id=user_id, name=name, currency_id=currency_id, created_at=self._clock.now()
        )
        return await self._workspaces.add(workspace)

    async def get_workspace(self, workspace_id: UUID, user_id: UUID) -> Workspace:
        workspace = await self._workspaces.get_by_id(workspace_id, user_id)
        if workspace is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return workspace

    async def list_workspaces(self, user_id: UUID, *, limit: int, offset: int) -> tuple[list[Workspace], int]:
        items = await self._workspaces.list(user_id, limit=limit, offset=offset)
        total = await self._workspaces.count(user_id)
        return items, total

    async def update_workspace(
        self, workspace_id: UUID, user_id: UUID, *, name: str, currency_id: UUID | None = None
    ) -> Workspace:
        current = await self.get_workspace(workspace_id, user_id)
        new_currency_id = current.currency_id if currency_id is None else currency_id
        if new_currency_id != current.currency_id:
            await self._ensure_currency_exists(new_currency_id)
            if await self._wallets.count(workspace_id) > 0:
                raise ConflictError(CURRENCY_LOCKED_MESSAGE)
        workspace = await self._workspaces.update(
            workspace_id, user_id, name=name, currency_id=new_currency_id, now=self._clock.now()
        )
        if workspace is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return workspace

    async def delete_workspace(self, workspace_id: UUID, user_id: UUID) -> None:
        deleted = await self._workspaces.delete(workspace_id, user_id)
        if not deleted:
            raise NotFoundError(NOT_FOUND_MESSAGE)

    async def _ensure_currency_exists(self, currency_id: UUID) -> None:
        if await self._currencies.missing_ids([currency_id]):
            raise ClientError(f"Неизвестный currency_id: {currency_id}")
