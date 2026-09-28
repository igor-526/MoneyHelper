import { ConfigProvider, theme as antdTheme } from "antd";
import ruRU from "antd/locale/ru_RU";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useMediaQuery } from "../useMediaQuery";
import { type ResolvedTheme, resolveTheme, THEME_COLOR, type ThemeMode } from "./mode";
import { localThemeStorage, type ThemeStorage } from "./storage";
import { APP_TOKENS } from "./tokens";

export const DARK_QUERY = "(prefers-color-scheme: dark)";

interface ThemeContextValue {
  mode: ThemeMode;
  resolved: ResolvedTheme;
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyToDocument(resolved: ResolvedTheme): void {
  const root = document.documentElement;
  root.setAttribute("data-theme", resolved);
  root.style.colorScheme = resolved;
  // Единый theme-color по текущей теме; media-варианты из index.html нужны только до загрузки JS
  document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]').forEach((meta) => {
    meta.removeAttribute("media");
    meta.content = THEME_COLOR[resolved];
  });
}

export function ThemeProvider({
  children,
  storage = localThemeStorage,
}: {
  children: ReactNode;
  storage?: ThemeStorage;
}) {
  const [mode, setModeState] = useState<ThemeMode>(() => storage.get());
  const systemDark = useMediaQuery(DARK_QUERY);
  const resolved = resolveTheme(mode, systemDark);

  useEffect(() => applyToDocument(resolved), [resolved]);

  const setMode = useCallback(
    (next: ThemeMode) => {
      storage.set(next);
      setModeState(next);
    },
    [storage],
  );

  const value = useMemo(() => ({ mode, resolved, setMode }), [mode, resolved, setMode]);
  const algorithm = resolved === "dark" ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm;

  return (
    <ThemeContext.Provider value={value}>
      <ConfigProvider locale={ruRU} theme={{ algorithm, token: APP_TOKENS }}>
        {children}
      </ConfigProvider>
    </ThemeContext.Provider>
  );
}

export function useThemeMode(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) {
    throw new Error("useThemeMode нужно вызывать внутри ThemeProvider");
  }
  return value;
}
