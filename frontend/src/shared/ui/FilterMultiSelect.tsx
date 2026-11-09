import { Button, Checkbox, Flex, Select, Typography } from "antd";

interface Props {
  label: string;
  options: { value: string; label: string }[];
  value: string[] | undefined;
  onChange: (value: string[]) => void;
}

export function FilterMultiSelect({ label, options, value, onChange }: Props) {
  const selected = value ?? options.map((option) => option.value);
  const selectedSet = new Set(selected);
  const count = options.filter((option) => selectedSet.has(option.value)).length;
  return (
    <Flex vertical gap={8}>
      <Typography.Text>{label}</Typography.Text>
      <Select
        mode="multiple"
        aria-label={label}
        placeholder={label}
        value={selected}
        options={options}
        onChange={onChange}
        maxTagCount="responsive"
        style={{ width: "100%" }}
      />
      <Flex gap={8} align="center" wrap>
        <Checkbox
          style={{ minHeight: 44, alignItems: "center" }}
          checked={options.length > 0 && count === options.length}
          indeterminate={count > 0 && count < options.length}
          onChange={(event) =>
            onChange(event.target.checked ? options.map((option) => option.value) : [])
          }
        >
          Выбрать всё
        </Checkbox>
        <Button
          onClick={() =>
            onChange(
              options
                .filter((option) => !selectedSet.has(option.value))
                .map((option) => option.value),
            )
          }
        >
          Инвертировать
        </Button>
      </Flex>
    </Flex>
  );
}
