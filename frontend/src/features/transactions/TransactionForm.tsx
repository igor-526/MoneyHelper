import { Button, DatePicker, Drawer, Form, Modal, Segmented, Select } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useEffect } from "react";
import type { CategoryType } from "@/features/categories/Category";
import { useCategories } from "@/features/categories/useCategories";
import { useWallets } from "@/features/wallets/useWallets";
import { applyFieldErrors, resolveErrorMessage, toApiError } from "@/shared/errors";
import { CurrencyPicker, MoneyInput, useCurrencies, useIsMobile, useToast } from "@/shared/ui";
import type { Transaction, TransactionFormValues } from "./Transaction";
import { useCreateTransaction } from "./useCreateTransaction";
import { useUpdateTransaction } from "./useUpdateTransaction";

export interface TransactionFormProps {
  open: boolean;
  onClose: () => void;
  /** `undefined` — форма создания; заданная `Transaction` — форма редактирования. */
  transaction?: Transaction;
}

/**
 * Внутренние поля antd Form: `occurred_at` — Dayjs (не строка). `type` — тоже поле Form (для реактивного чтения
 * через `Form.useWatch` и переиспользования встроенного `setFieldsValue` вместо отдельного `useState` + `useEffect`,
 * что нарушало бы `react-hooks/set-state-in-effect`), но НЕ входит в отправляемый `TransactionFormValues` — backend
 * его не принимает, тип полностью определяется `category_id`.
 */
interface TransactionFormFields {
  type: CategoryType;
  wallet_id: string;
  category_id: string;
  currency_id: string;
  amount: string;
  occurred_at?: Dayjs;
}

const KNOWN_FIELDS = ["wallet_id", "category_id", "currency_id", "amount", "occurred_at"] as const;

const TYPE_OPTIONS: { label: string; value: CategoryType }[] = [
  { label: "Доход", value: "income" },
  { label: "Расход", value: "expense" },
];

/** Один компонент для создания и редактирования операции (design.md, раздел «TransactionForm»). */
export function TransactionForm({ open, onClose, transaction }: TransactionFormProps) {
  const [form] = Form.useForm<TransactionFormFields>();
  const isMobile = useIsMobile();
  const toast = useToast();

  // Тип-переключатель — поле Form (для watch/reset без отдельного useState), но не входит в тело запроса
  // (design.md); переключатель только сужает опции Select категории.
  const type = Form.useWatch("type", form) ?? "income";

  const { data: wallets = [] } = useWallets();
  const { data: categories = [] } = useCategories(type);
  // Полный список категорий (независимо от переключателя типа) — нужен, чтобы при открытии формы на
  // редактирование вычислить тип текущей категории операции.
  const { data: allCategories = [] } = useCategories(undefined);
  const { data: currencies = [] } = useCurrencies();

  const createTransaction = useCreateTransaction();
  const updateTransaction = useUpdateTransaction();
  const mutation = transaction ? updateTransaction : createTransaction;

  const walletId = Form.useWatch("wallet_id", form);
  const currencyId = Form.useWatch("currency_id", form);
  const selectedWallet = wallets.find((wallet) => wallet.id === walletId);
  const selectedCurrency = currencies.find((currency) => currency.id === currencyId);

  useEffect(() => {
    if (!open) return;
    if (transaction) {
      const currentCategory = allCategories.find((c) => c.id === transaction.category_id);
      const leg = transaction.legs[0];
      form.setFieldsValue({
        type: currentCategory?.type ?? "income",
        wallet_id: transaction.wallet_id,
        category_id: transaction.category_id,
        currency_id: leg?.currency_id,
        amount: leg?.amount ?? "",
        occurred_at: dayjs(transaction.occurred_at),
      });
    } else {
      form.setFieldsValue({
        type: "income",
        wallet_id: undefined,
        category_id: undefined,
        currency_id: undefined,
        amount: "",
        occurred_at: undefined,
      });
    }
  }, [open, transaction, allCategories, form]);

  const handleTypeChange = (value: CategoryType) => {
    form.setFieldsValue({ type: value, category_id: undefined });
  };

  const handleWalletChange = (value: string) => {
    form.setFieldsValue({ wallet_id: value, currency_id: undefined });
  };

  const handleSubmit = (fields: TransactionFormFields) => {
    const payload: TransactionFormValues = {
      wallet_id: fields.wallet_id,
      category_id: fields.category_id,
      currency_id: fields.currency_id,
      amount: fields.amount,
      occurred_at: fields.occurred_at?.toISOString(),
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
      toast.success(transaction ? "Операция обновлена" : "Операция создана");
      onClose();
    };

    if (transaction) {
      updateTransaction.mutate({ id: transaction.id, values: payload }, { onSuccess, onError });
    } else {
      createTransaction.mutate(payload, { onSuccess, onError });
    }
  };

  const title = transaction ? "Редактировать операцию" : "Создать операцию";
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
      <Form.Item name="type" label="Тип">
        <Segmented aria-label="Тип" options={TYPE_OPTIONS} onChange={handleTypeChange} />
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
        name="currency_id"
        label="Валюта"
        rules={[{ required: true, message: "Выберите валюту" }]}
      >
        {/* `value`/`onChange` — заглушка для типов; Form.Item подставляет настоящие через cloneElement. */}
        <CurrencyPicker
          value={undefined}
          onChange={() => {}}
          allowedIds={selectedWallet?.currency_ids}
        />
      </Form.Item>
      <Form.Item name="amount" label="Сумма" rules={[{ required: true, message: "Введите сумму" }]}>
        <MoneyInput value="" onChange={() => {}} decimalPlaces={selectedCurrency?.decimalPlaces} />
      </Form.Item>
      <Form.Item name="occurred_at" label="Дата">
        <DatePicker showTime style={{ width: "100%" }} />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0 }}>
        <Button type="primary" htmlType="submit" block loading={mutation.isPending}>
          {transaction ? "Сохранить" : "Создать"}
        </Button>
      </Form.Item>
    </Form>
  );

  return isMobile ? (
    <Drawer placement="bottom" height="80vh" open={open} onClose={onClose} title={title}>
      {content}
    </Drawer>
  ) : (
    <Modal open={open} onCancel={onClose} footer={null} width={960} title={title} destroyOnClose>
      {content}
    </Modal>
  );
}
