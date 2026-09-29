## Context

Скелет backend (`backend-foundation`) и справочник валют (`currencies-seeding`) уже дают образец полного
вертикального среза (сущность → протокол → репозиторий → сервис → API → тесты) и переиспользуемый механизм
сидирования JSON-справочников в БД (`utils/seeding.py`). Задача 007 по объёму и духу похожа на 006 — небольшой
глобальный справочник с эндпоинтом чтения, — но отличается ключевым образом: иконки не персистентны и не
пользовательские данные, а закрытый курируемый список имён Lucide, зашитый в код. Ни таблица, ни репозиторий, ни
сидирование ему не нужны — это статическая константа, известная на момент сборки backend, а не запись, которую
кто-то создаёт через API.

На frontend уже существует закрытая статическая карта Lucide-компонентов `frontend/src/shared/ui/icons.ts`
(`ICONS: Record<string, LucideIcon>`), созданная в задаче 003 для UI-элементов приложения — до того, как появился
единый реестр backend. В ней сейчас смешаны две категории имён:
- 23 бизнес-иконки категорий/кошельков (banknote, briefcase, bus, car, coins, credit-card, film, gamepad-2, gift,
  graduation-cap, heart-pulse, house, landmark, piggy-bank, plane, shirt, shopping-cart, smartphone, trending-down,
  trending-up, utensils, wallet, zap) — именно они формализуются реестром `icons.json`;
- 7 UI-иконок интерфейса (settings, sun, moon, log-out, download, share, wifi-off) — не относятся к категориям и
  кошелькам, вне рамок задачи 007, реестр их не содержит.

Версия `lucide-react` на frontend уже зафиксирована (`^1.48.0`, `frontend/package.json`) в задаче 003; задача 007 её
не меняет и отдельного решения не принимает.

## Goals / Non-Goals

**Goals:**
- Единый источник правды для допустимых имён иконок — `backend/src/core/icons.json`.
- Backend строит из него `ALLOWED_ICONS` и переиспользуемый Pydantic-тип `IconName` для будущих схем кошельков и
  категорий (008/009).
- Эндпоинт `GET /api/icons` без авторизации, отдающий отсортированный список имён.
- Frontend не тянет список по сети (архитектурное ограничение PWA/tree-shaking сохраняется), а синхронизируется с
  backend через `vitest`-тест, читающий тот же JSON с диска.
- Некорректное имя иконки отклоняется валидатором с понятной ошибкой.

**Non-Goals:**
- Персистентное хранение реестра в БД, миграция, сидирование — реестр статический, живёт в коде.
- Подключение `IconName` к реальным схемам кошельков/категорий — их ещё нет (008/009).
- Загрузка пользовательских иконок, расширение до полного набора Lucide.
- Изменение версии `lucide-react` или механизма `resolveIcon`/`Icon` на frontend.

## Decisions

### Реестр — файл в `core`, а не таблица БД

**Решение:** `backend/src/core/icons.json` — простой JSON-список отсортированных строк в kebab-case:

```json
[
  "banknote",
  "briefcase",
  "bus",
  "car",
  "coins",
  "credit-card",
  "film",
  "gamepad-2",
  "gift",
  "graduation-cap",
  "heart-pulse",
  "house",
  "landmark",
  "piggy-bank",
  "plane",
  "shirt",
  "shopping-cart",
  "smartphone",
  "trending-down",
  "trending-up",
  "utensils",
  "wallet",
  "zap"
]
```

Ровно 23 имени — текущий состав бизнес-иконок из `frontend/src/shared/ui/icons.ts` (категория (а) в контексте выше),
без UI-иконок интерфейса. Расширение набора в будущем — правка этого файла (добавить строку с обеих сторон:
`icons.json` и `frontend/src/shared/ui/icons.ts`), не требует менять код механизма.

`backend/src/core/icons.py` читает файл при импорте модуля:

```python
import json
from pathlib import Path

_ICONS_PATH = Path(__file__).parent / "icons.json"

ALLOWED_ICONS: frozenset[str] = frozenset(json.loads(_ICONS_PATH.read_text(encoding="utf-8")))


def list_icon_names() -> list[str]:
    return sorted(ALLOWED_ICONS)
```

