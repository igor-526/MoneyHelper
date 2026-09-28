type Listener = (event: MediaQueryListEvent) => void;

interface MediaState {
  matches: boolean;
  listeners: Set<Listener>;
}

const states = new Map<string, MediaState>();
const defaults = new Map<string, boolean>();

function stateFor(query: string): MediaState {
  let state = states.get(query);
  if (!state) {
    state = { matches: defaults.get(query) ?? false, listeners: new Set() };
    states.set(query, state);
  }
  return state;
}

function createMediaQueryList(query: string): MediaQueryList {
  const state = stateFor(query);
  return {
    get matches() {
      return state.matches;
    },
    media: query,
    onchange: null,
    addEventListener: (_: string, listener: EventListenerOrEventListenerObject) =>
      state.listeners.add(listener as Listener),
    removeEventListener: (_: string, listener: EventListenerOrEventListenerObject) =>
      state.listeners.delete(listener as Listener),
    addListener: (listener: Listener) => state.listeners.add(listener),
    removeListener: (listener: Listener) => state.listeners.delete(listener),
    dispatchEvent: () => true,
  } as MediaQueryList;
}

/** Подменяет `window.matchMedia` управляемой реализацией и сбрасывает состояние. */
export function resetMatchMedia(): void {
  states.clear();
  defaults.clear();
  window.matchMedia = (query: string) => createMediaQueryList(query);
}

/** Задаёт значение запроса и уведомляет подписчиков (эмуляция смены размера окна/настройки системы). */
export function setMedia(query: string, matches: boolean): void {
  defaults.set(query, matches);
  const state = stateFor(query);
  state.matches = matches;
  state.listeners.forEach((listener) => listener({ matches, media: query } as MediaQueryListEvent));
}
