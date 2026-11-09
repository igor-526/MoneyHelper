# Исключение операций из аналитики

## Зачем
Выполнение этапа задачи docs/tasks/036_improves.md.

## Изменения
Расходы и пополнения SHALL хранить exclude_from_analytics, по умолчанию false. Аналитика исключает отмеченные операции и источники курсов; include_excluded=true включает их. В интерфейсе доступен общий переключатель, по умолчанию выключенный.

## API и БД
POST/PUT/GET transactions и topups: exclude_from_analytics. GET analytics и analytics/rates: include_excluded=false. Новая колонка transactions.exclude_from_analytics BOOLEAN NOT NULL DEFAULT false, обратимая миграция Alembic. Обычные списки операций включают отмеченные записи.

## Вне рамок
Авторизация, балансы, переводы и изменение валютной модели.
