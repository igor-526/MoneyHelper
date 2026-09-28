## Context

Backend-скелет готов: `GET /health`, ошибки всегда JSON `{"detail": ...}` (валидация — 400 со списком pydantic-ошибок
`loc/msg/type`), CORS с credentials для `CORS_ORIGINS=http://localhost:5173`, порт backend 8201. Frontend должен стать
фундаментом для всех фич: единый способ ходить в API и гарантированный показ любой ошибки. Правила SOLID для frontend
зафиксированы в AGENTS.md; требования — в спецификациях этого изменения.

## Goals / Non-Goals

**Goals:**
- Каркас `frontend/` с зависимостью компонентов от интерфейса `ApiClient`, а не от `fetch`.
- Ошибка любого запроса и любой мутации по умолчанию превращается в toast без кода в каждой фиче.
- Тестируемость: клиент, toast и обработчик ошибок проверяются unit-тестами без сети.
- QualityGate frontend в тех же `make format|lint|test` и в CI.
- Mobile-first: основной сценарий использования — телефон; каркас, тема и layout проектируются сначала под узкий экран.
- Светлая и тёмная темы (с режимом «как в системе») и PWA: установка на домашний экран, открытие оболочки офлайн, управляемое обновление версии.

**Non-Goals:**
- Экраны авторизации и бизнес-фич, работающий refresh, Docker-образ, E2E, antd-mobile, кэширование данных API и офлайн-мутации, push-уведомления, деплой по HTTPS.

## Decisions

**Менеджер пакетов: npm** (Node 24 + npm 11 уже установлены, `package-lock.json`, `npm ci` в CI). Альтернатива pnpm
быстрее, но требует отдельной установки и в CI, и локально; выигрыша для одного пакета нет.

**Сборка и стек: Vite + React 19 + TypeScript strict, react-router.** Vite — стандарт для CSR без SSR. Строгий
TypeScript (`strict`, `noUncheckedIndexedAccess`).

**Серверное состояние: TanStack Query.** `QueryCache.onError` и `MutationCache.onError` дают единственную точку для
глобального toast, что прямо реализует требование «ни одна ошибка не пропадает молча». Альтернатива — свои hooks над
`fetch` — потребовала бы самим реализовать кэш, состояния загрузки и отмену. Повторы (`retry`) отключаются для ошибок
4xx и `unauthorized`; для `network`/`server` запросов на чтение — один повтор, мутации не повторяются.

**UI-библиотека: Ant Design 6 (`antd`).** Задана пользователем. Подключается через `ConfigProvider` (локаль `ru_RU`,
тема) и компонент `App` (контекст для `message`). Импорты поштучные (`import { Button } from "antd"`), tree-shaking
Vite их выбрасывает. Отдельный `antd-mobile` не берём: один набор компонентов проще, а адаптивность достигается темой
и layout (см. ниже). Иконки — только Lucide (`Icon`), пакет `@ant-design/icons` не подключаем, чтобы не держать два набора.

**Mobile-first (тема и layout).**
- Тема antd (`shared/ui/theme.ts`): общие токены для обеих тем; `token.controlHeight = 44` (кнопки, поля, select), `fontSize = 16` (поля не вызывают
  зум iOS), увеличенные `paddingSM/paddingMD` между элементами, `borderRadius` 10. Тема — единственное место настройки.
- Хук `useIsMobile` (`shared/ui/useIsMobile.ts`) на собственном `useMediaQuery` (`matchMedia` + `useSyncExternalStore`):
  мобильный режим, если не выполнено `(min-width: 768px)` — порог брейкпоинта `md` antd. Свой `matchMedia` вместо
  `Grid.useBreakpoint()` выбран, чтобы не зависеть от внутренностей antd и использовать один механизм и для темы
  (`prefers-color-scheme`). Единственная точка выбора режима (принцип S/D); в тестах `matchMedia` подменяется.
