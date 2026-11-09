import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { FilterMultiSelect } from "./FilterMultiSelect";

const options = [
  { value: "a", label: "Первый" },
  { value: "b", label: "Второй" },
];
it("выбирает все значения и инвертирует частичный выбор", async () => {
  const onChange = vi.fn();
  render(
    <FilterMultiSelect label="Кошельки" value={["a"]} options={options} onChange={onChange} />,
  );
  await userEvent.click(screen.getByRole("button", { name: "Инвертировать" }));
  expect(onChange).toHaveBeenLastCalledWith(["b"]);
  await userEvent.click(screen.getByRole("checkbox", { name: "Выбрать всё" }));
  expect(onChange).toHaveBeenLastCalledWith(["a", "b"]);
});
it("снимает полный выбор", async () => {
  const onChange = vi.fn();
  render(
    <FilterMultiSelect label="Кошельки" value={undefined} options={options} onChange={onChange} />,
  );
  await userEvent.click(screen.getByRole("checkbox", { name: "Выбрать всё" }));
  expect(onChange).toHaveBeenCalledWith([]);
});
