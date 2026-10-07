## REMOVED Requirements

### Requirement: Backend переводов между кошельками
**Reason**: Операция «Перевод» больше не используется, а приложение не ведёт остатки средств.
**Migration**: Все endpoints `/api/workspaces/{workspace_id}/transfers...`, таблица `transfers`, доменная сущность,
сервис, протокол, repository и зависимости удаляются. Существующие строки удаляются без переноса.

