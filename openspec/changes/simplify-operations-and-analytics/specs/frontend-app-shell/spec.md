## MODIFIED Requirements

### Requirement: Защищённые маршруты приложения
Приложение SHALL иметь защищённые маршруты `/wallets`, `/categories`, `/transactions`, `/analytics` и `/settings`.
Маршрут `/transfers` SHALL NOT регистрироваться и SHALL обрабатываться как неизвестный маршрут.

#### Scenario: Старый маршрут переводов
- **WHEN** авторизованный пользователь открывает `/transfers`
- **THEN** приложение показывает стандартную страницу 404 и не выполняет запросов переводов

