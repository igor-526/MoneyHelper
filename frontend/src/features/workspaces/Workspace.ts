/** Форма ответа backend (`WorkspaceOut`) — без camelCase-маппинга, тот же принцип, что `Wallet`/`Category`. */
export interface Workspace {
  id: string;
  name: string;
  currency_id: string;
  created_at: string;
  updated_at: string | null;
}

/** Форма тела запроса `WorkspaceCreate`/`WorkspaceUpdate`; совпадает с именами полей формы. */
export interface WorkspaceFormValues {
  name: string;
  currency_id: string;
}
