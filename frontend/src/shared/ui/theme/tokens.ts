import type { ThemeConfig } from "antd";

/** Минимальная высота touch-цели (px). */
export const TOUCH_TARGET = 44;

/** Токены общие для светлой и тёмной тем: размеры не зависят от темы. */
export const APP_TOKENS: NonNullable<ThemeConfig["token"]> = {
  controlHeight: TOUCH_TARGET,
  controlHeightLG: 52,
  controlHeightSM: 36,
  fontSize: 16,
  borderRadius: 10,
  paddingSM: 12,
  marginSM: 12,
  paddingXS: 8,
};
