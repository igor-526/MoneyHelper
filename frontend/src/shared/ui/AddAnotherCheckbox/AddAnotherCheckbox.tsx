import { Checkbox, Form } from "antd";

/** Поле формы `add_another`: после успешного создания форма остаётся открытой. */
export function AddAnotherCheckbox() {
  return (
    <Form.Item name="add_another" valuePropName="checked">
      <Checkbox>Добавить ещё</Checkbox>
    </Form.Item>
  );
}
