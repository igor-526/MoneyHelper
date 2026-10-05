import type { Dayjs } from "dayjs";

export type DateRange = [Dayjs, Dayjs];

export interface DateRangePreset {
  key: string;
  label: string;
  range: (now: Dayjs) => DateRange;
}

const DAYS_IN_WEEK = 7;

/** Неделя начинается с понедельника независимо от локали dayjs. */
function startOfWeek(now: Dayjs): Dayjs {
  return now.subtract((now.day() + DAYS_IN_WEEK - 1) % DAYS_IN_WEEK, "day").startOf("day");
}

/** Быстрые диапазоны под выбором дат; новый вариант — новая строка таблицы. */
export const DATE_RANGE_PRESETS: readonly DateRangePreset[] = [
  { key: "today", label: "Сегодня", range: (now) => [now.startOf("day"), now.endOf("day")] },
  {
    key: "yesterday",
    label: "Вчера",
    range: (now) => {
      const yesterday = now.subtract(1, "day");
      return [yesterday.startOf("day"), yesterday.endOf("day")];
    },
  },
  {
    key: "week",
    label: "Неделя",
    range: (now) => {
      const start = startOfWeek(now);
      return [start, start.add(DAYS_IN_WEEK - 1, "day").endOf("day")];
    },
  },
  {
    key: "month",
    label: "Месяц",
    range: (now) => [now.startOf("month"), now.endOf("month")],
  },
];

/** Совпадает ли выбранный диапазон с быстрым (по границам дней) — для подсветки активной кнопки. */
export function findActivePreset(range: DateRange | null, now: Dayjs): string | undefined {
  if (range === null) return undefined;
  return DATE_RANGE_PRESETS.find((preset) => {
    const [from, to] = preset.range(now);
    return from.isSame(range[0], "day") && to.isSame(range[1], "day");
  })?.key;
}
