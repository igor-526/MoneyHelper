import { render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type * as SharedUi from "@/shared/ui";
import type { DailySpending } from "./dailySpending";
import { SpendingMode } from "./SpendingMode";

vi.mock("@/features/workspaces/useCurrentWorkspace", () => ({
  useCurrentWorkspace: () => ({ currency_id: "rub" }),
}));
vi.mock("@/shared/ui", async (importOriginal) => ({
  ...(await importOriginal<typeof SharedUi>()),
  useCurrencies: () => ({ data: [{ id: "rub", code: "RUB" }] }),
}));
vi.mock("./useAnalytics", () => ({
  useAnalytics: () => ({
    isSuccess: true,
    isPending: false,
    data: {
      buckets: [
        { group_key: "2026-01-01", expense: "10.00", income: "0" },
        { group_key: "2026-01-03", expense: "20.00", income: "0" },
      ],
      unconverted_currencies: [],
    },
  }),
}));
vi.mock("./SpendingChart", () => ({
  SpendingChart: ({ series }: { series: DailySpending[] }) => (
    <div data-testid="chart">{series.map((point) => point.day).join(",")}</div>
  ),
}));

it("скрывает пустые даты на графике, сохраняя их в статистике", () => {
  render(
    <SpendingMode range={{ dateFrom: "2026-01-01T00:00:00", dateTo: "2026-01-03T23:59:59" }} />,
  );
  expect(screen.getByTestId("chart")).toHaveTextContent("2026-01-01,2026-01-03");
  expect(screen.getByTestId("chart")).not.toHaveTextContent("2026-01-02");
  const table = screen.getByRole("table", { name: "Статистика дневных трат" });
  expect(within(table).getByText("Сумма").closest("tr")).toHaveTextContent("30.00 RUB");
  expect(within(table).getByText("Минимум").closest("tr")).toHaveTextContent("0.00 RUB");
  expect(within(table).getByText("Средняя").closest("tr")).toHaveTextContent("10.00 RUB");
  expect(within(table).getByText("Медиана").closest("tr")).toHaveTextContent("10.00 RUB");
});
