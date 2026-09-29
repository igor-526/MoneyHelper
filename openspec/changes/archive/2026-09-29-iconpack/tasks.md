## 1. Реестр иконок (backend, core)

- [x] 1.1 `backend/src/core/icons.json` — отсортированный JSON-список из 23 бизнес-иконок (текущий состав
      `frontend/src/shared/ui/icons.ts`, без UI-иконок интерфейса)
- [x] 1.2 `backend/src/core/icons.py` — `ALLOWED_ICONS: frozenset[str]` (чтение `icons.json` при импорте модуля),
      `list_icon_names() -> list[str]` (отсортированный список)
- [x] 1.3 Unit-тесты `core/icons.py`: `ALLOWED_ICONS` содержит ожидаемые 23 имени и не содержит UI-иконок
      (settings, sun, moon, log-out, download, share, wifi-off); `list_icon_names()` возвращает отсортированный
      список без дублей

## 2. Переиспользуемый тип валидации

- [x] 2.1 `backend/src/core/schemas/icon.py` — `IconName` (`Annotated[str, AfterValidator(...)]`), проверка
      членства в `ALLOWED_ICONS`
- [x] 2.2 Unit-тесты `IconName`: временная pydantic-модель с полем `IconName` принимает известное имя без изменений
      и отклоняет неизвестное (`ValidationError`)

## 3. API

- [x] 3.1 `backend/src/api/icons.py` — `GET /api/icons` (`response_model=list[str]`, без авторизации, без
      пагинации), возвращает `list_icon_names()`
- [x] 3.2 Подключить роутер `icons` в `main.py` рядом с `currencies_router`
- [x] 3.3 API/smoke-тесты: `/api/icons` зарегистрирован (дополнение к списку в существующем smoke-тесте), ответ 200
      с полным отсортированным списком без авторизации, приложение стартует без БД

## 4. Frontend: разделение реестра и синхронизация

- [x] 4.1 `frontend/src/shared/ui/icons.ts` — разделить текущую `ICONS` на `BUSINESS_ICONS` (23 бизнес-иконки) и
      `UI_ICONS` (settings, sun, moon, log-out, download, share, wifi-off); `ICONS = { ...BUSINESS_ICONS,
      ...UI_ICONS }`; экспортировать `BUSINESS_ICON_NAMES`
- [x] 4.2 Проверить, что существующие тесты `frontend/src/shared/ui/Icon.test.tsx` проходят без изменений
      (поведение `resolveIcon`/`Icon` не поменялось)
- [x] 4.3 `frontend/src/shared/ui/icons.sync.test.ts` — читает `backend/src/core/icons.json` с диска
      (`readFileSync(resolve(process.cwd(), "../backend/src/core/icons.json"))`) и сравнивает по значению (без
      учёта порядка) с `BUSINESS_ICON_NAMES`

## 5. Документация

- [x] 5.1 Проверить, что раздел «Иконки» в `AGENTS.md` не противоречит реализации (изменений не требуется, только
      сверка)

## 6. QualityGate

- [x] 6.1 `make format`
- [x] 6.2 `make lint`
- [x] 6.3 `make test` (backend unit + smoke; frontend vitest, включая новый тест синхронизации)
