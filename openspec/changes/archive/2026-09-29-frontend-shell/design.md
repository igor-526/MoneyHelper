## Context

Backend-капабилити, нужные для разделов 014–018, уже реализованы и заархивированы: `wallets`, `categories`,
`transactions`, `transfers`, `analytics`, `currencies`, `icons`. Frontend-фундамент (`frontend-app-shell`,
`api-client`, `error-handling`, `mobile-layout`, `dark-theme`, `pwa`, `toast-notifications`) и авторизация
(`frontend-auth`) тоже готовы. Единственное, чего не хватает перед тем, как каждая из пяти оставшихся
frontend-задач начнёт рисовать свои экраны, — общий набор переиспользуемых типов и UI-компонентов, которыми эти
экраны будут пользоваться одинаково. Без него пять задач независимо изобретут пять разных способов выбрать валюту,
ввести сумму, выбрать иконку и показать пустой список — что нарушает SOLID (O: варианты должны расширяться, а не
дублироваться; S: у каждого куска — одна причина меняться).

Все решения по объёму и границам этой задачи уже приняты оркестратором в `docs/tasks/013_frontend_shell.md`
(раздел «Контекст и решения») и не пересматриваются здесь: владение навигацией остаётся за 014/016/018, `Page<T>`
заводится один раз, `MoneyInput` — строка, не `InputNumber`, `EmptyState` без иллюстраций, `IconPicker` переключает
`Drawer`/`Modal` по ширине экрана. Этот документ фиксирует точные сигнатуры и механику реализации.

## Goals / Non-Goals

**Goals:**
- Один компонент `CurrencyPicker` для одиночного и множественного выбора валюты, данные — через `useCurrencies`
  (TanStack Query, `GET /api/currencies`), без клиентской пагинации.
- Один компонент `IconPicker` для выбора из уже существующего `BUSINESS_ICON_NAMES`, с адаптивным контейнером
  выбора (`Drawer` на телефоне / `Modal` на широком экране) по единственному источнику решения — `useIsMobile`.
- `MoneyInput` — контролируемый ввод суммы, значение остаётся строкой на всём пути (компонент → форма → API),
  никогда не проходит через `Number()`/`parseFloat`.
- `EmptyState` — единый минимальный компонент пустого состояния без иллюстраций.
- `Page<T>` — единственный источник истины для формы постраничного ответа на frontend.
- Все перечисленные части покрыты тестами и соответствуют mobile-first правилам AGENTS.md.

**Non-Goals:**
- Экраны кошельков/категорий/операций/пополнений-переводов/аналитики и их навигация/маршруты (014–018).
- Мастер первичной настройки (онбординг с пустыми данными — решение дорожной карты: только `EmptyState` на каждом
  экране, не отдельный флоу).
- Ручная проверка PWA (019).
- Любые изменения backend, БД, миграций Alembic — их не будет.
- Новые бизнес-иконки в `BUSINESS_ICONS`/`BUSINESS_ICON_NAMES` — список закрыт и синхронизирован с backend
  `icons.json` тестом `icons.sync.test.ts`.

## Decisions

### Структура файлов

```
frontend/src/shared/
  api/
    Page.ts                     # тип Page<T>, экспорт из shared/api/index.ts
  ui/
    CurrencyPicker/
      Currency.ts                # Currency, CurrencyDto, mapCurrency (чистая функция)
      Currency.test.ts
      useCurrencies.ts           # useQuery(GET /api/currencies) → Currency[]
      useCurrencies.test.ts
      CurrencyPicker.tsx
      CurrencyPicker.test.tsx
      index.ts
    IconPicker/
      IconPicker.tsx
      IconPicker.test.tsx
      index.ts
    MoneyInput/
      moneyInput.ts               # isValidMoneyAmount — чистая функция фильтрации ввода
      moneyInput.test.ts
      MoneyInput.tsx
      MoneyInput.test.tsx
      index.ts
    EmptyState/
      EmptyState.tsx
      EmptyState.test.tsx
      index.ts
```

Каждый компонент — отдельная папка с презентационным компонентом, hook/чистой функцией данных отдельно от JSX
(принцип S) и тестами рядом с кодом, по образцу уже существующего `shared/ui/toast/`. `shared/api/index.ts` и
`shared/ui/index.ts` дополняются новыми экспортами по тому же принципу, что и сейчас (именованные реэкспорты).

### `Page<T>` — точное зеркало backend-схемы

```ts
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
```

Поля `Page[T]` (`core/schemas/pagination.py`) уже все в едином регистре (`items`, `total`, `limit`, `offset` —
не snake_case-специфичные имена), поэтому маппинг не нужен: JSON-ответ уже валиден как `Page<T>` без преобразования
имён полей. Дженерик `T` — тип элемента (например, `CurrencyDto`), который может сам требовать маппинга (см. ниже).

