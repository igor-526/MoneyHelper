import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnalyticsBucketCard } from "./AnalyticsBucketCard";

describe("AnalyticsBucketCard", () => {
  it("рендерит подпись, доход и расход при ненулевых значениях", () => {
    render(
      <AnalyticsBucketCard
        label="Наличные"
        bucket={{ group_key: "w1", income: "150.00", expense: "50.00" }}
      />,
    );

    expect(screen.getByText("Наличные")).toBeInTheDocument();
    expect(screen.getByText("Доход: 150.00")).toBeInTheDocument();
    expect(screen.getByText("Расход: 50.00")).toBeInTheDocument();
  });

  it("рендерит нулевой доход без скрытия строки", () => {
    render(
      <AnalyticsBucketCard
        label="Карта"
        bucket={{ group_key: "w2", income: "0", expense: "20.00" }}
      />,
    );

    expect(screen.getByText("Доход: 0")).toBeInTheDocument();
    expect(screen.getByText("Расход: 20.00")).toBeInTheDocument();
  });

  it("рендерит нулевой расход без скрытия строки", () => {
    render(
      <AnalyticsBucketCard
        label="Карта"
        bucket={{ group_key: "w2", income: "20.00", expense: "0" }}
      />,
    );

    expect(screen.getByText("Доход: 20.00")).toBeInTheDocument();
    expect(screen.getByText("Расход: 0")).toBeInTheDocument();
  });
});
