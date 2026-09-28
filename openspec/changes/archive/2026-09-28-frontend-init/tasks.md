## 1. Каркас проекта

- [x] 1.1 Создать `frontend/` (Vite + React + TypeScript strict), `package.json`, `package-lock.json`, `.gitignore`, `.nvmrc`/`engines`
- [x] 1.2 Разложить `src/app`, `src/features`, `src/shared`, настроить алиас импортов и `tsconfig`
- [x] 1.3 Подключить antd, `lucide-react`; `index.html` с viewport (`viewport-fit=cover`), глобальный `index.css` (`100dvh`, без горизонтального overflow, `touch-action: manipulation`, переменные `--app-bg`/`--app-fg`)
- [x] 1.4 Добавить `shared/config` (чтение `VITE_API_URL`, значение по умолчанию `http://localhost:8201`) и `frontend/.env.example`; порт dev-сервера 5173

## 2. Инструменты качества

- [x] 2.1 Настроить ESLint (flat config, typescript-eslint, react-hooks, jsx-a11y) и Prettier
- [x] 2.2 Настроить Vitest + Testing Library + jsdom (общий setup: мок `matchMedia`, `localStorage`), скрипты `format`, `lint`, `typecheck`, `test`
- [x] 2.3 Подключить frontend к корневому `Makefile`: `format`, `lint`, `test`, цели `fe-install`, `fe-dev`, `fe-build`, `fe-preview`
- [x] 2.4 Добавить job frontend в `.github/workflows/ci.yml` (`npm ci`, lint, typecheck, test, build)

## 3. API-клиент

- [x] 3.1 Реализовать `ApiError`, `ApiErrorKind` и чистую функцию `parseApiError` (статус → kind, `detail`, `fieldErrors` из `loc`)
- [x] 3.2 Описать интерфейс `ApiClient` и реализовать `FetchApiClient` (cookies, JSON, таймаут, network/timeout)
- [x] 3.3 Добавить точку расширения `onUnauthorized` с одним повтором запроса
- [x] 3.4 Добавить `ApiClientProvider` и хук `useApiClient`
- [x] 3.5 Unit-тесты: нормализация для 400/401/403/404/409/500, не-JSON ответ, сетевой сбой, таймаут, `credentials: "include"`, повтор после 401

## 4. Темы (светлая и тёмная) и мобильная основа

- [x] 4.1 Реализовать токены темы `shared/ui/theme.ts` (`controlHeight 44`, `fontSize 16`, отступы, радиусы; одинаковы для обеих тем) и хук `useIsMobile`; тесты на значения токенов и переключение через мок `matchMedia`
- [x] 4.2 Реализовать `ThemeMode`, чистую `resolveTheme`, `ThemeStorage` (`localStorage["moneyhelper.theme"]`, try/catch, валидация) и тесты
- [x] 4.3 Реализовать `ThemeProvider` (antd `ConfigProvider` с `darkAlgorithm`/`defaultAlgorithm`, `ru_RU`, слушатель `prefers-color-scheme`, `data-theme`, `color-scheme`, `theme-color`) и хук `useThemeMode`; тесты: system/light/dark, смена системной настройки, восстановление, сбой хранилища, некорректное значение
- [x] 4.4 Добавить встроенный скрипт в `index.html` против мигания темы, два `theme-color` с `media`, тест на совпадение скрипта и `resolveTheme` на одних входах

## 5. Toast и Icon

- [x] 5.1 Реализовать `ToastProvider` и `useToast` поверх antd `message` (`App.useApp()`): ключ-дедупликация, `maxCount 3`, длительность 8/4 с, закрытие по нажатию, безопасная зона, роли ARIA
- [x] 5.2 Тесты Toast: показ, автоскрытие (fake timers), закрытие нажатием, дубликат, лимит, роль ошибки, ошибка вне провайдера
- [x] 5.3 Реализовать `Icon` над Lucide с запасной иконкой и тесты

## 6. Обработка ошибок

