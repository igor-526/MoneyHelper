import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { withSession } from "@/test/session";

async function fillAndSubmit(current: string, next: string) {
  await userEvent.type(screen.getByLabelText("Текущий пароль"), current);
  await userEvent.type(screen.getByLabelText("Новый пароль"), next);
  await userEvent.click(screen.getByRole("button", { name: "Сменить пароль" }));
}

describe("ChangePasswordForm", () => {
  it("успешная смена показывает toast и очищает поля", async () => {
    const api = new FakeApiClient(withSession(() => undefined));

    renderApp({ apiClient: api, path: "/settings" });
    await screen.findByRole("heading", { name: "Настройки" });

    await fillAndSubmit("correct-horse-battery", "new-password-1");

    expect(await screen.findByText("Пароль изменён")).toBeInTheDocument();
    expect(screen.getByLabelText("Текущий пароль")).toHaveValue("");
    expect(screen.getByLabelText("Новый пароль")).toHaveValue("");
    // Сессия осталась активной: защищённая страница по-прежнему доступна.
    expect(screen.getByRole("heading", { name: "Настройки" })).toBeInTheDocument();
  });

  it("неверный текущий пароль показывается у поля, а не «Сессия истекла»", async () => {
    const api = new FakeApiClient(
      withSession((request) => {
        if (request.path === "/api/auth/password") {
          throw new ApiError({
            kind: "unauthorized",
            status: 401,
            detail: "Неверный email или пароль",
          });
        }
        return {};
      }),
    );

    renderApp({ apiClient: api, path: "/settings" });
    await screen.findByRole("heading", { name: "Настройки" });

    await fillAndSubmit("wrong-password", "new-password-1");

    expect(await screen.findByText("Текущий пароль указан неверно")).toBeInTheDocument();
    expect(screen.queryByText("Сессия истекла, войдите снова")).not.toBeInTheDocument();
    // Сессия не сброшена: страница настроек всё ещё доступна.
    expect(screen.getByRole("heading", { name: "Настройки" })).toBeInTheDocument();
  });

  it("ошибка валидации нового пароля привязывается к полю", async () => {
    const api = new FakeApiClient(
      withSession((request) => {
        if (request.path === "/api/auth/password") {
          throw new ApiError({
            kind: "validation",
            status: 400,
            fieldErrors: { new_password: ["слишком короткий"] },
          });
        }
        return {};
      }),
    );

    renderApp({ apiClient: api, path: "/settings" });
    await screen.findByRole("heading", { name: "Настройки" });

    await fillAndSubmit("correct-horse-battery", "eightplus");

    expect(await screen.findByText("слишком короткий")).toBeInTheDocument();
  });
});