- Layout (`app/layout`): `AppLayout` выбирает `MobileShell` (фиксированная нижняя панель `TabBar` до 5 пунктов, контент с
  нижним отступом под панель) или `DesktopShell` (верхнее меню, контент ограничен по ширине). Пункты навигации задаются
  конфигурацией (`navItems`), а не разметкой (принцип O). Для нижней панели — `padding-bottom: env(safe-area-inset-bottom)`.
- `index.html`: viewport с `viewport-fit=cover`; корень на `100dvh`; глобальные CSS-правила: `box-sizing`, отсутствие
  горизонтального overflow, `-webkit-tap-highlight-color`, `touch-action: manipulation` (без задержки двойного тапа).
- Правила для фич (в AGENTS.md): формы в одну колонку, `inputMode="decimal"` для сумм, основное действие на всю ширину,
  `Drawer` снизу вместо `Modal`, списки/карточки вместо таблиц, никакого hover-only.
- Проверка: unit-тесты переключения `MobileShell`/`DesktopShell` через мок `matchMedia`; ручная проверка на эмуляции
  телефона 360×800 и 320×568 (DevTools) в задаче 7.3. jsdom не считает вёрстку, поэтому размеры touch-целей проверяются
  через значения темы, а не через `getBoundingClientRect`.

**Тёмная тема.**
- Режим `ThemeMode = "light" | "dark" | "system"`, чистая функция `resolveTheme(mode, systemPrefersDark): "light" | "dark"`
  (принцип S, легко тестируется). `ThemeProvider` держит режим, слушает `matchMedia("(prefers-color-scheme: dark)")`
  и отдаёт `useThemeMode()` → `{ mode, resolved, setMode }`.
- Внутри `ThemeProvider` находится antd `ConfigProvider` с `algorithm: resolved === "dark" ? theme.darkAlgorithm : theme.defaultAlgorithm`
  и общими токенами (`controlHeight 44`, `fontSize 16`) — размеры не зависят от темы. Цвета берутся из токенов
  (`theme.useToken()`) и CSS-переменных, а не хардкодятся.
- Хранение: `localStorage["moneyhelper.theme"]` через маленький интерфейс `ThemeStorage` (`get/set`) с обработкой исключений
  (закрытые режимы браузера); значение валидируется. Это предпочтение интерфейса, не токен авторизации, поэтому правило
  «ничего не хранить в localStorage» из AGENTS.md его не касается (в правило добавится явное уточнение).
- Без мигания: встроенный скрипт в `index.html` до загрузки бандла читает `localStorage` и `matchMedia` и ставит
  `<html data-theme="dark|light">` и `color-scheme`. Глобальный `index.css` задаёт `--app-bg`/`--app-fg` по
  `[data-theme]`; `ErrorBoundary` использует их и работает без antd. Скрипт маленький и дублирует логику
  `resolveTheme`; чтобы не разъехаться, тест сверяет результат скрипта и функции на одних входах.
- `theme-color`: в `index.html` два `<meta name="theme-color">` с `media="(prefers-color-scheme: ...)"`; при явном выборе режима,
  отличном от системного, `ThemeProvider` выставляет единый `theme-color` по текущей теме.
- Переключатель — `Segmented` antd (3 варианта, крупные цели) на странице `/settings`.
- Альтернативы: только системная тема без переключателя (пользователь просил именно тёмную тему как функцию — нужен выбор);
  CSS-переменные вместо алгоритмов antd (пришлось бы вручную красить все компоненты).

**PWA (`vite-plugin-pwa`, Workbox).**
- Плагин в `vite.config.ts`: `registerType: "prompt"`, `strategies: "generateSW"`, `workbox.globPatterns` для оболочки
  (`js,css,html,ico,png,svg,woff2`), `navigateFallback: "/index.html"`, `cleanupOutdatedCaches: true`. **Runtime-кэширования
  нет**: запросы к API идут мимо SW (кросс-origin запросы к backend SW не перехватывает без явного маршрута, и мы его не
  добавляем), поэтому cookies, CORS и свежесть финансовых данных не меняются. Тест проверяет, что в конфигурации нет
  `runtimeCaching`.
