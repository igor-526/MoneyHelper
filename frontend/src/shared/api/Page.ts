/** Форма постраничного ответа backend (`core/schemas/pagination.py`, `Page[T]`). */
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
