import { Button, DatePicker, Drawer, Form, Modal, Select, Typography } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useEffect, useMemo } from "react";
import { useWallets } from "@/features/wallets/useWallets";
import { applyFieldErrors, resolveErrorMessage, toApiError } from "@/shared/errors";
import { CurrencyPicker, MoneyInput, useCurrencies, useIsMobile, useToast } from "@/shared/ui";
import type { Transfer, TransferFormValues } from "./Transfer";
import { useCreateTransfer } from "./useCreateTransfer";
import { useUpdateTransfer } from "./useUpdateTransfer";

export interface TransferFormProps {
  open: boolean;
  onClose: () => void;
  /** `undefined` — форма создания; заданный `Transfer` — форма редактирования. */
  transfer?: Transfer;
}

interface TransferFormFields {
  from_wallet_id: string;
  to_wallet_id: string;
  currency_id: string;
  amount: string;
  occurred_at?: Dayjs;
}

const KNOWN_FIELDS = [
  "from_wallet_id",
  "to_wallet_id",
  "currency_id",
  "amount",
  "occurred_at",
] as const;

/** Один компонент для создания и редактирования перевода (design.md, раздел «TransferForm»). */
export function TransferForm({ open, onClose, transfer }: TransferFormProps) {
  const [form] = Form.useForm<TransferFormFields>();
  const isMobile = useIsMobile();
  const toast = useToast();

  const { data: wallets = [] } = useWallets();
  const { data: currencies = [] } = useCurrencies();

  const createTransfer = useCreateTransfer();
  const updateTransfer = useUpdateTransfer();
  const mutation = transfer ? updateTransfer : createTransfer;

  const fromWalletId = Form.useWatch("from_wallet_id", form);
  const toWalletId = Form.useWatch("to_wallet_id", form);
  const currencyId = Form.useWatch("currency_id", form);
  const fromWallet = wallets.find((wallet) => wallet.id === fromWalletId);
  const toWallet = wallets.find((wallet) => wallet.id === toWalletId);
  const selectedCurrency = currencies.find((currency) => currency.id === currencyId);

  const commonCurrencyIds = useMemo(() => {
    if (!fromWallet || !toWallet) return undefined;
    return fromWallet.currency_ids.filter((id) => toWallet.currency_ids.includes(id));
  }, [fromWallet, toWallet]);

  useEffect(() => {
    if (!open) return;
    if (transfer) {
      form.setFieldsValue({
        from_wallet_id: transfer.from_wallet_id,
        to_wallet_id: transfer.to_wallet_id,
        currency_id: transfer.currency_id,
        amount: transfer.amount,
        occurred_at: dayjs(transfer.occurred_at),
      });
    } else {
      form.setFieldsValue({
        from_wallet_id: undefined,
        to_wallet_id: undefined,
        currency_id: undefined,
        amount: "",
        occurred_at: undefined,
      });
    }
  }, [open, transfer, form]);

  const handleFromWalletChange = (value: string) => {
    const currentToWalletId = form.getFieldValue("to_wallet_id");
    form.setFieldsValue({
      from_wallet_id: value,
      // смена исходного кошелька, совпадающая с текущим целевым, сбрасывает целевой (постановка задачи, п. 5)
      to_wallet_id: currentToWalletId === value ? undefined : currentToWalletId,
      currency_id: undefined,
    });
  };

  const handleToWalletChange = (value: string) => {
    form.setFieldsValue({ to_wallet_id: value, currency_id: undefined });
  };

  const handleSubmit = (fields: TransferFormFields) => {
    const payload: TransferFormValues = {
      from_wallet_id: fields.from_wallet_id,
      to_wallet_id: fields.to_wallet_id,
      currency_id: fields.currency_id,
      amount: fields.amount,
      occurred_at: fields.occurred_at?.toISOString(),
    };

    const onError = (submitError: unknown) => {
      const apiError = toApiError(submitError);

      if (apiError.kind === "validation") {
        const { byField, toastMessage } = applyFieldErrors(apiError, KNOWN_FIELDS);
        for (const [name, errors] of Object.entries(byField)) {
          form.setFields([{ name: name as keyof TransferFormFields, errors }]);
        }
        toast.error(toastMessage);
        return;
      }
      toast.error(resolveErrorMessage(apiError));
    };

    const onSuccess = () => {
      toast.success(transfer ? "Перевод обновлён" : "Перевод создан");
      onClose();
    };

    if (transfer) {
      updateTransfer.mutate({ id: transfer.id, values: payload }, { onSuccess, onError });
    } else {
      createTransfer.mutate(payload, { onSuccess, onError });
    }
  };

  const noCommonCurrency = Boolean(fromWallet && toWallet && commonCurrencyIds?.length === 0);

  const title = transfer ? "Редактировать перевод" : "Создать перевод";
  const content = (
    <Form form={form} layout="vertical" onFinish={handleSubmit} disabled={mutation.isPending}>
      <Form.Item
        name="from_wallet_id"
        label="Откуда"
        rules={[{ required: true, message: "Выберите кошелёк" }]}
      >
        <Select
          options={wallets.map((wallet) => ({ value: wallet.id, label: wallet.name }))}
          onChange={handleFromWalletChange}
        />
      </Form.Item>
      <Form.Item
        name="to_wallet_id"
        label="Куда"
        rules={[{ required: true, message: "Выберите кошелёк" }]}
      >
        <Select
          options={wallets
            .filter((wallet) => wallet.id !== fromWalletId)
            .map((wallet) => ({ value: wallet.id, label: wallet.name }))}
          onChange={handleToWalletChange}
        />
      </Form.Item>
      {noCommonCurrency ? (
        <Form.Item label="Валюта">
          <Typography.Text type="warning">У этих кошельков нет общей валюты</Typography.Text>
        </Form.Item>
      ) : (
        <Form.Item
          name="currency_id"
          label="Валюта"
          rules={[{ required: true, message: "Выберите валюту" }]}
        >
          {/* `value`/`onChange` — заглушка для типов; Form.Item подставляет настоящие через cloneElement. */}
          <CurrencyPicker value={undefined} onChange={() => {}} allowedIds={commonCurrencyIds} />
        </Form.Item>
      )}
      <Form.Item name="amount" label="Сумма" rules={[{ required: true, message: "Введите сумму" }]}>
        <MoneyInput value="" onChange={() => {}} decimalPlaces={selectedCurrency?.decimalPlaces} />
      </Form.Item>
      <Form.Item name="occurred_at" label="Дата">
        <DatePicker showTime style={{ width: "100%" }} />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0 }}>
        <Button type="primary" htmlType="submit" block loading={mutation.isPending}>
          {transfer ? "Сохранить" : "Создать"}
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
