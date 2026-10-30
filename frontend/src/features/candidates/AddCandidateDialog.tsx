"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { type Path, useForm, useWatch } from "react-hook-form";
import type { z } from "zod";

import { DialogShell } from "@/components/DialogShell";
import { useToast } from "@/components/ToastProvider";
import { ApiError, errorMessage } from "@/lib/api/errors";

import { useCreateCandidate } from "./api";
import { type CandidateFormValues, candidateSchema } from "./candidateSchema";

const EMPTY: CandidateFormValues = { full_name: "", phone: "", email: "" };
const FIELDS: { name: keyof CandidateFormValues; label: string; type: string; autoComplete: string }[] = [
  { name: "full_name", label: "Candidate Name", type: "text", autoComplete: "name" },
  { name: "phone", label: "Mobile Number", type: "tel", autoComplete: "tel" },
  { name: "email", label: "Email", type: "email", autoComplete: "email" },
];

export function AddCandidateDialog({
  open,
  onClose,
  onAdded,
}: {
  open: boolean;
  onClose: () => void;
  onAdded: () => void;
}) {
  const toast = useToast();
  const createCandidate = useCreateCandidate();
  const form = useForm<CandidateFormValues, unknown, z.output<typeof candidateSchema>>({
    resolver: zodResolver(candidateSchema),
    mode: "onTouched",
    defaultValues: EMPTY,
  });
  const { register, handleSubmit, setError, setFocus, reset, formState } = form;
  const values = useWatch({ control: form.control });
  const allFilled = FIELDS.every(({ name }) => (values[name] ?? "").trim() !== "");
  const anyTyped = FIELDS.some(({ name }) => (values[name] ?? "") !== "");

  const close = () => {
    if (formState.isSubmitting) return;
    onClose();
  };

  const submit = handleSubmit(async (input) => {
    try {
      const candidate = await createCandidate.mutateAsync(input);
      toast(`${candidate.full_name} added successfully`);
      onAdded();
      onClose();
    } catch (error) {
      let placed = false;
      const fields = error instanceof ApiError ? error.fields : {};
      for (const [field, messages] of Object.entries(fields)) {
        if (FIELDS.some(({ name }) => name === field) && messages[0]) {
          setError(field as Path<CandidateFormValues>, { message: messages[0] });
          placed = true;
        }
      }
      if (!placed) {
        setError("root.server", { message: errorMessage(error) });
      }
    }
  });

  const serverError = formState.errors.root?.server?.message;

  return (
    <DialogShell
      open={open}
      title="Add Candidate"
      minHeight={500}
      onClose={close}
      onSubmit={submit}
      onEntered={() => setFocus("full_name")}
      ignoreBackdropClick={anyTyped}
      onExited={() => {
        reset(EMPTY);
        createCandidate.reset();
      }}
      actions={
        <>
          <Button variant="outlined" onClick={close} disabled={formState.isSubmitting}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            color="accent"
            disabled={!allFilled}
            loading={formState.isSubmitting}
          >
            Add candidate
          </Button>
        </>
      }
    >
      <Stack spacing={4}>
        {serverError && <Alert severity="error">{serverError}</Alert>}
        {FIELDS.map(({ name, label, type, autoComplete }) => {
          // An empty field shows no error until it is typed in or the form is submitted.
          const shown = formState.dirtyFields[name] || formState.isSubmitted;
          const fieldError = shown ? formState.errors[name] : undefined;
          return (
            <TextField
              key={name}
              label={label}
              type={type}
              required
              fullWidth
              autoComplete={autoComplete}
              error={Boolean(fieldError)}
              helperText={fieldError?.message}
              disabled={formState.isSubmitting}
              {...register(name)}
            />
          );
        })}
      </Stack>
    </DialogShell>
  );
}
