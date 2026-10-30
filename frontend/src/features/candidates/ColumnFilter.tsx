"use client";

import FilterListIcon from "@mui/icons-material/FilterList";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import { type FormEvent, type ReactNode, type RefObject, useRef, useState } from "react";

import { STATUS_LABELS } from "@/features/communications/StatusChip";

import type { StatusFilter } from "./api";
import { STATUS_OPTIONS } from "./useCandidatesUrlState";

const PANEL_WIDTH = 280;

type ColumnFilterProps = {
  label: string;
  active: boolean;
  /** The panel's fields; `close` dismisses the panel. */
  children: (close: () => void, focusRef: RefObject<HTMLInputElement | null>) => ReactNode;
};

/** The header's filter icon and the panel it opens. The icon turns blue while a filter is set. */
export function ColumnFilter({ label, active, children }: ColumnFilterProps) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const focusRef = useRef<HTMLInputElement | null>(null);
  const close = () => setAnchor(null);

  return (
    <>
      <IconButton
        size="small"
        aria-label={`Filter by ${label.toLowerCase()}`}
        aria-pressed={active}
        onClick={(event) => setAnchor(event.currentTarget)}
        sx={{ p: 0.5, color: active ? "accent.main" : "icon" }}
      >
        <FilterListIcon sx={{ fontSize: 16 }} />
      </IconButton>
      <Popover
        open={anchor !== null}
        anchorEl={anchor}
        onClose={close}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        // Focus fields here: the focus trap undoes autoFocus.
        slotProps={{ transition: { onEntered: () => focusRef.current?.focus() } }}
      >
        <Box sx={{ width: PANEL_WIDTH, p: 2 }}>{children(close, focusRef)}</Box>
      </Popover>
    </>
  );
}

type FilterFormProps = {
  onApply: () => void;
  onClear: () => void;
  canApply?: boolean;
  children: ReactNode;
};

function FilterForm({ onApply, onClear, canApply = true, children }: FilterFormProps) {
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (canApply) onApply();
  };
  return (
    <Box component="form" onSubmit={submit} noValidate>
      {children}
      <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1, mt: 2 }}>
        <Button onClick={onClear}>Clear</Button>
        <Button type="submit" variant="contained" disabled={!canApply}>
          Apply
        </Button>
      </Box>
    </Box>
  );
}

type FieldProps<T> = {
  value: T;
  onChange: (value: T) => void;
  close: () => void;
  focusRef: RefObject<HTMLInputElement | null>;
};

export function TextFilter({
  label,
  value,
  onChange,
  close,
  focusRef,
  inputMode,
  maxLength,
  allowed,
}: FieldProps<string> & {
  label: string;
  maxLength: number;
  inputMode?: "numeric";
  /** Characters outside this set are dropped as they are typed. */
  allowed?: RegExp;
}) {
  const [draft, setDraft] = useState(value);
  const apply = (next: string) => {
    onChange(next.trim());
    close();
  };
  return (
    <FilterForm onApply={() => apply(draft)} onClear={() => apply("")}>
      <TextField
        label={`${label} contains`}
        size="small"
        fullWidth
        value={draft}
        onChange={(event) =>
          setDraft(allowed ? [...event.target.value].filter((char) => allowed.test(char)).join("") : event.target.value)
        }
        inputRef={focusRef}
        slotProps={{ htmlInput: { maxLength, inputMode } }}
      />
    </FilterForm>
  );
}

export function StatusFilterField({ value, onChange, close, focusRef }: FieldProps<StatusFilter[]>) {
  const [draft, setDraft] = useState<StatusFilter[]>(value);
  const toggle = (status: StatusFilter, checked: boolean) =>
    setDraft((current) => (checked ? [...current, status] : current.filter((item) => item !== status)));
  const apply = (next: StatusFilter[]) => {
    onChange(STATUS_OPTIONS.filter((status) => next.includes(status)));
    close();
  };
  return (
    <FilterForm onApply={() => apply(draft)} onClear={() => apply([])}>
      <FormGroup>
        {STATUS_OPTIONS.map((status, index) => (
          <FormControlLabel
            key={status}
            label={status === "none" ? "No messages" : STATUS_LABELS[status]}
            control={
              <Checkbox
                checked={draft.includes(status)}
                onChange={(event) => toggle(status, event.target.checked)}
                slotProps={{ input: { ref: index === 0 ? focusRef : undefined } }}
              />
            }
          />
        ))}
      </FormGroup>
    </FilterForm>
  );
}

export function DateRangeFilter({
  value,
  onChange,
  close,
  focusRef,
}: FieldProps<{ from: string; to: string }>) {
  const [draft, setDraft] = useState(value);
  const invalid = draft.from !== "" && draft.to !== "" && draft.to < draft.from;
  const apply = (next: { from: string; to: string }) => {
    onChange(next);
    close();
  };
  return (
    <FilterForm onApply={() => apply(draft)} onClear={() => apply({ from: "", to: "" })} canApply={!invalid}>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <TextField
          label="From"
          type="date"
          size="small"
          value={draft.from}
          onChange={(event) => setDraft({ ...draft, from: event.target.value })}
          inputRef={focusRef}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          label="To"
          type="date"
          size="small"
          value={draft.to}
          onChange={(event) => setDraft({ ...draft, to: event.target.value })}
          error={invalid}
          helperText={invalid ? "Pick a date on or after the start date." : undefined}
          slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: draft.from || undefined } }}
        />
      </Box>
    </FilterForm>
  );
}
