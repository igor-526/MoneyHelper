# transfers Specification

## Purpose
Фиксирует отсутствие переводов в актуальной предметной модели и HTTP API приложения.
## Requirements
### Requirement: Отсутствие backend переводов
Backend SHALL NOT регистрировать endpoints переводов и SHALL NOT содержать таблицу `transfers` в актуальной схеме.

#### Scenario: Запрос старого endpoint
- **WHEN** клиент обращается к прежнему endpoint `/api/workspaces/{workspace_id}/transfers`
- **THEN** ресурс переводов недоступен и данные переводов не создаются
