import { describe, expect, it } from "vitest";
import { parseApiError } from "@/shared/api";
import { applyFieldErrors } from "./fieldErrors";

const error = parseApiError(400, {
  detail: [
    { loc: ["body", "email"], msg: "неверный email", type: "value_error" },
    { loc: ["body", "name"], msg: "слишком короткое", type: "value_error" },
    { loc: ["body", "extra"], msg: "не нужно", type: "value_error" },
  ],
});

describe("applyFieldErrors", () => {
  it("привязывает сообщения к полям формы и всегда возвращает общий текст toast", () => {
    const result = applyFieldErrors(error, ["email", "name", "extra"]);
    expect(result.byField).toEqual({
      email: ["неверный email"],
      name: ["слишком короткое"],
      extra: ["не нужно"],
    });
    expect(result.rest).toEqual([]);
    expect(result.toastMessage).toBe("Проверьте заполнение формы");
  });

  it("сообщения неизвестных полей попадают в toast", () => {
    const result = applyFieldErrors(error, ["email"]);
    expect(result.byField).toEqual({ email: ["неверный email"] });
    expect(result.rest).toEqual(["name: слишком короткое", "extra: не нужно"]);
    expect(result.toastMessage).toBe(
      "Проверьте заполнение формы: name: слишком короткое; extra: не нужно",
    );
  });

  it("длинный остаток в toast обрезается", () => {
    const many = parseApiError(400, {
      detail: ["a", "b", "c", "d"].map((f) => ({ loc: ["body", f], msg: "ошибка" })),
    });
    expect(applyFieldErrors(many, []).toastMessage).toBe(
      "Проверьте заполнение формы: a: ошибка; b: ошибка; c: ошибка…",
    );
  });
});
