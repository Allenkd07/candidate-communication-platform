import type { SelectedCandidate } from "@/features/candidates/CandidateTable";

/**
 * Templates are stored with placeholders ({{first_name}}, {{full_name}}) that
 * the server fills in per recipient. Recruiters never see them: the message box shows the text
 * written out for one candidate, and their name is turned back into placeholders on send.
 */
const FIELDS: { key: string; value: (candidate: SelectedCandidate) => string }[] = [
  { key: "full_name", value: (candidate) => candidate.full_name.trim() },
  { key: "first_name", value: (candidate) => candidate.full_name.trim().split(/\s+/)[0] ?? "" },
];

const PLACEHOLDER = /\{\{\s*([A-Za-z_]+)\s*\}\}/g;

export function hasPlaceholders(text: string): boolean {
  return new RegExp(PLACEHOLDER.source).test(text);
}

/** The text as this candidate will receive it. */
export function fillIn(text: string, candidate: SelectedCandidate): string {
  return text.replace(PLACEHOLDER, (match, key: string) => {
    const field = FIELDS.find((item) => item.key === key);
    return field ? field.value(candidate) : match;
  });
}

/** The reverse of fillIn: this candidate's name becomes placeholders again. */
export function toTemplate(text: string, candidate: SelectedCandidate): string {
  // Full name first, so its first name isn't replaced on its own.
  return FIELDS.reduce((result, field) => {
    const value = field.value(candidate);
    if (!value) return result;
    return result.replace(new RegExp(`\\b${escapeRegExp(value)}\\b`, "g"), `{{${field.key}}}`);
  }, text);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
