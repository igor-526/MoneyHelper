import { DEFAULT_THEME_MODE, parseThemeMode, THEME_STORAGE_KEY, type ThemeMode } from "./mode";

/** Хранилище режима темы; ошибки хранилища не должны ломать приложение. */
export interface ThemeStorage {
  get(): ThemeMode;
  set(mode: ThemeMode): void;
}

export const localThemeStorage: ThemeStorage = {
  get() {
    try {
      return parseThemeMode(window.localStorage.getItem(THEME_STORAGE_KEY));
    } catch {
      return DEFAULT_THEME_MODE;
    }
  },
  set(mode) {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, mode);
    } catch {
      // хранилище недоступно (приватный режим и т.п.): выбор действует до перезапуска
    }
  },
};
