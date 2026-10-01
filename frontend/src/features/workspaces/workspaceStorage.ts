export const WORKSPACE_STORAGE_KEY = "moneyhelper.workspace";

/** Хранилище выбранного воркспейса; ошибки хранилища не должны ломать приложение (образец `localThemeStorage`). */
export interface WorkspaceStorage {
  get(): string | null;
  set(id: string): void;
}

export const workspaceStorage: WorkspaceStorage = {
  get() {
    try {
      return window.localStorage.getItem(WORKSPACE_STORAGE_KEY);
    } catch {
      return null;
    }
  },
  set(id) {
    try {
      window.localStorage.setItem(WORKSPACE_STORAGE_KEY, id);
    } catch {
      // хранилище недоступно (приватный режим и т.п.): выбор действует до перезагрузки
    }
  },
};