**Альтернатива (отвергнута): таблица `icons` в БД, сидируемая как `currencies`.** Отвергнута, потому что реестр не
персистентная сущность с жизненным циклом (создание/обновление записи через API, внешние ключи от кошельков и
категорий на `id` записи) — это набор допустимых *значений* строкового поля, известный на этапе разработки, а не
данные, которыми управляет администратор в рантайме. Заводить таблицу, репозиторий и сидирование ради статического
списка строк было бы избыточным слоем (нарушение «не создавай лишних слоёв там, где это неоправданно» из AGENTS.md):
- Схема кошелька/категории хранит `icon_name: str`, а не `icon_id: UUID` со ссылкой на таблицу иконок — так проще
  (не нужен JOIN ради отображения иконки) и так буквально сформулировано в AGENTS.md: «в БД хранится имя иконки
  Lucide в kebab-case».
- Список валют содержательно растёт (пользователь может попросить добавить валюту), список иконок — это по сути
  константа приложения, синхронизированная с зашитой в бандл frontend картой компонентов; расхождение между «что в
  БД» и «что отрисовывает frontend» здесь опаснее, чем у валют (валюта без справочника — просто пропавшая строка в
  списке, иконка без соответствующего frontend-компонента — сломанная отрисовка), поэтому единственный безопасный
  источник правды — файл, коммитящийся вместе с кодом обеих частей, а не запись, которую можно завести в рантайме
  через сид независимо от того, добавлен ли компонент на frontend.

**Отклонение от структуры AGENTS.md, обоснование.** `core/icons.py` — не `entity`/`protocol`/`service`/`schema`, а
отдельный модуль верхнего уровня `core/`. Это осознанное отклонение от перечисленных в AGENTS.md подпакетов `core`:
реестр не описывает поведение (нет сценария использования, который оправдывал бы `core/services/icon.py`) и не
имеет реализации за протоколом (нет альтернативной реализации, которую можно было бы подставить — это не
внешняя зависимость, а константа модуля, как `MONEY_MAX_DIGITS`/`MONEY_DECIMAL_PLACES` в `core/schemas/money.py`).
Добавлять `core/services/icon.py` с единственным методом-обёрткой над константой или протокол ради одной
реализации нарушило бы тот же принцип «без лишних слоёв», поэтому `list_icon_names()` вызывается из `api/icons.py`
напрямую, как обычная чистая функция — не нарушает «роутер не содержит бизнес-логики», так как сортировка
статического набора не бизнес-правило, а форма ответа.

### Переиспользуемый Pydantic-тип `IconName`

`backend/src/core/schemas/icon.py`, по аналогии с `Money` (`core/schemas/money.py`):

```python
from typing import Annotated

from pydantic import AfterValidator

from core.icons import ALLOWED_ICONS


def _check_known_icon(value: str) -> str:
    if value not in ALLOWED_ICONS:
        raise ValueError(f"Unknown icon name: {value!r}")
    return value


IconName = Annotated[str, AfterValidator(_check_known_icon)]
```

**Почему `AfterValidator`, а не `Literal[*ALLOWED_ICONS]`.** `Literal` требует значений, известных статическому
анализатору (mypy/basedpyright) на этапе проверки типов; `ALLOWED_ICONS` строится в рантайме из JSON, значит
`Literal` из него собрать нельзя без генерации кода. `AfterValidator` с функцией членства во `frozenset` — O(1)
проверка, привычный для проекта паттерн валидации строки по правилу (как `ck_users_email_lowercase` на уровне БД
для email), не требует кодогенерации и остаётся простым при расширении `icons.json`.

`IconName` в этой задаче не подключается ни к одной реальной схеме (категорий и кошельков ещё нет — 008/009 вне
рамок), но используется в собственном unit-тесте: временная pydantic-модель в тесте проверяет, что известное имя
проходит валидацию, а неизвестное — падает с `ValidationError`.

### Эндпоинт `GET /api/icons`

