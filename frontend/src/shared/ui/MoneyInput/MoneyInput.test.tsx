import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Form } from "antd";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { MoneyInput } from "./MoneyInput";

function Harness({
  decimalPlaces,
  onChange,
}: {
  decimalPlaces?: number;
  onChange: (value: string) => void;
}) {
  const [value, setValue] = useState("");
  return (
    <MoneyInput
      value={value}
      decimalPlaces={decimalPlaces}
      onChange={(next) => {
        setValue(next);
        onChange(next);
      }}
    />
  );
}

describe("MoneyInput", () => {
  it("значение, передаваемое в onChange, всегда строка", async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);

    await userEvent.type(screen.getByRole("textbox"), "12.5");

    for (const call of onChange.mock.calls) {
      expect(typeof call[0]).toBe("string");
    }
    expect(screen.getByRole("textbox")).toHaveValue("12.5");
  });

  it("недопустимый символ отклоняется: значение поля не меняется", async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);

    await userEvent.type(screen.getByRole("textbox"), "a");

    expect(screen.getByRole("textbox")).toHaveValue("");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("вторая точка отклоняется", async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);

    await userEvent.type(screen.getByRole("textbox"), "1..2");

    expect(screen.getByRole("textbox")).toHaveValue("1.2");
  });

  it("запятая отображается и передаётся как точка", async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);

    await userEvent.type(screen.getByRole("textbox"), "12,5");

    expect(screen.getByRole("textbox")).toHaveValue("12.5");
    expect(onChange).toHaveBeenLastCalledWith("12.5");
  });

  it("превышение decimalPlaces отклоняется", async () => {
    const onChange = vi.fn();
    render(<Harness decimalPlaces={2} onChange={onChange} />);

    await userEvent.type(screen.getByRole("textbox"), "1.234");

    expect(screen.getByRole("textbox")).toHaveValue("1.23");
  });

  it("работает внутри Form.Item без дополнительных пропов формы (getValueFromEvent/valuePropName не нужны)", async () => {
    const onFinish = vi.fn();
    function FormHarness() {
      const [form] = Form.useForm();
      return (
        <Form form={form} initialValues={{ amount: "" }} onFinish={onFinish}>
          {/* value/onChange ниже — заглушки: Form.Item подменяет их значением и обработчиком поля формы. */}
          <Form.Item name="amount" label="Сумма">
            <MoneyInput value="" onChange={() => {}} />
          </Form.Item>
          <button type="submit">Отправить</button>
        </Form>
      );
    }
    render(<FormHarness />);

    await userEvent.type(screen.getByLabelText("Сумма"), "42.5");
    await userEvent.click(screen.getByRole("button", { name: "Отправить" }));

    expect(onFinish).toHaveBeenCalledWith({ amount: "42.5" });
  });
});
