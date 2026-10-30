"use client";

import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";

import { DialogShell } from "@/components/DialogShell";
import { ApiError, errorMessage } from "@/lib/api/errors";
import type { SelectedCandidate } from "@/features/candidates/CandidateTable";
import type { MessageTemplate } from "@/lib/api/types";

import { useDeleteTemplate, useSaveTemplate, useTemplates } from "./api";
import { fillIn, toTemplate } from "./placeholders";

type TemplateToolbarProps = {
  /** The message as written for `candidate`. */
  body: string;
  /** The candidate the message box is written for: the first recipient. */
  candidate: SelectedCandidate | undefined;
  /** Receives the template's stored text, placeholders included. */
  onApply: (template: string) => void;
};

const NOTICE_MS = 4000;

/**
 * The template menu and "Save as template", shown above the message box. Templates are shown
 * written out for `candidate`; saving turns that candidate's details back into placeholders.
 * Confirmations appear inline: a toast would cover the drawer's buttons.
 */
export function TemplateToolbar({ body, candidate, onApply }: TemplateToolbarProps) {
  const templates = useTemplates();
  const deleteTemplate = useDeleteTemplate();
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const [applied, setApplied] = useState<MessageTemplate | null>(null);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<{ text: string; error: boolean } | null>(null);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), NOTICE_MS);
    return () => clearTimeout(timer);
  }, [notice]);

  const apply = (template: MessageTemplate) => {
    setApplied(template);
    onApply(template.body);
    setMenuAnchor(null);
  };

  const remove = (template: MessageTemplate) =>
    deleteTemplate.mutate(template.id, {
      onSuccess: () => {
        if (applied?.id === template.id) setApplied(null);
        setNotice({ text: `Template "${template.name}" deleted`, error: false });
      },
      onError: (error) => setNotice({ text: errorMessage(error), error: true }),
    });

  return (
    <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        {notice && (
          <Typography
            variant="caption"
            role="status"
            sx={{ color: notice.error ? "error.main" : "success.main" }}
          >
            {notice.text}
          </Typography>
        )}
        <Button size="small" endIcon={<ArrowDropDownIcon />} onClick={(event) => setMenuAnchor(event.currentTarget)}>
          Templates
        </Button>
        <Button size="small" onClick={() => setSaving(true)} disabled={body.trim() === ""}>
          Save as template
        </Button>
      </Box>
      <Menu
        anchorEl={menuAnchor}
        open={menuAnchor !== null}
        onClose={() => setMenuAnchor(null)}
        slotProps={{ paper: { sx: { width: 360, maxHeight: 360 } } }}
      >
        {templates.isError && <MenuItem disabled>{errorMessage(templates.error)}</MenuItem>}
        {templates.data?.length === 0 && <MenuItem disabled>No templates yet. Save a message to reuse it.</MenuItem>}
        {templates.data?.map((template) => (
          <MenuItem key={template.id} onClick={() => apply(template)} sx={{ alignItems: "flex-start", gap: 1 }}>
            <ListItemText
              primary={template.name}
              secondary={candidate ? fillIn(template.body, candidate) : template.body}
              slotProps={{ secondary: { noWrap: true } }}
              sx={{ minWidth: 0 }}
            />
            <IconButton
              size="small"
              aria-label={`Delete template ${template.name}`}
              onClick={(event) => {
                event.stopPropagation();
                remove(template);
              }}
            >
              <DeleteOutlineIcon fontSize="small" />
            </IconButton>
          </MenuItem>
        ))}
      </Menu>
      <SaveTemplateDialog
        open={saving}
        body={candidate ? toTemplate(body, candidate) : body}
        templates={templates.data ?? []}
        suggestedName={applied?.name ?? ""}
        onClose={() => setSaving(false)}
        onSaved={(template) => {
          setApplied(template);
          setSaving(false);
          setNotice({ text: `Template "${template.name}" saved`, error: false });
        }}
      />
    </Box>
  );
}

function SaveTemplateDialog({
  open,
  body,
  templates,
  suggestedName,
  onClose,
  onSaved,
}: {
  open: boolean;
  body: string;
  templates: MessageTemplate[];
  suggestedName: string;
  onClose: () => void;
  onSaved: (template: MessageTemplate) => void;
}) {
  const save = useSaveTemplate();
  const [name, setName] = useState("");
  const existing = templates.find((template) => template.name.toLowerCase() === name.trim().toLowerCase());
  const fieldError = save.error instanceof ApiError ? save.error.fields.name?.[0] ?? save.error.fields.body?.[0] : undefined;

  const submit = () => {
    if (name.trim() === "") return;
    save.mutate({ name, body, templateId: existing?.id }, { onSuccess: onSaved });
  };

  return (
    <DialogShell
      open={open}
      title={existing ? "Update template" : "Save as template"}
      onClose={onClose}
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      onEntered={() => setName(suggestedName)}
      onExited={() => {
        setName("");
        save.reset();
      }}
      actions={
        <>
          <Button variant="outlined" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="contained" color="accent" disabled={name.trim() === ""} loading={save.isPending}>
            {existing ? "Update template" : "Save template"}
          </Button>
        </>
      }
    >
      <TextField
        label="Template name"
        required
        fullWidth
        autoFocus
        value={name}
        onChange={(event) => setName(event.target.value)}
        error={Boolean(fieldError) || (save.isError && !fieldError)}
        helperText={
          fieldError ??
          (save.isError ? errorMessage(save.error) : existing ? "This replaces the saved text of that template." : undefined)
        }
        slotProps={{ htmlInput: { maxLength: 60 } }}
      />
    </DialogShell>
  );
}
