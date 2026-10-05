import { Button, Drawer, Form, Input, Modal } from "antd";
import { useEffect } from "react";
import { applyFieldErrors, resolveErrorMessage, toApiError } from "@/shared/errors";
import { CurrencyPicker, IconPicker, useIsMobile, useToast } from "@/shared/ui";
import type { Wallet, WalletFormValues } from "./Wallet";
import { useCreateWallet } from "./useCreateWallet";
import { useUpdateWallet } from "./useUpdateWallet";

export interface WalletFormProps {
  open: boolean;
  onClose: () => void;
  /** `undefined` — форма создания; заданный `Wallet` — форма редактирования, поля предзаполняются его значениями. */
  wallet?: Wallet;
}

const KNOWN_FIELDS = ["name", "icon", "currency_id"] as const;

/** Один компонент для создания и редактирования кошелька (design.md, раздел «WalletForm»). */
export function WalletForm({ open, onClose, wallet }: WalletFormProps) {
  const [form] = Form.useForm<WalletFormValues>();
  const isMobile = useIsMobile();
  const toast = useToast();
  const createWallet = useCreateWallet();
  const updateWallet = useUpdateWallet();
  const mutation = wallet ? updateWallet : createWallet;

  useEffect(() => {
    if (!open) return;
    if (wallet) {
      form.setFieldsValue({
        name: wallet.name,
        icon: wallet.icon,
        currency_id: wallet.currency_id,
      });
    } else {
      form.resetFields();
    }
  }, [open, wallet, form]);

  const handleSubmit = (values: WalletFormValues) => {
    const onError = (submitError: unknown) => {
      const apiError = toApiError(submitError);

      if (apiError.kind === "validation") {
        const { byField, toastMessage } = applyFieldErrors(apiError, KNOWN_FIELDS);
        for (const [name, errors] of Object.entries(byField)) {
          form.setFields([{ name: name as keyof WalletFormValues, errors }]);
        }
        toast.error(toastMessage);
        return;
      }
      if (apiError.kind === "conflict") {
        form.setFields([{ name: "currency_id", errors: [resolveErrorMessage(apiError)] }]);
      }
      toast.error(resolveErrorMessage(apiError));
    };

    const onSuccess = () => {
      toast.success(wallet ? "Кошелёк обновлён" : "Кошелёк создан");
      onClose();
    };

    if (wallet) {
      updateWallet.mutate({ id: wallet.id, values }, { onSuccess, onError });
    } else {
      createWallet.mutate(values, { onSuccess, onError });
    }
  };

  const title = wallet ? "Редактировать кошелёк" : "Создать кошелёк";
  const content = (
    <Form form={form} layout="vertical" onFinish={handleSubmit} disabled={mutation.isPending}>
      <Form.Item
        name="name"
        label="Название"
        rules={[{ required: true, message: "Введите название" }]}
      >
        <Input maxLength={100} />
      </Form.Item>
      <Form.Item
        name="icon"
        label="Иконка"
        rules={[{ required: true, message: "Выберите иконку" }]}
      >
        {/* `value`/`onChange` — заглушка для типов; Form.Item подставляет настоящие через cloneElement. */}
        <IconPicker value={undefined} onChange={() => {}} />
      </Form.Item>
      <Form.Item
        name="currency_id"
        label="Валюта"
        rules={[{ required: true, message: "Выберите валюту" }]}
      >
        <CurrencyPicker value={undefined} onChange={() => {}} />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0 }}>
        <Button type="primary" htmlType="submit" block loading={mutation.isPending}>
          {wallet ? "Сохранить" : "Создать"}
        </Button>
      </Form.Item>
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
