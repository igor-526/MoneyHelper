# Production-миграция локального времени операций

Миграция `20261007_0013` удаляет таблицу переводов и преобразует `transactions.occurred_at` из `timestamptz` в
локальное время UTC+8 без timezone. Она использует явное `AT TIME ZONE 'Asia/Shanghai'`; timezone московского сервера
и PostgreSQL-сессии на результат не влияет.

## До развёртывания

1. Остановить старую версию backend, чтобы она не записывала строки во время несовместимой миграции.
2. Сделать полный проверенный backup PostgreSQL. Это единственный способ восстановить удаляемые переводы.
3. Сохранить результаты контрольных запросов:

   ```sql
   SELECT count(*) FROM transactions;
   SELECT count(*) FROM transaction_legs;
   SELECT id, occurred_at, occurred_at AT TIME ZONE 'Asia/Shanghai' AS expected_local
   FROM transactions
   ORDER BY occurred_at, id;
   ```

## Применение

Запустить штатную команду миграции `make be-migrate`. DDL выполняется транзакционно: ошибка преобразования откатывает
изменение типа и удаление таблицы.

## Проверка после миграции

До запуска новой версии backend проверить:

```sql
SELECT count(*) FROM transactions;
SELECT count(*) FROM transaction_legs;
SELECT id, occurred_at FROM transactions ORDER BY occurred_at, id;
SELECT data_type
FROM information_schema.columns
WHERE table_name = 'transactions' AND column_name = 'occurred_at';
SELECT to_regclass('public.transfers');
```

Количество строк и идентификаторы должны совпасть с preflight-выборкой, `occurred_at` — с `expected_local`, тип —
`timestamp without time zone`, `to_regclass` — `NULL`. При расхождении не запускать приложение и восстановить полный
backup.
