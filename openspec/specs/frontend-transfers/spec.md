# frontend-transfers Specification

## Purpose
Фиксирует отсутствие маршрута, интерфейса и API-клиента переводов во frontend.
## Requirements
### Requirement: Отсутствие frontend переводов
Frontend SHALL NOT регистрировать маршрут, вкладку, формы, запросы или кэши переводов.

#### Scenario: Старый маршрут переводов
- **WHEN** пользователь открывает `/transfers`
- **THEN** отображается стандартная страница 404 без запросов к API переводов
