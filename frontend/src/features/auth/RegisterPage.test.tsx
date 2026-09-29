import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { AUTHENTICATED_USER } from "@/test/session";

async function fillAndSubmit(email: string, password: string) {
  await userEvent.type(screen.getByLabelText("Email"), email);
  await userEvent.type(screen.getByLabelText("Пароль"), password);
  await userEvent.click(screen.getByRole("button", { name: "Зарегистрироваться" }));
}

function apiWithRegisterError(error: ApiError) {
  return new FakeApiClient((request) => {
    if (request.path === "/api/auth/me") throw new ApiError({ kind: "unauthorized", status: 401 });
    if (request.path === "/api/auth/register") throw error;
    return { status: "ok" };
  });
}

describe("RegisterPage", () => {
  it("успешная регистрация ведёт на /login с уведомлением", async () => {
    const api = new FakeApiClient((request) => {
      if (request.path === "/api/auth/me")
        throw new ApiError({ kind: "unauthorized", status: 401 });
      if (request.path === "/api/auth/register") return AUTHENTICATED_USER;
      return { status: "ok" };
    });

    renderApp({ apiClient: api, path: "/register" });
    await screen.findByRole("heading", { name: "Регистрация" });

    await fillAndSubmit("user@example.com", "correct-horse-battery");

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
    expect(await screen.findByText("Регистрация выполнена, войдите")).toBeInTheDocument();
  });

  it("регистрация отключена показывает заметное сообщение вместо формы", async () => {
    const api = apiWithRegisterError(
      new ApiError({ kind: "forbidden", status: 403, detail: "Регистрация недоступна" }),
    );

    renderApp({ apiClient: api, path: "/register" });
    await screen.findByRole("heading", { name: "Регистрация" });

    await fillAndSubmit("user@example.com", "correct-horse-battery");

    expect(await screen.findByText("Регистрация недоступна")).toBeInTheDocument();
    expect(screen.queryByText("Недостаточно прав для этого действия")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
  });

  it("занятый email показывает сообщение у поля", async () => {
    const api = apiWithRegisterError(
      new ApiError({
        kind: "conflict",
        status: 409,
        detail: "Пользователь с таким email уже зарегистрирован",
      }),
    );

    renderApp({ apiClient: api, path: "/register" });
    await screen.findByRole("heading", { name: "Регистрация" });

    await fillAndSubmit("user@example.com", "correct-horse-battery");

    expect(await screen.findByText("Такой email уже зарегистрирован")).toBeInTheDocument();
  });

  it("ошибки валидации привязываются к полям", async () => {
    const api = apiWithRegisterError(
      new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { password: ["слишком короткий"] },
      }),
    );

    renderApp({ apiClient: api, path: "/register" });
    await screen.findByRole("heading", { name: "Регистрация" });

    await fillAndSubmit("user@example.com", "1234567890");

    expect(await screen.findByText("слишком короткий")).toBeInTheDocument();
  });
});