`backend/src/api/icons.py`, без схемы-обёртки (`response_model=list[str]`) — по аналогии с решением не вводить
`Page`/`PageParams` для маленького статического списка:

```python
from fastapi import APIRouter

from core.icons import list_icon_names

router = APIRouter(prefix="/api/icons", tags=["Icons"])


@router.get("", response_model=list[str])
async def list_icons() -> list[str]:
    return list_icon_names()
```

Подключается в `main.py` рядом с `currencies_router`, без авторизации (справочник не персональные данные, как
`GET /api/currencies`).

Ответ:
```json
["banknote", "briefcase", "bus", "car", "coins", "credit-card", "film", "gamepad-2", "gift", "graduation-cap",
 "heart-pulse", "house", "landmark", "piggy-bank", "plane", "shirt", "shopping-cart", "smartphone",
 "trending-down", "trending-up", "utensils", "wallet", "zap"]
```

**Альтернатива (отвергнута): обёртка `IconsOut { items: list[str] }`.** Отвергнута — обёртка нужна, когда у ответа
есть метаданные (`total`, `limit`, `offset`, как у `Page`) или он может расшириться дополнительными полями; здесь
ответ — весь смысл эндпоинта, и обёртка добавила бы файл `api/schemas/icon.py` ради одного поля без further смысла.

### Frontend: разделение `icons.ts` на `BUSINESS_ICONS` и `UI_ICONS`

**Решение:** `frontend/src/shared/ui/icons.ts` заводит две именованные карты вместо одной плоской:

```ts
/** Бизнес-иконки категорий и кошельков — синхронизированы с backend/src/core/icons.json (см. icons.sync.test.ts). */
const BUSINESS_ICONS: Record<string, LucideIcon> = {
  banknote: Banknote,
  briefcase: Briefcase,
  // ...остальные 21 бизнес-иконок
};

/** Иконки интерфейса приложения — не относятся к категориям/кошелькам, вне реестра iconpack. */
const UI_ICONS: Record<string, LucideIcon> = {
  settings: Settings,
  sun: Sun,
  moon: Moon,
  "log-out": LogOut,
  download: Download,
  share: Share,
  "wifi-off": WifiOff,
};

export const ICONS: Record<string, LucideIcon> = { ...BUSINESS_ICONS, ...UI_ICONS };
export const BUSINESS_ICON_NAMES: readonly string[] = Object.keys(BUSINESS_ICONS);
```

`ICONS`, `resolveIcon`, `Icon.tsx` не меняются по поведению — `ICONS` остаётся объединением, как раньше, поэтому
существующие тесты (`Icon.test.tsx`) продолжают проходить без изменений. `BUSINESS_ICON_NAMES` — единственный новый
экспорт, специально для теста синхронизации.

**Альтернатива (отвергнута): один список исключений `UI_ICON_NAMES` рядом с прежней единой `ICONS`.** Рассмотрена
(«явный список UI-icon-имён рядом с ICONS» из задания), но отвергнута в пользу двух карт: список-исключение — это
неявная связь (нужно помнить, что при добавлении новой бизнес-иконки в `ICONS` список исключений трогать не нужно, а
при добавлении новой UI-иконки — нужно, иначе тест синхронизации ложно потребует добавить её в `icons.json`).
Две явные карты именем говорят о своей природе и не требуют синхронизировать два места при каждом добавлении —
достаточно положить новую иконку в правильную карту один раз.

### Тест синхронизации frontend ↔ backend

Новый файл `frontend/src/shared/ui/icons.sync.test.ts`, по образцу уже существующего чтения внешнего файла в тестах
(`frontend/src/shared/ui/theme/bootstrap.test.ts` читает `index.html` через `readFileSync`/`resolve(process.cwd(),
...)`):

```ts
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { BUSINESS_ICON_NAMES } from "./icons";

describe("реестр иконок синхронизирован с backend", () => {
  it("BUSINESS_ICON_NAMES совпадает с backend/src/core/icons.json", () => {
    const raw = readFileSync(resolve(process.cwd(), "../backend/src/core/icons.json"), "utf-8");
    const backendIcons: string[] = JSON.parse(raw);
    expect(new Set(BUSINESS_ICON_NAMES)).toEqual(new Set(backendIcons));
  });
});
```

