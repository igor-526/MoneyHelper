import type { ComponentType } from "react";
import type { AnalyticsRange } from "./Analytics";
import { CategoriesMode } from "./CategoriesMode";
import { SpendingMode } from "./SpendingMode";

/** Режим аналитики — один вариант выбора вверху страницы. Новый режим — новая строка таблицы. */
export interface AnalyticsMode {
  key: string;
  label: string;
  Panel: ComponentType<{ range: AnalyticsRange }>;
}

export const ANALYTICS_MODES: readonly AnalyticsMode[] = [
  { key: "categories", label: "Категории", Panel: CategoriesMode },
  { key: "spending", label: "Трата", Panel: SpendingMode },
];

export const DEFAULT_ANALYTICS_MODE = ANALYTICS_MODES[0]!;
