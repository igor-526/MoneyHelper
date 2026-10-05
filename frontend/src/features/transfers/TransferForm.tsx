import { Alert, Button, Drawer, Form, Modal, Select } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useEffect } from "react";
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
  DayPicker,
  toOccurredAt,
} from "@/shared/ui";
import type { Transfer, TransferFormValues } from "./Transfer";
import { useCreateTransfer } from "./useCreateTransfer";
import { useUpdateTransfer } from "./useUpdateTransfer";
import { useDeleteTransfer } from "./useDeleteTransfer";

export interface TransferFormProps {
  open: boolean;
  onClose: () => void;
  /** `undefined` — форма создания; заданный `Transfer` — форма редактирования. */
  transfer?: Transfer;
}

interface TransferFormFields {
  add_another?: boolean;
  from_wallet_id: string;
  to_wallet_id: string;
  amount: string;
  occurred_at?: Dayjs;
}

const KNOWN_FIELDS = ["from_wallet_id", "to_wallet_id", "amount", "occurred_at"] as const;

/** Один компонент для создания и редактирования перевода (design.md, раздел «TransferForm»). */
export function TransferForm({ open, onClose, transfer }: TransferFormProps) {
  const [form] = Form.useForm<TransferFormFields>();
  const isMobile = useIsMobile();
  const toast = useToast();

  const { data: wallets = [] } = useWallets();
  const { data: currencies = [] } = useCurrencies();

  const createTransfer = useCreateTransfer();
  const updateTransfer = useUpdateTransfer();
  const deleteMutation = useDeleteTransfer();
  const mutation = transfer ? updateTransfer : createTransfer;

  const fromWalletId = Form.useWatch("from_wallet_id", form);
  const fromWallet = wallets.find((wallet) => wallet.id === fromWalletId);
  const currency = currencies.find((item) => item.id === fromWallet?.currency_id);
  const targetWallets = fromWallet
    ? wallets.filter(
        (wallet) => wallet.id !== fromWallet.id && wallet.currency_id === fromWallet.currency_id,
      )
    : [];

  useEffect(() => {
    if (!open) return;
    form.setFieldValue("add_another", false);
    if (transfer) {
      form.setFieldsValue({
        from_wallet_id: transfer.from_wallet_id,
        to_wallet_id: transfer.to_wallet_id,
        amount: formatAmount(transfer.amount),
        occurred_at: dayjs(transfer.occurred_at),
      });
    } else {
      form.setFieldsValue({
        from_wallet_id: undefined,
        to_wallet_id: undefined,
        amount: "",
        occurred_at: dayjs(),
      });
    }
  }, [open, transfer, form]);

  const handleFromWalletChange = (value: string) => {
    const currentToWallet = wallets.find(
      (wallet) => wallet.id === form.getFieldValue("to_wallet_id"),
    );
    const from = wallets.find((wallet) => wallet.id === value);
    const keepTarget =
      currentToWallet &&
      currentToWallet.id !== value &&
      currentToWallet.currency_id === from?.currency_id;
    form.setFieldsValue({
      from_wallet_id: value,
      // целевой кошелёк, не подходящий новому исходному (тот же или другая валюта), сбрасывается
      to_wallet_id: keepTarget ? currentToWallet.id : undefined,
    });
  };

  const handleSubmit = (fields: TransferFormFields) => {
    const payload: TransferFormValues = {
      from_wallet_id: fields.from_wallet_id,
      to_wallet_id: fields.to_wallet_id,
      amount: fields.amount,
      occurred_at: fields.occurred_at && toOccurredAt(fields.occurred_at, transfer?.occurred_at),
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
      if (!transfer && fields.add_another) {
        form.setFieldsValue({ amount: "", occurred_at: dayjs() });
        return;
      }
      onClose();
    };

    if (transfer) {
      updateTransfer.mutate({ id: transfer.id, values: payload }, { onSuccess, onError });
    } else {
      createTransfer.mutate(payload, { onSuccess, onError });
    }
  };

  const noTargetWallets = Boolean(fromWallet) && targetWallets.length === 0;

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, { onSuccess: onClose });
  };

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
          disabled={noTargetWallets}
          options={targetWallets.map((wallet) => ({ value: wallet.id, label: wallet.name }))}
        />
      </Form.Item>
      {noTargetWallets ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
          title={`Нет других кошельков в валюте ${currency?.code ?? ""}`.trim()}
          description="Перевод возможен только между кошельками одной валюты. Чтобы получить деньги в другой валюте, пополните нужный кошелёк: конвертация делается через пополнение."
        />
      ) : null}
      <Form.Item
        name="amount"
        label={currency ? `Сумма (${currency.code})` : "Сумма"}
        rules={[{ required: true, message: "Введите сумму" }]}
      >
        <MoneyInput value="" onChange={() => {}} decimalPlaces={currency?.decimalPlaces} />
      </Form.Item>
      <Form.Item name="occurred_at" label="Дата">
        <DayPicker />
      </Form.Item>
      {transfer ? null : <AddAnotherCheckbox />}
      <Form.Item style={{ marginBottom: 0 }}>
        <Button
          type="primary"
          htmlType="submit"
          block
          loading={mutation.isPending}
          disabled={noTargetWallets}
        >
          {transfer ? "Сохранить" : "Создать"}
        </Button>
      </Form.Item>
      {transfer ? (
        <Form.Item style={{ marginTop: 12, marginBottom: 0 }}>
          <ConfirmDeleteButton
            title="Удалить перевод?"
            loading={deleteMutation.isPending}
            onConfirm={() => handleDelete(transfer.id)}
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