- Manifest задан в отдельном файле `pwa/manifest.ts` (константа), плагин и тесты используют один источник:
  `name`, `short_name`, `description`, `lang: "ru"`, `start_url`/`scope: "/"`, `display: "standalone"`, `theme_color`,
  `background_color`, иконки `192`, `512`, `512 maskable`. Ограничение: manifest не умеет менять цвета по теме, поэтому
  `background_color` (экран запуска) фиксирован; он выбирается нейтральным, а `theme_color` — брендовым.
- Иконки: один исходный `public/icon.svg` (простая иконка кошелька), `@vite-pwa/assets-generator` (`npm run pwa-assets`)
  создаёт PNG 64/192/512, maskable 512 с полями, `apple-touch-icon` 180 и `favicon.ico`; результат коммитится, чтобы
  сборка не зависела от генератора.
- iOS: `apple-mobile-web-app-capable`, `apple-mobile-web-app-title`, `apple-mobile-web-app-status-bar-style=black-translucent`
  (безопасные зоны уже учтены через `viewport-fit=cover`), `apple-touch-icon`. Событие `beforeinstallprompt` на iOS
  отсутствует, поэтому показывается инструкция.
- Обновление: хук `usePwaUpdate` — обёртка над `useRegisterSW` из `virtual:pwa-register/react` (интерфейс
  `{ needRefresh, update() }`, принцип D; в тестах модуль подменяется алиасом). Компонент `PwaBanners` (в layout над нижней панелью)
  показывает «Доступна новая версия» с кнопкой «Обновить» и офлайн-баннер («Нет соединения…»). Автоматически новая версия не
  применяется, чтобы не потерять ввод в форме.
- Онлайн-статус: `useOnlineStatus` на `navigator.onLine` + события `online/offline`.
- Установка: `useInstallPrompt` перехватывает `beforeinstallprompt` (сохраняет событие, `preventDefault`), отдаёт
  `{ canInstall, install(), isStandalone, isIos }`; UI — кнопка и подсказка на `/settings`.
- Service worker работает только в защищённом контексте: `localhost` допускается, для прода нужен HTTPS (деплой вне рамок).
  В dev-сервере SW выключен (`devOptions.enabled = false`), PWA проверяется через `npm run build && npm run preview`.
- Альтернативы: `injectManifest` со своим SW (больше кода без выигрыша), кэширование API stale-while-revalidate
  (риск показать устаревшие деньги и утечка данных между пользователями на общем устройстве — отвергнуто).

**Toast: интерфейс `useToast` поверх antd `message`.** Компоненты зависят от нашего `useToast`, а не от `message`
(принцип D), поэтому реализацию можно поменять. `ToastProvider` берёт `message` из `App.useApp()`. Дедупликация — через
`key = type + text` (antd обновляет уведомление с тем же ключом и перезапускает таймер), лимит — `maxCount: 3`, длительность
8 с для ошибок и 4 с для остальных, закрытие по нажатию (`onClick` → `message.destroy(key)`), смещение сверху
`calc(env(safe-area-inset-top) + 8px)`, роли ARIA задаются в содержимом. Свою очередь не пишем — антд уже даёт её.
Альтернатива `notification` отвергнута: карточка крупнее и занимает больше места на телефоне.

**API-клиент: `ApiClient` (интерфейс) + `FetchApiClient` (реализация на `fetch`).** Интерфейс: `request<T>(options)` и
удобные `get/post/put/patch/delete`. Реализация:
1. `fetch` с `credentials: "include"`, `AbortController` для таймаута (15 c, настраивается);
2. при сбое `fetch` — `ApiError(kind: "network")`, при абортe по таймауту — `kind: "timeout"`;
3. при `!response.ok` — разбор JSON тела в `ApiError` через отдельную чистую функцию `parseApiError(status, body)`
   (принцип S: разбор отделён от транспорта);
