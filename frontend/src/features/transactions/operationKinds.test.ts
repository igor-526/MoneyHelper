import { describe, expect, it } from "vitest";
import {
  DEFAULT_OPERATION_KIND,
  EXPENSE_KIND,
  findOperationKind,
  OPERATION_KINDS,
  TOPUP_KIND,
} from "./operationKinds";

describe("OPERATION_KINDS", () => {
  it("содержит вкладки «Расход» и «Пополнение» с уникальными ключами", () => {
    expect(OPERATION_KINDS.map((kind) => [kind.key, kind.label])).toEqual([
      ["expense", "Расход"],
      ["topup", "Пополнение"],
    ]);
  });

  it("пополнение — категории дохода, расход — категории расхода", () => {
    expect([TOPUP_KIND.categoryType, EXPENSE_KIND.categoryType]).toEqual(["income", "expense"]);
  });

  it("findOperationKind возвращает вид по ключу, иначе вид по умолчанию", () => {
    expect(findOperationKind("topup").key).toBe("topup");
    expect(DEFAULT_OPERATION_KIND.key).toBe("expense");
    expect(findOperationKind("transfer")).toBe(DEFAULT_OPERATION_KIND);
    expect(findOperationKind("unknown")).toBe(DEFAULT_OPERATION_KIND);
    expect(findOperationKind(null)).toBe(DEFAULT_OPERATION_KIND);
  });
});