### `Currency` и маппинг `CurrencyOut` → `Currency`

Прецедента маппинга snake_case → camelCase в проекте нет: единственный похожий случай — `User` в
`features/auth/session.ts`, где поле `created_at` оставлено как есть, без преобразования (маппинга не требовалось
по спецификации задачи 005). Раз явного прецедента нет, решение принимается здесь и обосновывается:

```ts
// Форма ответа backend (CurrencyOut) — только внутренний тип, наружу компонента не выходит.
interface CurrencyDto {
  id: string;
  code: string;
  name: string;
  decimal_places: number;
}

export interface Currency {
  id: string;
  code: string;
  name: string;
  decimalPlaces: number;
}

export function mapCurrency(dto: CurrencyDto): Currency {
  return { id: dto.id, code: dto.code, name: dto.name, decimalPlaces: dto.decimal_places };
}
```

`mapCurrency` — явная чистая функция с ручным перечислением полей, а не generic camelCase-конвертер объекта
(`camelizeKeys` и т. п.). Причины:
1. **Типобезопасность.** Явная функция даёт TypeScript-ошибку компиляции при рассинхроне с `CurrencyOut`; generic
   конвертер по рекурсивным ключам типизируется либо `any`, либо сложными mapped types, которые не спасают от
   опечатки в рантайме.
2. **Согласованность с проектом.** Разбор ответа backend в проекте уже делается явными чистыми функциями
   (`parseApiError` в `shared/api/parseApiError.ts`), а не общими трансформерами — тот же принцип применён здесь.
3. **Область действия.** Только `Currency` требует camelCase по этому изменению (решение оркестратора); `User`
   остался как есть — значит, единого проектного правила «весь API-ответ конвертируется» нет, и вводить общий
   механизм ради одного типа избыточно (YAGNI). Если в будущих задачах (014+) потребуется камelCase для других DTO
   (`WalletOut`, `CategoryOut`), у них будет явный прецедент — точно такая же ручная функция рядом с hook'ом,
   а не общий утилитный слой.

Маппинг происходит один раз, на границе — внутри `useCurrencies`, сразу после ответа API; дальше по приложению
везде используется только `Currency`, `CurrencyDto` не экспортируется из `shared/ui`.

### `useCurrencies` — hook на `useQuery`

```ts
export function useCurrencies() {
  const api = useApiClient();
  return useQuery({
    queryKey: ["currencies"],
    queryFn: async ({ signal }) => {
      const page = await api.get<Page<CurrencyDto>>("/api/currencies", {
        query: { limit: 100, offset: 0 },
        signal,
      });
      return page.items.map(mapCurrency);
    },
  });
}
```

`limit: 100` — максимум, допустимый `PageParams` (`le=100`). Справочник валют мал (сейчас 3: CNY/RUB/USDT,
сидируется при старте), поэтому одной страницы с максимальным `limit` достаточно, чтобы забрать весь список без
клиентской постраничной подгрузки; если справочник когда-нибудь превысит 100 записей, это станет заметно по `total`
в ответе и потребует отдельного решения (вне рамок — решение дорожной карты зафиксировало именно такой подход).
`GET /api/currencies` не требует авторизации и не меняется от пользователя к пользователю, поэтому `useQuery` без
`meta: { silent: true }` — ошибка загрузки показывается глобальным toast по умолчанию (обычное поведение
`error-handling`), а сам `CurrencyPicker` дополнительно переходит в локальное состояние «недоступно» (см. ниже) —
это не дублирование сообщения, а два независимых эффекта одной ошибки (глобальное уведомление + состояние виджета).

### `CurrencyPicker` — один компонент, `multiple` как дискриминант типов

```ts
interface CurrencyPickerBaseProps {
  placeholder?: string;
  disabled?: boolean;
}

interface SingleCurrencyPickerProps extends CurrencyPickerBaseProps {
  multiple?: false;
  value: string | undefined;
  onChange: (value: string | undefined) => void;
}

interface MultipleCurrencyPickerProps extends CurrencyPickerBaseProps {
  multiple: true;
  value: string[];
  onChange: (value: string[]) => void;
}

export type CurrencyPickerProps = SingleCurrencyPickerProps | MultipleCurrencyPickerProps;
```

