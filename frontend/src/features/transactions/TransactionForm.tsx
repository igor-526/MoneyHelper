import { Button, DatePicker, Drawer, Form, Input, Modal, Select } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useEffect } from "react";
import { useCategories } from "@/features/categories/useCategories";
import { useWallets } from "@/features/wallets/useWallets";
import { applyFieldErrors, resolveErrorMessage, toApiError } from "@/shared/errors";
import {
  AddAnotherCheckbox,
  ConfirmDeleteButton,
  formatAmount,
  MoneyInput,
  useCurrencies,
  useIsMobile,
  useToast,
} from "@/shared/ui";
import type { Transaction, TransactionFormValues } from "./Transaction";
import { useCreateTransaction } from "./useCreateTransaction";
import { useUpdateTransaction } from "./useUpdateTransaction";
import { useDeleteTransaction } from "./useDeleteTransaction";

export interface TransactionFormProps {
  open: boolean;
  onClose: () => void;
  /** `undefined` — форма создания; заданная `Transaction` — форма редактирования. */
  transaction?: Transaction;
}

/** Внутренние поля antd Form: `occurred_at` — Dayjs (не строка). */
interface TransactionFormFields {
  add_another?: boolean;
  wallet_id: string;
  category_id: string;
  amount: string;
  occurred_at?: Dayjs;
  comment?: string;
}

const KNOWN_FIELDS = ["wallet_id", "category_id", "amount", "occurred_at", "comment"] as const;

/** Один компонент для создания и редактирования расхода: валюта — валюта кошелька, не выбирается. */
export function TransactionForm({ open, onClose, transaction }: TransactionFormProps) {
  const [form] = Form.useForm<TransactionFormFields>();
  const isMobile = useIsMobile();
  const toast = useToast();

  const { data: wallets = [] } = useWallets();
  const { data: categories = [] } = useCategories("expense");
  const { data: currencies = [] } = useCurrencies();

  const createTransaction = useCreateTransaction();
  const updateTransaction = useUpdateTransaction();
  const deleteMutation = useDeleteTransaction();
  const mutation = transaction ? updateTransaction : createTransaction;

  const walletId = Form.useWatch("wallet_id", form);
  const walletCurrency = currencies.find(
    (currency) => currency.id === wallets.find((wallet) => wallet.id === walletId)?.currency_id,
  );

  useEffect(() => {
    if (!open) return;
    form.setFieldValue("add_another", false);
    form.setFieldsValue({
      wallet_id: transaction?.wallet_id,
      category_id: transaction?.category_id,
      amount: formatAmount(transaction?.legs[0]?.amount ?? ""),
      occurred_at: transaction ? dayjs(transaction.occurred_at) : undefined,
      comment: transaction?.comment ?? undefined,
    });
  }, [open, transaction, form]);

  const handleSubmit = (fields: TransactionFormFields) => {
    const payload: TransactionFormValues = {
      wallet_id: fields.wallet_id,
      category_id: fields.category_id,
      amount: fields.amount,
      occurred_at: fields.occurred_at?.toISOString(),
      comment: fields.comment,
    };

    const onError = (submitError: unknown) => {
      const apiError = toApiError(submitError);

      if (apiError.kind === "validation") {
        const { byField, toastMessage } = applyFieldErrors(apiError, KNOWN_FIELDS);
        for (const [name, errors] of Object.entries(byField)) {
          form.setFields([{ name: name as keyof TransactionFormFields, errors }]);
        }
        toast.error(toastMessage);
        return;
      }
      toast.error(resolveErrorMessage(apiError));
    };

    const onSuccess = () => {
      toast.success(transaction ? "Расход обновлён" : "Расход создан");
      if (!transaction && fields.add_another) {
        form.setFieldsValue({ amount: "", occurred_at: undefined, comment: undefined });
        return;
      }
      onClose();
    };

    if (transaction) {
      updateTransaction.mutate({ id: transaction.id, values: payload }, { onSuccess, onError });
    } else {
      createTransaction.mutate(payload, { onSuccess, onError });
    }
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, { onSuccess: onClose });
  };

  const title = transaction ? "Редактировать расход" : "Создать расход";
  const content = (
    <Form form={form} layout="vertical" onFinish={handleSubmit} disabled={mutation.isPending}>
      <Form.Item
        name="wallet_id"
        label="Кошелёк"
        rules={[{ required: true, message: "Выберите кошелёк" }]}
      >
        <Select options={wallets.map((wallet) => ({ value: wallet.id, label: wallet.name }))} />
      </Form.Item>
      <Form.Item
        name="category_id"
        label="Категория"
        rules={[{ required: true, message: "Выберите категорию" }]}
      >
        <Select
          options={categories.map((category) => ({ value: category.id, label: category.name }))}
        />
      </Form.Item>
      <Form.Item
        name="amount"
        label={walletCurrency ? `Сумма (${walletCurrency.code})` : "Сумма"}
        rules={[{ required: true, message: "Введите сумму" }]}
      >
        <MoneyInput value="" onChange={() => {}} decimalPlaces={walletCurrency?.decimalPlaces} />
      </Form.Item>
      <Form.Item name="occurred_at" label="Дата">
        <DatePicker showTime style={{ width: "100%" }} />
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
            title="Удалить расход?"
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
