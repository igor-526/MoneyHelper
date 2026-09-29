import { Button, Drawer, Form, Input, Modal, Segmented } from "antd";
import { useEffect } from "react";
import { applyFieldErrors, resolveErrorMessage, toApiError } from "@/shared/errors";
import { IconPicker, useIsMobile, useToast } from "@/shared/ui";
import type { Category, CategoryFormValues, CategoryType } from "./Category";
import { useCreateCategory } from "./useCreateCategory";
import { useUpdateCategory } from "./useUpdateCategory";

export interface CategoryFormProps {
  open: boolean;
  onClose: () => void;
  /** Тип по умолчанию для новой категории (текущий фильтр списка, если он не «все»). Игнорируется при редактировании. */
  defaultType?: CategoryType;
  /** `undefined` — форма создания; заданная `Category` — форма редактирования, поля предзаполняются её значениями. */
  category?: Category;
}

const KNOWN_FIELDS = ["type", "name", "icon"] as const;
const NAME_CONFLICT_MESSAGE = "Категория с таким названием уже существует в этом типе";

const TYPE_OPTIONS = [
  { label: "Доход", value: "income" },
  { label: "Расход", value: "expense" },
];

/** Один компонент для создания и редактирования категории (design.md, раздел «CategoryForm»). */
export function CategoryForm({ open, onClose, defaultType, category }: CategoryFormProps) {
  const [form] = Form.useForm<CategoryFormValues>();
  const isMobile = useIsMobile();
  const toast = useToast();
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const mutation = category ? updateCategory : createCategory;

  useEffect(() => {
    if (!open) return;
    if (category) {
      form.setFieldsValue({
        type: category.type,
        name: category.name,
        icon: category.icon,
      });
    } else {
      form.setFieldsValue({ type: defaultType ?? "income", name: "", icon: undefined });
    }
  }, [open, category, defaultType, form]);

  const handleSubmit = (values: CategoryFormValues) => {
    const onError = (submitError: unknown) => {
      const apiError = toApiError(submitError);

      if (apiError.kind === "validation") {
        const { byField, toastMessage } = applyFieldErrors(apiError, KNOWN_FIELDS);
        for (const [name, errors] of Object.entries(byField)) {
          form.setFields([{ name: name as keyof CategoryFormValues, errors }]);
        }
        toast.error(toastMessage);
        return;
      }
      if (apiError.kind === "conflict") {
        form.setFields([{ name: "name", errors: [NAME_CONFLICT_MESSAGE] }]);
        return;
      }
      toast.error(resolveErrorMessage(apiError));
    };

    const onSuccess = () => {
      toast.success(category ? "Категория обновлена" : "Категория создана");
      onClose();
    };

    if (category) {
      updateCategory.mutate({ id: category.id, values }, { onSuccess, onError });
    } else {
      createCategory.mutate(values, { onSuccess, onError });
    }
  };

  const title = category ? "Редактировать категорию" : "Создать категорию";
  const content = (
    <Form form={form} layout="vertical" onFinish={handleSubmit} disabled={mutation.isPending}>
      <Form.Item name="type" label="Тип" rules={[{ required: true, message: "Выберите тип" }]}>
        <Segmented aria-label="Тип" options={TYPE_OPTIONS} />
      </Form.Item>
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
      <Form.Item style={{ marginBottom: 0 }}>
        <Button type="primary" htmlType="submit" block loading={mutation.isPending}>
          {category ? "Сохранить" : "Создать"}
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
