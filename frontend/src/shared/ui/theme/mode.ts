export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "moneyhelper.theme";
export const DEFAULT_THEME_MODE: ThemeMode = "system";

export function resolveTheme(mode: ThemeMode, systemPrefersDark: boolean): ResolvedTheme {
  if (mode === "system") return systemPrefersDark ? "dark" : "light";
  return mode;
}

/** Некорректное значение (например, из повреждённого хранилища) заменяется режимом по умолчанию. */
export function parseThemeMode(value: unknown): ThemeMode {
  return value === "light" || value === "dark" || value === "system" ? value : DEFAULT_THEME_MODE;
}

/** Цвет фона страницы для `<meta name="theme-color">` (совпадает с colorBgLayout antd). */
export const THEME_COLOR: Record<ResolvedTheme, string> = {
  light: "#f5f5f5",
  dark: "#000000",
};
