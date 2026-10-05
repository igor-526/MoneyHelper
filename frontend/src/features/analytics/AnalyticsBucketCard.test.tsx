import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnalyticsBucketCard } from "./AnalyticsBucketCard";

describe("AnalyticsBucketCard", () => {
  it("рендерит подпись, доход и расход при ненулевых значениях", () => {
    render(
      <AnalyticsBucketCard
        label="Наличные"
        bucket={{ group_key: "w1", income: "150.00", expense: "50.00" }}
        currencyCode="RUB"
      />,
    );

    expect(screen.getByText("Наличные")).toBeInTheDocument();
    expect(screen.getByText("Доход: 150.00 RUB")).toBeInTheDocument();
    expect(screen.getByText("Расход: 50.00 RUB")).toBeInTheDocument();
  });

  it("рендерит нулевой доход без скрытия строки", () => {
    render(
      <AnalyticsBucketCard
        label="Карта"
        bucket={{ group_key: "w2", income: "0", expense: "20.00" }}
        currencyCode="RUB"
      />,
    );

    expect(screen.getByText("Доход: 0 RUB")).toBeInTheDocument();
    expect(screen.getByText("Расход: 20.00 RUB")).toBeInTheDocument();
  });

  it("рендерит нулевой расход без скрытия строки", () => {
    render(
      <AnalyticsBucketCard
        label="Карта"
        bucket={{ group_key: "w2", income: "20.00", expense: "0" }}
        currencyCode="RUB"
      />,
    );

    expect(screen.getByText("Доход: 20.00 RUB")).toBeInTheDocument();
    expect(screen.getByText("Расход: 0 RUB")).toBeInTheDocument();
  });

  it("убирает хвостовые нули восьмизначной суммы backend", () => {
    render(
      <AnalyticsBucketCard
        label="Карта"
        bucket={{ group_key: "w2", income: "78.50000000", expense: "0.00000000" }}
        currencyCode="CNY"
      />,
    );

    expect(screen.getByText("Доход: 78.50 CNY")).toBeInTheDocument();
    expect(screen.getByText("Расход: 0.00 CNY")).toBeInTheDocument();
  });
});