`value`/`onChange` — идентификаторы валют (`id: string`, как отдаёт backend), не сами объекты `Currency`: это
стандартный контракт значения формы (сравним с тем, как `wallet.currency_ids` на backend — список UUID). Компонент
оборачивает antd `Select` (`mode={multiple ? "multiple" : undefined}`), опции — `useCurrencies()` (`code — name`),
`loading={isPending}` во время загрузки. При `isError` `Select` переходит в `disabled` с `placeholder`
«Валюты недоступны» (замещает переданный `placeholder`) — тестируемое локальное состояние ошибки загрузки, глобальный
toast уже показан обработчиком `error-handling`. Один компонент с булевым `multiple`, а не два раздельных
(`CurrencySelect`/`CurrencyMultiSelect`), выбран потому, что оба режима на 100% используют одну и ту же загрузку
данных, разметку опций и состояния ошибки/загрузки — разница только в форме `value`/`onChange` и в одном пропе antd;
раздельные компоненты дублировали бы всё, кроме одной строки. Дискриминированное объединение типов по `multiple`
(вместо `value: string | string[]`) даёт вызывающему коду точную типизацию без приведений типов на каждом сайте
использования (SOLID I: потребитель получает ровно ту форму пропсов, которая соответствует его режиму).

### `IconPicker` — `Drawer`/`Modal` по `useIsMobile`, выбор без иллюстраций

```ts
export interface IconPickerProps {
  value: string | undefined;
  onChange: (name: string) => void;
  label?: string; // подпись для скринридера триггера, по умолчанию «Иконка»
}
```

Триггер — antd `Button` (`block`, высота ≥ 44 px из общей темы) с превью `Icon` слева, если `value` задан, и текстом
(имя не показываем — только превью, требование задачи), либо просто текст «Иконка не выбрана», когда `value`
не задан. Никакой дополнительной служебной иконки (например, «открыть выбор») не добавляется: сама кнопка и есть
интерактивный элемент, а превью бизнес-иконки — достаточный визуальный индикатор (явное указание в постановке).

По нажатию открывается список всех `BUSINESS_ICON_NAMES` — сеткой квадратных кнопок (каждая ≥ 44×44 px, `Icon`
внутри), выбранная подсвечивается токеном темы (`colorPrimary`/`colorPrimaryBg`), без хардкода цвета. Тап по
иконке сразу вызывает `onChange(name)` и закрывает контейнер — без отдельной кнопки «Подтвердить»: это на один шаг
короче для частого действия (создание кошелька/категории) и соответствует тому, как в приложении уже работают
короткие модальные выборы (одно действие — один результат). `Drawer`/`Modal` выбираются `useIsMobile()` — та же
единственная точка принятия решения, что уже используется для layout (`MobileShell`/`DesktopShell`) и это первый
компонент, который применяет уже сформулированное в AGENTS.md общее правило «на телефоне `Drawer`, не `Modal`» к
собственному модальному сценарию (в существующем коде это правило раньше нигде не было реализовано — ни один
компонент ещё не открывал ни `Drawer`, ни `Modal`), поэтому паттерн переиспользует инфраструктуру (`useIsMobile`),
а не копирует несуществующий прежний код. `Drawer` — `placement="bottom"`, `height="80vh"`; `Modal` — центрированный,
`width` в пределах ширины контента (960 px, как у `DesktopShell`).

### `MoneyInput` — строка, фильтрация, без `InputNumber`

```ts
export interface MoneyInputProps {
  value: string;
  onChange: (value: string) => void;
  decimalPlaces?: number;
  placeholder?: string;
  disabled?: boolean;
  id?: string;
}
```

`onChange(value: string)` (а не `onChange(event)`) — сигнатура, совместимая с тем, как antd `Form.Item` по умолчанию
извлекает значение (`getValueFromEvent`: если первый аргумент не содержит `target`, он используется как есть), то
есть `MoneyInput` можно поместить прямо в `<Form.Item name="amount"><MoneyInput /></Form.Item>` без дополнительных
пропов формы.

Реализация — обычный antd `Input` (`inputMode="decimal"`, `autoComplete="off"`), а не `InputNumber`: `InputNumber`
приводит значение к JS `number` внутри своей модели (даже если снаружи форматировать вывод строкой), что на суммах
с 8 знаками после запятой и до 24 значащих цифр (`MONEY_MAX_DIGITS`/`MONEY_DECIMAL_PLACES`, `core/schemas/money.py`)
даёт потерю точности — ровно та же причина, по которой backend использует `Decimal`/`NUMERIC`, а не `float`
(зафиксировано в AGENTS.md, разделе «Деньги и валюты»). Одна десятичная точка `.` — тот же разделитель, что отдаёт
backend в JSON (`Money` сериализуется `format(value, "f")`, всегда с точкой), поэтому конвертация разделителя между
вводом и API не нужна.