4. 401 → вызов настраиваемого `onUnauthorized(): Promise<boolean>`; при `true` — ровно один повтор запроса. Без
   `onUnauthorized` — сразу `ApiError`. Флаг повтора передаётся внутри вызова, а не хранится в состоянии.
Токены нигде не читаются: их видит только браузер в cookies. Зависимость — только от `fetch` (передаётся в конструктор
для тестов), поэтому подмена в тестах без `msw`.

**Формат `ApiError`:** `kind`, `status: number | null`, `detail: string | null`, `fieldErrors: Record<string, string[]>`.
Поле формы — `loc` без ведущего `body`, элементы склеиваются через `.` (`items.0.amount`). `detail`, не являющийся
строкой или списком валидации, отбрасывается, тогда работают сообщения по умолчанию.

**Глобальная обработка: `createErrorMessageResolver` + `handleApiError`.** Чистая функция
`resolveErrorMessage(error, overrides?)` выбирает текст по таблице `kind → сообщение` (принцип O: новый вид ошибки —
новая строка таблицы, а не ветка `if`). `handleApiError(toast)` вызывается из `onError` кэшей. Действие
переопределяет сообщение через `meta: { errorMessages?: Partial<Record<ApiErrorKind, string>>; silent?: boolean }` в
`useMutation`/`useQuery`; `silent` отключает глобальный toast, тогда действие обязано обработать ошибку явно.
Для 400 с полями: помощник `applyFieldErrors(error, knownFields)` возвращает `{ byField, rest }`; форма показывает
`byField`, а `rest` добавляется в toast (см. спеку).

**401 в глобальном обработчике.** Пока нет авторизации (005), 401 показывает toast «Сессия истекла, войдите снова».
Перенаправление на вход и refresh подключаются в 005 через `onUnauthorized` и отдельный слушатель; для этого в
`ApiClient` оставлена точка расширения, а глобальный обработчик не знает о роутинге (принцип D).

**Error boundary:** классовый компонент (`componentDidCatch`) в корне, экран ошибки с кнопкой «Перезагрузить»
(`window.location.reload`). Он вне `ThemeProvider`/antd, чтобы работать даже при сбое провайдеров; вёрстка простая, с теми же правилами
(кнопка ≥ 44 px, viewport), цвета из CSS-переменных `--app-bg`/`--app-fg`, поэтому корректен в обеих темах. Ошибки асинхронных запросов он не ловит — они обрабатываются кэшами Query.

**Композиция (`src/app`):** `ErrorBoundary → ThemeProvider (внутри antd ConfigProvider: ru_RU, светлый/тёмный алгоритм) → antd App → ToastProvider → ApiClientProvider → QueryClientProvider → RouterProvider`; `PwaBanners` рендерится в layout.
`QueryClient` создаётся фабрикой, получающей `toast`, поэтому его глобальный обработчик зависит от интерфейса toast.
Реализация `ApiClient` создаётся только в `main.tsx` из `VITE_API_URL`.

**Iconpack: `Icon` над `lucide-react`.** Имя из БД (kebab-case) сопоставляется с компонентом через закрытую статическую карту
`ICONS` (`shared/ui/icons.ts`); неизвестное имя → запасная иконка `CircleHelp`. Динамическая подгрузка каждой иконки
(`DynamicIcon`) отвергнута: она создаёт по чанку на иконку, и precache PWA раздувается сотнями файлов. Полный набор иконок
для категорий и кошельков определит задача «Iconpack» (007): карта расширяется без изменения интерфейса `Icon`.

**Стили:** стили antd (CSS-in-JS) плюс небольшой глобальный `index.css` (mobile-правила выше) и CSS Modules для
собственной раскладки. Цвета и размеры берутся из токенов темы (`theme.useToken()`), а не хардкодятся.

**Инструменты качества:** ESLint (flat config, typescript-eslint, react-hooks, jsx-a11y) + Prettier, `tsc --noEmit`,
Vitest + Testing Library + jsdom. Тесты лежат рядом с кодом (`*.test.ts(x)`). Скрипты `npm run format|lint|typecheck|test`.
Корневой `Makefile`: `format`/`lint`/`test` вызывают `$(MAKE) -C backend …` и `npm --prefix frontend run …`; добавляются
`fe-install`, `fe-dev`, `fe-build`. Для `make test` зависимости frontend ставятся отдельно (`fe-install`), CI использует `npm ci`.

