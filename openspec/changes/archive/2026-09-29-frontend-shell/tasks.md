## 1. Тип `Page<T>`

- [x] 1.1 Создать `frontend/src/shared/api/Page.ts` с интерфейсом `Page<T>` (`items`, `total`, `limit`, `offset`)
- [x] 1.2 Экспортировать `Page` из `frontend/src/shared/api/index.ts`

## 2. `CurrencyPicker`: тип, маппинг, hook

- [x] 2.1 Создать `frontend/src/shared/ui/CurrencyPicker/Currency.ts` (`CurrencyDto`, `Currency`, чистая функция `mapCurrency`) и `Currency.test.ts` (маппинг всех полей, включая `decimal_places` → `decimalPlaces`)
- [x] 2.2 Реализовать `useCurrencies` в `frontend/src/shared/ui/CurrencyPicker/useCurrencies.ts` (`useQuery`, `GET /api/currencies` через `useApiClient`, `query: { limit: 100, offset: 0 }`, ответ маппится `mapCurrency`) и `useCurrencies.test.ts` (успешная загрузка, состояние ошибки) через `FakeApiClient`

## 3. `CurrencyPicker`: компонент

- [x] 3.1 Реализовать `CurrencyPicker.tsx` (antd `Select`, дискриминированные пропы `SingleCurrencyPickerProps`/`MultipleCurrencyPickerProps` по `multiple`, состояния загрузки/ошибки/выбора по design.md)
- [x] 3.2 Написать `CurrencyPicker.test.tsx`: одиночный выбор, множественный выбор, состояние загрузки, состояние ошибки (`FakeApiClient` с исключением), отображение `code`/`name` в опциях
- [x] 3.3 Создать `frontend/src/shared/ui/CurrencyPicker/index.ts` (реэкспорт `CurrencyPicker`, `useCurrencies`, `Currency`) и добавить реэкспорт в `frontend/src/shared/ui/index.ts`

## 4. `IconPicker`

- [x] 4.1 Реализовать `frontend/src/shared/ui/IconPicker/IconPicker.tsx`: триггер с превью через `Icon` (или текст «Иконка не выбрана»), список `BUSINESS_ICON_NAMES` сеткой кнопок ≥ 44×44 px, переключение `Drawer`/`Modal` по `useIsMobile`, выбор-и-закрытие по тапу
- [x] 4.2 Написать `IconPicker.test.tsx`: превью выбранной иконки, состояние без выбора, `Drawer` на телефоне (мок `matchMedia`), `Modal` на широком экране, выбор иконки вызывает `onChange` и закрывает контейнер, список состоит ровно из `BUSINESS_ICON_NAMES`
- [x] 4.3 Создать `frontend/src/shared/ui/IconPicker/index.ts` и добавить реэкспорт в `frontend/src/shared/ui/index.ts`

## 5. `MoneyInput`

- [x] 5.1 Реализовать чистую функцию `isValidMoneyAmount` в `frontend/src/shared/ui/MoneyInput/moneyInput.ts` и `moneyInput.test.ts` (цифры и точка, не более одной точки, ограничение `decimalPlaces`, промежуточные состояния вида `"12."`, поведение без `decimalPlaces`)
- [x] 5.2 Реализовать `MoneyInput.tsx` (antd `Input`, `inputMode="decimal"`, `onChange(value: string)`, фильтрация через `isValidMoneyAmount`, шрифт ≥ 16 px из темы) — без `InputNumber`
- [x] 5.3 Написать `MoneyInput.test.tsx`: значение остаётся строкой, недопустимый символ отклоняется, вторая точка отклоняется, превышение `decimalPlaces` отклоняется, ввод работает внутри `Form.Item` (значение попадает в форму без дополнительных пропов)
- [x] 5.4 Создать `frontend/src/shared/ui/MoneyInput/index.ts` и добавить реэкспорт в `frontend/src/shared/ui/index.ts`

## 6. `EmptyState`

- [x] 6.1 Реализовать `frontend/src/shared/ui/EmptyState/EmptyState.tsx` (иконка + заголовок обязательны, `description?` и `action?: { label; onClick }` опциональны, без иллюстраций)
- [x] 6.2 Написать `EmptyState.test.tsx`: минимальный рендер, рендер с описанием, рендер с кнопкой действия и вызов `onClick`, отсутствие кнопки без `action`
- [x] 6.3 Создать `frontend/src/shared/ui/EmptyState/index.ts` и добавить реэкспорт в `frontend/src/shared/ui/index.ts`

## 7. QualityGate

- [x] 7.1 `make format`
- [x] 7.2 `make lint`
- [x] 7.3 `make test`
- [x] 7.4 `openspec validate frontend-shell --strict` и `openspec validate --all --strict`
