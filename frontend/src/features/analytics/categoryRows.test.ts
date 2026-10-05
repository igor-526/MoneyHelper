import { describe, expect, it } from "vitest";
import type { Category } from "@/features/categories/Category";
import {
  buildCategoryRows,
  type CategoryRow,
  foldRows,
  shareOf,
  sortRows,
  totalAmount,
} from "./categoryRows";

const CATEGORIES = new Map<string, Category>([
  ["c1", { id: "c1", type: "expense", name: "Продукты", icon: "coins" } as Category],
  ["c2", { id: "c2", type: "expense", name: "Кафе", icon: "coins" } as Category],
]);

function row(id: string, name: string, amount: string): CategoryRow {
  return { id, name, icon: undefined, amount };
}

describe("buildCategoryRows", () => {
  it("превращает корзины в строки с названием и иконкой, нулевые расходы отбрасывает", () => {
    const rows = buildCategoryRows(
      [
        { group_key: "c1", income: "0", expense: "150.00" },
        { group_key: "c2", income: "0", expense: "0.00" },
      ],
      CATEGORIES,
    );

    expect(rows).toEqual([{ id: "c1", name: "Продукты", icon: "coins", amount: "150.00" }]);
  });

  it("неизвестная категория получает прочерк вместо названия", () => {
    const rows = buildCategoryRows([{ group_key: "zz", income: "0", expense: "5.00" }], CATEGORIES);

    expect(rows[0]?.name).toBe("…");
  });
});

describe("sortRows", () => {
  const rows = [row("a", "А", "10"), row("b", "Б", "30"), row("c", "В", "20")];

  it("по убыванию и по возрастанию суммы", () => {
    expect(sortRows(rows, "desc").map((r) => r.id)).toEqual(["b", "c", "a"]);
    expect(sortRows(rows, "asc").map((r) => r.id)).toEqual(["a", "c", "b"]);
  });

  it("не изменяет исходный массив; равные суммы — по названию", () => {
    const equal = [row("b", "Б", "10"), row("a", "А", "10")];

    expect(sortRows(equal, "desc").map((r) => r.id)).toEqual(["a", "b"]);
    expect(equal.map((r) => r.id)).toEqual(["b", "a"]);
  });
});

describe("totalAmount и shareOf", () => {
  it("итог — точная сумма строк, доля — процент от итога", () => {
    const rows = [row("a", "А", "0.10"), row("b", "Б", "0.30")];

    expect(totalAmount(rows)).toBe("0.40");
    expect(shareOf(rows[0]!, "0.40")).toBeCloseTo(25);
  });

  it("при нулевом итоге доля — 0", () => {
    expect(shareOf(row("a", "А", "0"), "0")).toBe(0);
  });
});

describe("foldRows", () => {
  it("не больше limit строк остаются как есть, по убыванию", () => {
    expect(foldRows([row("a", "А", "1"), row("b", "Б", "2")], 3).map((r) => r.id)).toEqual([
      "b",
      "a",
    ]);
  });

  it("лишние категории сворачиваются в «Прочие» с суммой остатка", () => {
    const rows = [
      row("a", "А", "40"),
      row("b", "Б", "30"),
      row("c", "В", "20"),
      row("d", "Г", "10"),
    ];

    const folded = foldRows(rows, 2);

    expect(folded.map((r) => [r.name, r.amount])).toEqual([
      ["А", "40"],
      ["Б", "30"],
      ["Прочие", "30"],
    ]);
  });
});
