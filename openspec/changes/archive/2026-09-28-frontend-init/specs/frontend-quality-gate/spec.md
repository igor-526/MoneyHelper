## ADDED Requirements

### Requirement: Команды QualityGate покрывают frontend
Корневые `make format`, `make lint` и `make test` SHALL выполнять и backend, и frontend. `make format` MUST запускать Prettier и автоисправления ESLint; `make lint` — проверки ESLint, Prettier (без записи) и `tsc --noEmit`; `make test` — unit-тесты Vitest без сети и без backend.

#### Scenario: Проверка форматирования
- **WHEN** файл frontend не соответствует Prettier
- **THEN** `make lint` завершается с ненулевым кодом, а `make format` исправляет файл

#### Scenario: Ошибка типов
- **WHEN** в коде frontend есть ошибка типов
- **THEN** `make lint` завершается с ненулевым кодом

#### Scenario: Тесты без backend
- **WHEN** backend не запущен и сети нет
- **THEN** `make test` проходит

### Requirement: Тесты обработки ошибок
Набор unit-тестов SHALL для каждого вида ошибки (400, 401, 403, 404, 409, 500, сетевой сбой, таймаут) проверять, что показывается toast с ожидаемым текстом и состояние действия не остаётся «загрузкой». Дополнительно MUST быть тесты нормализации `ApiError`, `useToast`, `Icon`, error boundary, темы (размеры touch-целей и шрифта) переключения layout между телефоном и широким экраном, определения и сохранения темы, конфигурации manifest и service worker (нет кэширования API), хуков `useInstallPrompt` и онлайн-статуса, баннера обновления.

#### Scenario: Покрытие видов ошибок
- **WHEN** запускается `make test`
- **THEN** выполняются тесты для каждого из перечисленных видов ошибок и проходят

### Requirement: CI для frontend
CI SHALL запускать lint, typecheck и тесты frontend отдельным job без БД и без backend.

#### Scenario: Pull request
- **WHEN** в репозиторий приходит push или pull request
- **THEN** job frontend устанавливает зависимости по lock-файлу (`npm ci`) и выполняет lint и тесты
