## 1. Backend

- [x] 1.1 `DayDimension`, `LegRecord.occurred_at`, часовой пояс в `AnalyticsDimension`/сервисе/схеме запроса
- [x] 1.2 Тесты: unit (сутки в поясе) и API (`group_by=day`, неизвестный пояс)

## 2. Frontend

- [x] 2.1 `FiltersDialog`, окно фильтров операций переведено на него
- [x] 2.2 `spendingFilters`, `SpendingFiltersPopup`, `dailySpending`, `SpendingChart`, `SpendingMode`, строка в `ANALYTICS_MODES`
- [x] 2.3 Тесты режима, фильтров и ряда по дням

## 3. Проверка

- [x] 3.1 `make format`, `make lint`, `make test`
