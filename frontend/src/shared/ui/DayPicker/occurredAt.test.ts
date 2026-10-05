import dayjs from "dayjs";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toOccurredAt } from "./occurredAt";

describe("toOccurredAt", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 0, 15, 14, 30, 5));
  });
  afterEach(() => vi.useRealTimers());

  it("берёт текущее время суток для выбранной даты", () => {
    const result = toOccurredAt(dayjs(new Date(2026, 0, 14)));

    expect(dayjs(result).format("YYYY-MM-DD HH:mm:ss")).toBe("2026-01-14 14:30:05");
  });

  it("сохраняет исходный момент, если дата не менялась", () => {
    const original = new Date(2026, 0, 14, 9, 0, 0).toISOString();

    expect(toOccurredAt(dayjs(new Date(2026, 0, 14)), original)).toBe(original);
  });

  it("при смене даты у существующей операции берёт текущее время суток", () => {
    const original = new Date(2026, 0, 14, 9, 0, 0).toISOString();

    const result = toOccurredAt(dayjs(new Date(2026, 0, 13)), original);

    expect(dayjs(result).format("YYYY-MM-DD HH:mm")).toBe("2026-01-13 14:30");
  });
});
