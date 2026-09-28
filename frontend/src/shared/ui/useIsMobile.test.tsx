import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { setMedia } from "@/test/matchMedia";
import { DESKTOP_QUERY, MOBILE_BREAKPOINT, useIsMobile } from "./useIsMobile";

describe("useIsMobile", () => {
  it("на узком экране возвращает true", () => {
    setMedia(DESKTOP_QUERY, false);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });

  it("на широком экране возвращает false", () => {
    setMedia(DESKTOP_QUERY, true);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });

  it("реагирует на изменение ширины окна", () => {
    setMedia(DESKTOP_QUERY, false);
    const { result } = renderHook(() => useIsMobile());
    act(() => setMedia(DESKTOP_QUERY, true));
    expect(result.current).toBe(false);
  });

  it("порог совпадает с брейкпоинтом md antd", () => {
    expect(MOBILE_BREAKPOINT).toBe(768);
  });
});