`process.cwd()` для `vitest` в этом проекте — `frontend/` (та же база, что использует `bootstrap.test.ts`), поэтому
путь до `backend/src/core/icons.json` — `../backend/src/core/icons.json`. Сравнение — по значению без учёта порядка
(`Set`), потому что порядок в JSON и порядок объявления полей объекта в TS не обязаны совпадать, важен только состав.
Это и есть «правило синхронизации» из задачи 007: рассинхронизация (иконка добавлена в `icons.json`, но не в
`BUSINESS_ICONS`, или наоборот) роняет `make fe-test`/`make test` и обнаруживается в CI, а не в рантайме у
пользователя.

## Risks / Trade-offs

- [Два места хранения одного списка (`icons.json` и `BUSINESS_ICONS` в `icons.ts`) можно рассинхронизировать при
  правке] → тест синхронизации на `vitest` ловит любое расхождение на этапе `make test`/CI, до деплоя.
- [`core/icons.py` — модуль верхнего уровня в `core`, вне устоявшихся подпакетов `entities/schemas/protocols/
  services`] → осознанно и обосновано выше: заводить сервис/протокол ради одной константы без альтернативной
  реализации было бы лишним слоем; прецедент такого же уровня простоты — константы в `core/schemas/money.py`.
- [`IconName` в этой задаче не используется ни одной реальной схемой] → ожидаемо, задача 007 явно готовит тип для
  008/009 (см. Non-goals в proposal.md); он покрыт собственным unit-тестом, чтобы не быть мёртвым непротестированным
  кодом.
- [Относительный путь `../backend/src/core/icons.json` в тесте frontend завязан на монорепозиторий с фиксированной
  структурой каталогов] → так же, как `bootstrap.test.ts` уже завязан на `process.cwd()` == `frontend/`; при смене
  структуры репозитория оба теста потребуют правки синхронно, это не новый риск, а существующий паттерн проекта.

## Migration Plan

Миграция БД не требуется (см. Non-Goals). Шаги внедрения:
1. Добавить `backend/src/core/icons.json`, `core/icons.py`, `core/schemas/icon.py`, `api/icons.py`, подключить
   роутер в `main.py`.
2. Разделить `frontend/src/shared/ui/icons.ts` на `BUSINESS_ICONS`/`UI_ICONS`, экспортировать `BUSINESS_ICON_NAMES`;
   `ICONS`, `resolveIcon`, `Icon.tsx` не меняются.
3. Добавить `frontend/src/shared/ui/icons.sync.test.ts`.
4. Тесты backend (unit + smoke) и frontend (`vitest`), затем полный QualityGate.

Откат: удаление добавленных файлов и роутера; на реестр иконок пока никто не ссылается (кошельки/категории — 008,
009), откат безопасен.

## Open Questions

Все три открытых вопроса задачи 007 (`docs/tasks/007_iconpack.md`) решены:

1. **Полный список Lucide или ограниченное подмножество?** Решено: ограниченное курируемое подмножество — стартовый
   набор из 23 уже существующих бизнес-иконок категорий/кошельков. Весь пакет Lucide (>1000 иконок) не
   поддерживается: поддерживать соответствие такого объёма было бы бессмысленно, а расширение конкретными именами по
   мере необходимости — обычная правка `icons.json` и `BUSINESS_ICONS`.
2. **Как синхронизировать со списком frontend?** Решено: единый источник правды — `backend/src/core/icons.json`;
   frontend не запрашивает его по сети (сохраняется статическая карта имя → компонент для PWA precache/
   tree-shaking), а синхронизация проверяется `vitest`-тестом, читающим тот же файл с диска и сравнивающим его с
   `BUSINESS_ICON_NAMES`.
3. **Версия Lucide?** Решено: уже зафиксирована в задаче 003 (`lucide-react ^1.48.0`, `frontend/package.json`),
   отдельного решения в этой задаче не требуется.
