import { useMediaQuery } from "./useMediaQuery";

/** Брейкпоинт `md` antd: экраны уже 768 px считаются телефоном. */
export const MOBILE_BREAKPOINT = 768;
export const DESKTOP_QUERY = `(min-width: ${MOBILE_BREAKPOINT}px)`;

/** Единственная точка выбора между мобильной и широкой разметкой. */
export function useIsMobile(): boolean {
  return !useMediaQuery(DESKTOP_QUERY);
}
