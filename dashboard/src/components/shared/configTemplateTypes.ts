export interface TemplateItemMeta {
  type?: string;
  default?: unknown;
  invisible?: boolean;
  description?: string;
  hint?: string;
  condition?: Record<string, unknown>;
  items: Record<string, TemplateItemMeta>;
  [key: string]: unknown;
}

export interface TemplateMeta {
  name?: string;
  hint?: string;
  description?: string;
  hide_hint_in_list?: boolean;
  display_item?: string;
  items: Record<string, TemplateItemMeta>;
  [key: string]: unknown;
}

export type TemplateValue =
  | string
  | number
  | boolean
  | TemplateValue[]
  | { [key: string]: TemplateValue };

export type TemplateEntryValue = TemplateValue & {
  [key: string]: TemplateValue;
};

export type TemplateEntry = {
  __template_key?: string;
} & {
  [key: string]: TemplateEntryValue;
};
