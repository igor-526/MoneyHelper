import { Button, Drawer, Form, Input, Modal, Select } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useEffect } from "react";
import { useCategories } from "@/features/categories/useCategories";
import { useWallets } from "@/features/wallets/useWallets";
import { useCurrentWorkspace } from "@/features/workspaces/useCurrentWorkspace";
import { applyFieldErrors, resolveErrorMessage, toApiError } from "@/shared/errors";
import {
  AddAnotherCheckbox,
  ConfirmDeleteButton,
  formatAmount,
  MoneyInput,
  useCurrencies,
  useIsMobile,
  useToast,
  DayPicker,
  toOccurredAt,
} from "@/shared/ui";
import type { TopupFormValues, Transaction } from "./Transaction";
import { useCreateTopup } from "./useCreateTopup";
import { useUpdateTopup } from "./useUpdateTopup";
import { useDeleteTopup } from "./useDeleteTopup";

export interface TopupFormProps {
  open: boolean;
  onClose: () => void;
  /** `undefined` — форма создания; заданное пополнение — форма редактирования. */
  transaction?: Transaction;
}

/** `amounts` — суммы по валютам ног, адресуемые путём `["amounts", currencyId]`. */
interface TopupFormFields {
  add_another?: boolean;
  wallet_id: string;
  category_id: string;
  amounts: Record<string, string>;
  occurred_at?: Dayjs;
  comment?: string;
}

/** Ошибки по конкретным ногам и текстовые бизнес-правила (набор валют, категория не дохода) попадают в toast. */
const KNOWN_FIELDS = ["wallet_id", "category_id", "occurred_at", "comment"] as const;

/**
 * Форма пополнения (создание и редактирование): суммы в валюте воркспейса и в валюте выбранного кошелька; если
 * валюты совпадают — одно поле.
 */
export function TopupForm({ open, onClose, transaction }: TopupFormProps) {
  const [form] = Form.useForm<TopupFormFields>();
  const isMobile = useIsMobile();
  const toast = useToast();

  const { data: wallets = [] } = useWallets();
  const { data: categories = [] } = useCategories("income");
  const { data: currencies = [] } = useCurrencies();

  const workspace = useCurrentWorkspace();

  const createTopup = useCreateTopup();
  const updateTopup = useUpdateTopup();
  const deleteMutation = useDeleteTopup();
  const mutation = transaction ? updateTopup : createTopup;

  const walletId = Form.useWatch("wallet_id", form);
  const selectedWallet = wallets.find((wallet) => wallet.id === walletId);
  const legCurrencyIds =
    selectedWallet && workspace
      ? [...new Set([workspace.currency_id, selectedWallet.currency_id])]
      : [];
  const currencyById = new Map(currencies.map((currency) => [currency.id, currency]));

  useEffect(() => {
    if (!open) return;
    form.setFieldValue("add_another", false);
    form.setFieldsValue({
      wallet_id: transaction?.wallet_id,
      category_id: transaction?.category_id,
      occurred_at: dayjs(transaction?.occurred_at),
      comment: transaction?.comment ?? undefined,
    });
    form.setFieldValue(
      "amounts",
      Object.fromEntries(
        (transaction?.legs ?? []).map((leg) => [leg.currency_id, formatAmount(leg.amount)]),
      ),
    );
  }, [open, transaction, form]);

  const handleWalletChange = (value: string) => {
    // `setFieldsValue` сливает вложенные объекты, поэтому суммы сбрасываются отдельно, целиком.
    form.setFieldValue("amounts", {});
    form.setFieldValue("wallet_id", value);
  };

  const handleSubmit = (fields: TopupFormFields) => {
    const payload: TopupFormValues = {
      wallet_id: fields.wallet_id,
      category_id: fields.category_id,
      legs: legCurrencyIds.map((currencyId) => ({
        currency_id: currencyId,
        // Сумма каждой валюты обязательна (`rules: required`); `?? ""` — только для типа.
        amount: fields.amounts[currencyId] ?? "",
      })),
      occurred_at: fields.occurred_at && toOccurredAt(fields.occurred_at, transaction?.occurred_at),
      comment: fields.comment,
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
      toast.success(transaction ? "Пополнение обновлено" : "Пополнение создано");
      if (!transaction && fields.add_another) {
        form.setFieldsValue({ occurred_at: dayjs(), comment: undefined });
        form.setFieldValue("amounts", {});
        return;
      }
      onClose();
    };

    if (transaction) {
      updateTopup.mutate({ id: transaction.id, values: payload }, { onSuccess, onError });
    } else {
      createTopup.mutate(payload, { onSuccess, onError });
    }
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, { onSuccess: onClose });
  };

  const title = transaction ? "Редактировать пополнение" : "Создать пополнение";
  const content = (
    <Form form={form} layout="vertical" onFinish={handleSubmit} disabled={mutation.isPending}>
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
      {legCurrencyIds.map((currencyId) => {
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
        <DayPicker />
      </Form.Item>
      <Form.Item
        name="comment"
        label="Комментарий"
        rules={[{ max: 1000, message: "Не более 1000 символов" }]}
      >
        <Input.TextArea rows={2} maxLength={1000} showCount />
      </Form.Item>
      {transaction ? null : <AddAnotherCheckbox />}
      <Form.Item style={{ marginBottom: 0 }}>
        <Button type="primary" htmlType="submit" block loading={mutation.isPending}>
          {transaction ? "Сохранить" : "Создать"}
        </Button>
      </Form.Item>
      {transaction ? (
        <Form.Item style={{ marginTop: 12, marginBottom: 0 }}>
          <ConfirmDeleteButton
            title="Удалить пополнение?"
            loading={deleteMutation.isPending}
            onConfirm={() => handleDelete(transaction.id)}
          />
        </Form.Item>
      ) : null}
    </Form>
  );

  return isMobile ? (
    <Drawer placement="bottom" size="80vh" open={open} onClose={onClose} title={title}>
      {content}
    </Drawer>
  ) : (
    <Modal open={open} onCancel={onClose} footer={null} width={960} title={title} destroyOnHidden>
      {content}
    </Modal>
  );
}
