import { Button, DatePicker, Drawer, Form, Modal, Select } from "antd";
import type { Dayjs } from "dayjs";
import { useEffect } from "react";
import { useCategories } from "@/features/categories/useCategories";
import { useWallets } from "@/features/wallets/useWallets";
import { applyFieldErrors, resolveErrorMessage, toApiError } from "@/shared/errors";
import { MoneyInput, useCurrencies, useIsMobile, useToast } from "@/shared/ui";
import type { TopupFormValues } from "./Transaction";
import { useCreateTopup } from "./useCreateTopup";

export interface TopupFormProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Только создание (design.md, Non-Goals — редактирование пополнения не делается: backend не даёт менять число
 * ног через `PUT`). `amounts` — суммы по валютам выбранного кошелька, адресуемые путём `["amounts", currencyId]`.
 */
interface TopupFormFields {
  wallet_id: string;
  category_id: string;
  amounts: Record<string, string>;
  occurred_at?: Dayjs;
}

/** Осознанно узкий список — design.md, раздел «Обработка ошибок»: ошибки по конкретным ногам и текстовые
 * бизнес-правила (неполный/избыточный набор валют, категория не дохода) единообразно попадают в toast. */
const KNOWN_FIELDS = ["wallet_id", "category_id"] as const;

/** Форма пополнения многовалютного кошелька: динамический набор полей сумм по валютам кошелька (design.md). */
export function TopupForm({ open, onClose }: TopupFormProps) {
  const [form] = Form.useForm<TopupFormFields>();
  const isMobile = useIsMobile();
  const toast = useToast();

  const { data: wallets = [] } = useWallets();
  const { data: categories = [] } = useCategories("income");
  const { data: currencies = [] } = useCurrencies();

  const createTopup = useCreateTopup();

  const walletId = Form.useWatch("wallet_id", form);
  const selectedWallet = wallets.find((wallet) => wallet.id === walletId);
  const currencyById = new Map(currencies.map((currency) => [currency.id, currency]));

  useEffect(() => {
    if (!open) return;
    form.setFieldsValue({
      wallet_id: undefined,
      category_id: undefined,
      amounts: {},
      occurred_at: undefined,
    });
  }, [open, form]);

  const handleWalletChange = (value: string) => {
    form.setFieldsValue({ wallet_id: value, amounts: {} });
  };

  const handleSubmit = (fields: TopupFormFields) => {
    const payload: TopupFormValues = {
      wallet_id: fields.wallet_id,
      category_id: fields.category_id,
      legs: (selectedWallet?.currency_ids ?? []).map((currencyId) => ({
        currency_id: currencyId,
        // Форма требует заполнить сумму каждой валюты (`rules: required`), поэтому на отправке значение всегда
        // есть; `?? ""` — только для типа (`noUncheckedIndexedAccess` не знает про валидацию формы).
        amount: fields.amounts[currencyId] ?? "",
      })),
      occurred_at: fields.occurred_at?.toISOString(),
    };

    const onError = (submitError: unknown) => {
      const apiError = toApiError(submitError);

      if (apiError.kind === "validation") {
        const { byField, toastMessage } = applyFieldErrors(apiError, KNOWN_FIELDS);
        for (const [name, errors] of Object.entries(byField)) {
          form.setFields([{ name: name as keyof TopupFormFields, errors }]);
        }
        toast.error(toastMessage);
        return;
      }
      toast.error(resolveErrorMessage(apiError));
    };

    const onSuccess = () => {
      toast.success("Пополнение создано");
      onClose();
    };

    createTopup.mutate(payload, { onSuccess, onError });
  };

  const content = (
    <Form form={form} layout="vertical" onFinish={handleSubmit} disabled={createTopup.isPending}>
      <Form.Item
        name="wallet_id"
        label="Кошелёк"
        rules={[{ required: true, message: "Выберите кошелёк" }]}
      >
        <Select
          options={wallets.map((wallet) => ({ value: wallet.id, label: wallet.name }))}
          onChange={handleWalletChange}
        />
      </Form.Item>
      {(selectedWallet?.currency_ids ?? []).map((currencyId) => {
        const currency = currencyById.get(currencyId);
        return (
          <Form.Item
            key={currencyId}
            name={["amounts", currencyId]}
            label={`Сумма (${currency?.code ?? "…"})`}
            rules={[{ required: true, message: "Введите сумму" }]}
          >
            <MoneyInput value="" onChange={() => {}} decimalPlaces={currency?.decimalPlaces} />
          </Form.Item>
        );
      })}
      <Form.Item
        name="category_id"
        label="Категория"
        rules={[{ required: true, message: "Выберите категорию" }]}
      >
        <Select
          options={categories.map((category) => ({ value: category.id, label: category.name }))}
        />
      </Form.Item>
      <Form.Item name="occurred_at" label="Дата">
        <DatePicker showTime style={{ width: "100%" }} />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0 }}>
        <Button type="primary" htmlType="submit" block loading={createTopup.isPending}>
          Создать
        </Button>
      </Form.Item>
    </Form>
  );

  return isMobile ? (
    <Drawer placement="bottom" height="80vh" open={open} onClose={onClose} title="Пополнение">
      {content}
    </Drawer>
  ) : (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={960}
      title="Пополнение"
      destroyOnClose
    >
      {content}
    </Modal>
  );
}
