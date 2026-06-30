// API types mirroring the CIdy backend DTOs.

export type FieldType =
  | "text"
  | "rich_text"
  | "number"
  | "currency"
  | "boolean"
  | "single_select"
  | "multi_select"
  | "checkbox_group"
  | "date"
  | "quarter_year"
  | "sdg_target_list"
  | "ga_resolution_list"
  | "repeating_group"
  | "budget_table"
  | "rating_scale";

export interface Constraints {
  required?: boolean;
  max_chars?: number | null;
  max_words?: number | null;
  max_pages?: number | null;
  max_items?: number | null;
  order?: string | null;
  options?: string[] | null;
  min_value?: number | null;
}

export interface SchemaField {
  id: string;
  label: string;
  type: FieldType;
  guidance: string;
  constraints: Constraints;
  fields?: SchemaField[] | null;
}

export interface SchemaSection {
  id: string;
  title: string;
  guidance: string;
  repeating: boolean;
  fields: SchemaField[];
}

export interface TemplateSchema {
  schema_id: string;
  version: string;
  fund: string;
  artifact_type: string;
  title: string;
  sections: SchemaSection[];
}

export interface SchemaInfo {
  schema_id: string;
  version: string;
  fund: string;
  artifact_type: string;
  title: string;
}

export type ArtifactValues = Record<string, unknown>;

export interface ArtifactSummary {
  id: string;
  schema_id: string;
  schema_version: string;
  title: string;
  version_no: number;
  status: string;
  updated_at: string;
}

export interface ArtifactDetail extends ArtifactSummary {
  owner_id: string;
  content: ArtifactValues;
  created_at: string;
}

export interface Issue {
  path: string;
  severity: "error" | "warning";
  message: string;
}

export interface ValidationReport {
  is_valid: boolean;
  required_total: number;
  required_filled: number;
  missing: string[];
  issues: Issue[];
}

export interface SDGSuggestion {
  target: string;
  title: string;
  rationale: string;
}

export interface UserInfo {
  id: string;
  email: string;
}
