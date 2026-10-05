import dayjs from "dayjs";
import { describe, expect, it } from "vitest";
import { DATE_RANGE_PRESETS, findActivePreset } from "./dateRangePresets";

function preset(key: string) {
  return DATE_RANGE_PRESETS.find((item) => item.key === key)!;
}

function format([from, to]: [dayjs.Dayjs, dayjs.Dayjs]) {
  return [from.format("YYYY-MM-DD HH:mm"), to.format("YYYY-MM-DD HH:mm")];
}

// Среда, 2026-10-07
const NOW = dayjs("2026-10-07T15:30:00");

describe("DATE_RANGE_PRESETS", () => {
  it("порядок кнопок: сегодня, вчера, неделя, месяц", () => {
    expect(DATE_RANGE_PRESETS.map((item) => item.label)).toEqual([
      "Сегодня",
      "Вчера",
      "Неделя",
      "Месяц",
    ]);
  });

  it("сегодня — весь текущий день", () => {
    expect(format(preset("today").range(NOW))).toEqual(["2026-10-07 00:00", "2026-10-07 23:59"]);
  });

  it("вчера — весь предыдущий день", () => {
    expect(format(preset("yesterday").range(NOW))).toEqual([
      "2026-10-06 00:00",
      "2026-10-06 23:59",
    ]);
  });

  it("неделя — текущая календарная неделя с понедельника по воскресенье", () => {
    expect(format(preset("week").range(NOW))).toEqual(["2026-10-05 00:00", "2026-10-11 23:59"]);
  });

  it("неделя в воскресенье начинается с понедельника той же недели", () => {
    expect(format(preset("week").range(dayjs("2026-10-11T10:00:00")))).toEqual([
      "2026-10-05 00:00",
      "2026-10-11 23:59",
    ]);
  });

  it("неделя в понедельник начинается в этот же день", () => {
    expect(format(preset("week").range(dayjs("2026-10-05T10:00:00")))[0]).toBe("2026-10-05 00:00");
  });

  it("месяц — текущий календарный месяц, а не последние 30 дней", () => {
    expect(format(preset("month").range(NOW))).toEqual(["2026-10-01 00:00", "2026-10-31 23:59"]);
  });
});

describe("findActivePreset", () => {
  it("находит быстрый диапазон по границам дней", () => {
    expect(findActivePreset(preset("week").range(NOW), NOW)).toBe("week");
  });

  it("произвольный диапазон и отсутствие диапазона — без активной кнопки", () => {
    expect(findActivePreset([dayjs("2026-10-02"), dayjs("2026-10-03")], NOW)).toBeUndefined();
    expect(findActivePreset(null, NOW)).toBeUndefined();
  });
});
