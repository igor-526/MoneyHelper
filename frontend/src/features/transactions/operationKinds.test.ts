import { describe, expect, it } from "vitest";
import {
  DEFAULT_OPERATION_KIND,
  EXPENSE_KIND,
  findOperationKind,
  OPERATION_KINDS,
  TOPUP_KIND,
} from "./operationKinds";

describe("OPERATION_KINDS", () => {
  it("содержит вкладки «Пополнение», «Расход» и «Перевод» с уникальными ключами", () => {
    expect(OPERATION_KINDS.map((kind) => [kind.key, kind.label])).toEqual([
      ["topup", "Пополнение"],
      ["expense", "Расход"],
      ["transfer", "Перевод"],
    ]);
  });

  it("пополнение — категории дохода, расход — категории расхода", () => {
    expect([TOPUP_KIND.categoryType, EXPENSE_KIND.categoryType]).toEqual(["income", "expense"]);
  });

  it("findOperationKind возвращает вид по ключу, иначе вид по умолчанию", () => {
    expect(findOperationKind("expense").key).toBe("expense");
    expect(findOperationKind("transfer").key).toBe("transfer");
    expect(findOperationKind("unknown")).toBe(DEFAULT_OPERATION_KIND);
    expect(findOperationKind(null)).toBe(DEFAULT_OPERATION_KIND);
  });
});
