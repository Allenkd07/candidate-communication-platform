import Button from "@mui/material/Button";

import { errorMessage } from "@/lib/api/errors";

import { EmptyState } from "./EmptyState";

/** Inline error for a data view that failed to load, with a way to try again. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <EmptyState
      title="Couldn't load this"
      description={errorMessage(error)}
      action={
        <Button variant="outlined" onClick={onRetry}>
          Retry
        </Button>
      }
    />
  );
}
