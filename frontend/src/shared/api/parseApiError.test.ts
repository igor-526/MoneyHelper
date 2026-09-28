import { describe, expect, it } from "vitest";
import { parseApiError } from "./parseApiError";

describe("parseApiError", () => {
  it.each([
    [400, "validation"],
    [401, "unauthorized"],
    [403, "forbidden"],
    [404, "not_found"],
    [409, "conflict"],
    [500, "server"],
    [503, "server"],
    [418, "unknown"],
  ] as const)("статус %s -> %s", (status, kind) => {
    const error = parseApiError(status, { detail: "текст" });
    expect(error.kind).toBe(kind);
    expect(error.status).toBe(status);
    expect(error.detail).toBe("текст");
  });

  it("сохраняет текстовый detail для 409", () => {
    const error = parseApiError(409, { detail: "Кошелёк уже существует" });
    expect(error).toMatchObject({
      kind: "conflict",
      status: 409,
      detail: "Кошелёк уже существует",
    });
  });

  it("собирает ошибки валидации по полям и отбрасывает сегмент body", () => {
    const error = parseApiError(400, {
      detail: [
        { loc: ["body", "email"], msg: "value is not a valid email address", type: "value_error" },
        { loc: ["body", "items", 0, "amount"], msg: "field required", type: "missing" },
        { loc: ["body", "email"], msg: "слишком длинный", type: "value_error" },
      ],
    });
    expect(error.kind).toBe("validation");
    expect(error.detail).toBeNull();
    expect(error.fieldErrors).toEqual({
      email: ["value is not a valid email address", "слишком длинный"],
      "items.0.amount": ["field required"],
    });
  });

  it("сообщения без имени поля попадают в detail", () => {
    const error = parseApiError(400, { detail: [{ loc: ["body"], msg: "неверное тело" }] });
    expect(error.fieldErrors).toEqual({});
    expect(error.detail).toBe("неверное тело");
  });

  it.each([[undefined], [null], ["<html>"], [{ other: 1 }], [{ detail: 42 }]])(
    "тело %j без detail даёт пустой detail",
    (body) => {
      const error = parseApiError(500, body);
      expect(error).toMatchObject({ kind: "server", status: 500, detail: null, fieldErrors: {} });
    },
  );
});