Фильтрация — чистая функция `isValidMoneyAmount(value: string, decimalPlaces?: number): boolean` (тестируется
отдельно от компонента, SOLID S):
```ts
export function isValidMoneyAmount(value: string, decimalPlaces?: number): boolean {
  const pattern =
    decimalPlaces == null ? /^\d*\.?\d*$/ : new RegExp(`^\\d*(\\.\\d{0,${decimalPlaces}})?$`);
  return pattern.test(value);
}
```
Разрешены цифры и не более одной точки; допускается промежуточное состояние ввода («12.» без цифр после точки),
чтобы не мешать набору. `decimalPlaces` ограничивает число знаков после точки, когда валюта уже выбрана (обычно —
`Currency.decimalPlaces` выбранной валюты); без него ограничения по разрядам нет — сервер провалидирует
(`Money`, до 8 знаков и 24 значащих цифр) и вернёт 400 с понятным сообщением по полю через уже существующий
`applyFieldErrors`. Ограничение на общее число цифр (24) на клиенте не вводится — оно не является типичным
пользовательским сценарием ошибки (суммы такого размера нереалистичны) и уже покрыто серверной валидацией;
вводить его на клиенте без явного требования — усложнение без задачи (YAGNI), которое можно добавить в 014+, если
понадобится по факту UI. `handleChange` компонента вызывает `onChange` только если `isValidMoneyAmount` вернула
`true`, иначе игнорирует нажатие (значение поля не меняется) — так поле никогда не может провалидированно попасть
в состояние с лишним символом.

### `EmptyState` — иконка, текст, опциональное действие одним объектом

```ts
export interface EmptyStateProps {
  icon: string; // имя иконки Lucide (kebab-case), как в БД
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}
```

`action` — один опциональный объект (`label` + `onClick` вместе), а не два раздельных опциональных пропа
(`actionLabel?`, `onAction?`): раздельные пропы допускали бы некорректное промежуточное состояние («есть текст
кнопки, но нет обработчика» и наоборот), которое пришлось бы обрабатывать в рантайме; один объект делает такое
состояние невозможным на уровне типов (SOLID I — точный контракт того, что нужно потребителю). Рендер: `Icon`
крупного размера (32 px, `size` проп `Icon`) по центру, `Typography.Title level={5}` — заголовок,
`Typography.Text type="secondary"` — описание, если передано, `Button type="primary"` (`block` на телефоне) —
если передан `action`. Никаких иллюстраций/картинок — в приложении нет источника изображений, кроме иконок Lucide
(зафиксировано в постановке и `docs/tasks/013_frontend_shell.md`).

## Risks / Trade-offs

- [`limit: 100` для валют перестанет вмещать весь справочник, если он вырастет] → `total` в ответе виден в hook'е;
  расширение (клиентская подгрузка или поиск на сервере) — отдельная будущая задача, если понадобится по факту
  роста справочника (сейчас 3 валюты).
- [Ручной `mapCurrency` требует правки при изменении `CurrencyOut`] → изменение схемы backend — часть отдельного
  OpenSpec-изменения с собственным design.md; `Currency.test.ts` фиксирует форму `CurrencyDto` → `Currency` и
  падает при рассинхроне до того, как ошибка попадёт в рантайм.
- [Тап-и-закрыть в `IconPicker` не даёт отменить выбор одним действием после открытия] → закрытие `Drawer`/`Modal`
  без выбора (свайп/оверлей/`Esc`) не меняет `value` — уже выбранная иконка остаётся прежней; риск минимален для
  частоты действия (выбор при создании/редактировании кошелька или категории).
- [Регулярное выражение `MoneyInput` пропускает такие промежуточные состояния, как одинокая точка `"."`] →
  осознанно: конечная валидация суммы (положительность, соответствие `decimalPlaces` выбранной валюты) — забота
  формы конкретного экрана (014/016/017) при отправке, не самого поля ввода; `isValidMoneyAmount` отвечает только
  за то, что в поле нельзя ввести символ, порождающий заведомо неверную денежную строку.
- [`CurrencyPicker`/`IconPicker` — новые сквозные точки, которыми будут пользоваться сразу 4 задачи] → тесты
  этой задачи фиксируют контракт (`props`, поведение состояний загрузки/ошибки/выбора) до начала работы над
  экранами, чтобы 014–018 полагались на стабильный API, а не переоткрывали его.

## Migration Plan

Backend, база данных, миграции Alembic и существующие API-контракты **не меняются**: изменение затрагивает только
новые файлы внутри `frontend/src/shared/api/` и `frontend/src/shared/ui/` плюс их реэкспорт из
`shared/api/index.ts`/`shared/ui/index.ts`. Разворачивания/отката на уровне инфраструктуры не требуется — обычный
деплой frontend-сборки. Существующие компоненты (`navItems`, `routes.tsx`, экраны `health`/`settings`/`auth`) не
трогаются, риска регресса уже работающих разделов нет.

## Open Questions

Нет — все решения по объёму и границам приняты оркестратором в `docs/tasks/013_frontend_shell.md`; сигнатуры и
механика реализации зафиксированы в разделе «Decisions» выше.
