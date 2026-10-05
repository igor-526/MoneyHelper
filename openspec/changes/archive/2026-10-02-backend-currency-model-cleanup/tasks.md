## 1. Поиск остатков старой модели

- [x] 1.1 Поиск `currency_ids`, `wallet_currencies`, «ног по каждой валюте», «общая валюта», баланс списком в коде, тестах, seed, документации, specs; зафиксировать результат
- [x] 1.2 Переименовать `get_currency_ids` → `get_currency_id_by_wallet` (протокол, репозиторий, fake, `AnalyticsService`, тесты)

## 2. Документация

- [x] 2.1 AGENTS.md: переписать раздел «Деньги и валюты» под новую модель
- [x] 2.2 README.md: убрать описание многовалютного кошелька, описать новую модель
- [x] 2.3 `openspec/config.yaml`: переписать context
- [x] 2.4 Основные specs `wallets`, `transactions`, `transfers`, `analytics`: исправить вводные разделы; сверить требования с кодом
- [x] 2.5 `docs/tasks/002_roadmap.md`: убрать устаревшие решения (пополнение/«общая валюта»), отметить 030

## 3. Миграции

- [x] 3.1 На чистой временной БД: `upgrade head`, `downgrade 0009`, `upgrade head`, `downgrade base`, `upgrade head`; удалить БД

## 4. QualityGate

- [x] 4.1 `make format`, `make lint`, `make test`, `make test-infra` проходят; backend smoke проходит