- [x] 6.1 Реализовать таблицу сообщений и `resolveErrorMessage` с переопределениями
- [x] 6.2 Реализовать `handleApiError` и фабрику `QueryClient` с глобальными `QueryCache.onError` / `MutationCache.onError`, поддержкой `meta.errorMessages` и `meta.silent`, политикой `retry`
- [x] 6.3 Реализовать `applyFieldErrors` (привязка к полям формы, остаток в toast)
- [x] 6.4 Реализовать корневой `ErrorBoundary` без antd (цвета из CSS-переменных, кнопка ≥ 44 px, «Перезагрузить»)
- [x] 6.5 Тесты: для каждого вида (400, 401, 403, 404, 409, 500, network, timeout) toast с нужным текстом, состояние не «загрузка», для запроса и для мутации; переопределение и `silent`; поля валидации; error boundary

## 7. Оболочка приложения

- [x] 7.1 Собрать `App` и провайдеры в порядке ErrorBoundary → ThemeProvider (antd ConfigProvider) → antd App → Toast → ApiClient → Query → Router; `main.tsx` создаёт `FetchApiClient`
- [x] 7.2 Реализовать роутинг и адаптивный layout: `AppLayout`, `MobileShell` (нижняя панель с safe-area) и `DesktopShell`, конфигурация `navItems` («Главная», «Настройки»); страницу «Страница не найдена»
- [x] 7.3 Реализовать `features/health`: hook `useHealth` и страницу-заглушку с состоянием backend
- [x] 7.4 Реализовать `features/settings`: страница `/settings` с переключателем темы (`Segmented`), блоком установки PWA и версией приложения
- [x] 7.5 Тесты layout: на телефоне нижняя панель без верхней навигации, на широком экране наоборот, контент не перекрыт панелью
- [x] 7.6 Тесты оболочки: страница с фейковым `ApiClient` (доступен / сетевой сбой с toast / 500), неизвестный маршрут, переключатель темы на `/settings`

## 8. PWA

- [x] 8.1 Добавить `public/icon.svg`, `pwa-assets.config.ts` и `npm run pwa-assets` (`@vite-pwa/assets-generator`); сгенерировать и закоммитить PNG 192/512, maskable 512, `apple-touch-icon` 180, favicon
- [x] 8.2 Вынести manifest в `pwa/manifest.ts`; подключить `vite-plugin-pwa` (`registerType: "prompt"`, precache оболочки, `navigateFallback`, `cleanupOutdatedCaches`, без `runtimeCaching`, SW выключен в dev); мета-теги manifest и iOS в `index.html`
- [x] 8.3 Тесты конфигурации: состав manifest, существование файлов иконок, отсутствие `runtimeCaching` и правил для адреса API
- [x] 8.4 Реализовать `useOnlineStatus` и `usePwaUpdate` (обёртка над `virtual:pwa-register/react`, подмена в тестах) и `PwaBanners` (обновление и офлайн, над нижней панелью с safe-area); тесты
- [x] 8.5 Реализовать `useInstallPrompt` (`beforeinstallprompt`, standalone, iOS) и UI установки на `/settings`; тесты

## 9. Документация и проверка

- [x] 9.1 Обновить AGENTS.md (структура frontend, Ant Design, mobile-first и мобильные паттерны, темы: цвета только из токенов, PWA: API не кэшируется, правило обращения к API только через hooks, `meta.silent`, уточнение про `localStorage` для темы, команды `make fe-*`)
- [x] 9.2 Обновить README.md (запуск frontend, PWA, QualityGate) и `openspec/config.yaml` (frontend: antd, тема, PWA)
- [x] 9.3 Вручную проверить (`make fe-dev`): страница показывает «backend доступен» без CORS-ошибок; остановить backend — toast «Нет соединения»; эмуляция телефона 360×800 и 320×568 (нет горизонтального скролла, нижняя панель и toast вне безопасных зон, размеры элементов); ширина ≥ 768 px; светлая и тёмная темы, переключатель, отсутствие мигания; записать размер сборки
- [ ] 9.4 (service worker, офлайн, установка и баннер обновления отложены: PWA пока не устанавливается) Вручную проверить PWA (`make fe-build && make fe-preview`): manifest и иконки в DevTools → Application, service worker активен, оболочка открывается офлайн, запросы к API не кэшируются, кнопка установки, баннер обновления после пересборки; отметить, что проверка на реальном iOS/Android-устройстве выполняется пользователем
- [x] 9.5 QualityGate: `make format`, `make lint`, `make test` (backend и frontend) проходят