**Структура:**
```
frontend/
  src/
    app/           # App, providers, router, layout (MobileShell/DesktopShell, navItems)
    features/
      health/      # страница-заглушка: hook useHealth, компонент
      settings/    # страница настроек: переключатель темы, установка PWA
    shared/
      api/         # ApiClient, FetchApiClient, ApiError, parseApiError, ApiClientProvider
      errors/      # resolveErrorMessage, handleApiError, applyFieldErrors, ErrorBoundary
      ui/          # theme (токены), ThemeProvider/useThemeMode, useIsMobile, toast (ToastProvider, useToast), Icon
      pwa/         # manifest, usePwaUpdate, useOnlineStatus, useInstallPrompt, PwaBanners
      config/      # чтение VITE_API_URL
    main.tsx
  public/          # icon.svg, сгенерированные иконки, favicon
  pwa-assets.config.ts, vite.config.ts
```

## Risks / Trade-offs

- [Размер бандла antd] → поштучные импорты, code-splitting роутов (`React.lazy`) появится с первыми страницами; размер сборки фиксируется в отчёте `npm run build`, для мобильной сети целимся в первый экран < 300 КБ gzip.
- [antd по умолчанию рассчитан на десктоп: мелкие элементы, `Modal`, `Table`] → тема с `controlHeight 44`, правила мобильных паттернов в AGENTS.md; отказ от `Modal`/`Table` на телефоне.
- [Мобильные размеры нельзя проверить в jsdom] → тесты на значения темы и переключение layout, ручная проверка на эмуляции телефона.
- [Версия antd 6 новая, возможны отличия API от 5] → API `message`/`App`/`ConfigProvider` сверяется с документацией установленной версии при реализации; обёртки скрывают детали.
- [Глобальный `onError` может показать toast дважды, если действие само показывает ошибку] → флаг `meta.silent` и явное правило в AGENTS.md.
- [Ошибки, брошенные вне Query (например, прямой вызов `ApiClient` в обработчике события)] → правило: обращения к API только через hooks на Query; прямой вызов клиента — только внутри `queryFn`/`mutationFn`.
- [Точная семантика `dynamicIconImports` зависит от версии lucide-react] → интерфейс `Icon` скрывает реализацию; поведение покрыто тестами.
- [Разные origin: в dev cookies работают между портами `localhost` (same-site)] → проверено вручную в критерии готовности; в проде — общий родительский домен (решение для деплоя вне этого изменения).

- [Service worker может держать старую версию и сбивать разработку] → SW выключен в dev, обновление только по подтверждению пользователя, `cleanupOutdatedCaches`; проверка через `preview`.
- [Кэшировать оболочку безопасно, а API — нет] → в конфигурации нет `runtimeCaching`, покрыто тестом; при добавлении офлайн-данных нужна отдельная задача с продуманной изоляцией пользователей.
- [Мигание темы при старте и рассинхрон встроенного скрипта с `resolveTheme`] → скрипт минимален, тест сверяет оба на одних входах.
- [PWA на iOS ограничена: нет `beforeinstallprompt`, разные особенности standalone] → инструкция для iOS, ручная проверка на реальном устройстве вне CI (отмечено в задачах).
- [Manifest не поддерживает цвета по теме] → нейтральный `background_color`, `theme-color` переопределяется мета-тегами и JS.
- [PWA требует HTTPS в проде] → зафиксировано как требование к деплою (вне рамок).

## Open Questions

- Иконка приложения: временная простая SVG-иконка кошелька; при желании заменить на фирменную — заменой `public/icon.svg` и запуском `npm run pwa-assets`.
- Офлайн-доступ к данным (кэш чтения) — отдельная будущая задача, если понадобится.
