"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";

import { DialogShell } from "@/components/DialogShell";
import { useToast } from "@/components/ToastProvider";
import { errorMessage } from "@/lib/api/errors";

import { useDeleteCandidates } from "./api";
import type { SelectedCandidate } from "./CandidateTable";

export function DeleteCandidatesDialog({
  open,
  candidates,
  onClose,
  onDeleted,
}: {
  open: boolean;
  candidates: SelectedCandidate[];
  onClose: () => void;
  onDeleted: () => void;
}) {
  const toast = useToast();
  const deleteCandidates = useDeleteCandidates();
  const count = candidates.length;
  const single = count === 1 ? candidates[0] : undefined;

  const close = () => {
    if (deleteCandidates.isPending) return;
    deleteCandidates.reset();
    onClose();
  };

  const confirm = () => {
    deleteCandidates.mutate(
      candidates.map(({ id }) => id),
      {
        onSuccess: () => {
          toast(single ? "Candidate deleted successfully" : `${count} Candidates deleted successfully`);
          deleteCandidates.reset();
          onDeleted();
          onClose();
        },
      },
    );
  };

  return (
    <DialogShell
      open={open}
      title="Delete Candidate"
      minHeight={360}
      onClose={close}
      actions={
        <>
          <Button variant="outlined" onClick={close} disabled={deleteCandidates.isPending}>
            Cancel
          </Button>
          <Button variant="contained" color="error" onClick={confirm} loading={deleteCandidates.isPending}>
            {single ? "Delete candidate" : `Delete ${count} candidates`}
          </Button>
        </>
      }
    >
      {deleteCandidates.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errorMessage(deleteCandidates.error)}
        </Alert>
      )}
      <Typography sx={{ fontSize: 16, lineHeight: "21.6px" }}>
        {single
          ? "Are you sure you want to delete this Candidate?"
          : `Are you sure you want to delete ${count} Candidates?`}
      </Typography>
      <Typography sx={{ mt: "6px", fontSize: 12, lineHeight: "19.9px", letterSpacing: 0.4, color: "text.secondary" }}>
        {single
          ? `This action cannot be undone, and you’ll lose all communication history with ${single.full_name}.`
          : "This action cannot be undone, and you’ll lose all communication history with these candidates"}
      </Typography>
    </DialogShell>
  );
}
