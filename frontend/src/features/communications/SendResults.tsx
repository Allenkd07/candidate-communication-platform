"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Skeleton from "@mui/material/Skeleton";
import Typography from "@mui/material/Typography";

import { ErrorState } from "@/components/ErrorState";
import { useToast } from "@/components/ToastProvider";
import { errorMessage } from "@/lib/api/errors";
import type { Batch, MessageStatus } from "@/lib/api/types";
import { formatDateTime, pluralize } from "@/lib/format";

import { batchInFlight, useBatch, useRetryMessages } from "./api";
import { StatusChip } from "./StatusChip";

// Order of the summary line, from furthest along to not yet sent.
const SUMMARY_ORDER: MessageStatus[] = ["read", "delivered", "sent", "queued", "scheduled", "failed"];

export function summarize(counts: Batch["counts"]): string {
  return SUMMARY_ORDER.filter((status) => counts[status] > 0)
    .map((status) => `${counts[status]} ${status}`)
    .join(" · ");
}

/** Live per-recipient results of one send; updates as delivery statuses arrive. */
export function SendResults({ batchId, pollMs }: { batchId: string; pollMs?: number }) {
  const batch = useBatch(batchId, { pollMs });
  const retry = useRetryMessages();
  const toast = useToast();

  if (batch.isError && !batch.data) {
    return <ErrorState error={batch.error} onRetry={() => void batch.refetch()} />;
  }
  if (!batch.data) {
    return <Skeleton variant="rounded" height={160} />;
  }

  const { data } = batch;
  const inFlight = batchInFlight(data);
  const retryable = data.messages.filter((message) => message.can_retry).length;
  const scheduledFor = data.messages.find((message) => message.status === "scheduled")?.scheduled_for ?? null;
  const pending = retry.isPending ? retry.variables : undefined;
  const retrying = (target: { messageId: string } | { batchId: string }) =>
    pending !== undefined &&
    ("messageId" in target
      ? "messageId" in pending && pending.messageId === target.messageId
      : "batchId" in pending && pending.batchId === target.batchId);
  const retryTarget = (target: { messageId: string } | { batchId: string }) =>
    retry.mutate(target, { onError: (error) => toast(errorMessage(error), "error") });

  return (
    <Box>
      <Typography sx={{ fontSize: 16, lineHeight: "21.6px" }}>
        {scheduledFor
          ? `Message to ${pluralize(data.total, "candidate")} scheduled for ${formatDateTime(scheduledFor)}`
          : `Message sent to ${pluralize(data.total, "candidate")}`}
      </Typography>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
        <Typography sx={{ fontWeight: "fontWeightBold" }} aria-live="polite">
          {summarize(data.counts)}
        </Typography>
        {retryable > 0 && (
          <Button
            variant="outlined"
            size="small"
            onClick={() => retryTarget({ batchId: data.id })}
            loading={retrying({ batchId: data.id })}
            disabled={retry.isPending}
          >
            Retry failed ({retryable})
          </Button>
        )}
      </Box>
      <Typography
        variant="body2"
        sx={{ color: "text.secondary", mt: 0.5, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
      >
        {data.messages[0]?.body ?? data.body}
      </Typography>
      <Box sx={{ height: 4, my: 2 }}>{inFlight && <LinearProgress aria-label="Delivering" />}</Box>
      <List disablePadding>
        {data.messages.map((message) => (
          <ListItem
            key={message.id}
            divider
            disableGutters
            sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography>{message.candidate.full_name}</Typography>
              {message.status === "failed" && message.failure_reason && (
                <Typography variant="body2" sx={{ color: "error.main" }}>
                  {message.failure_reason}
                </Typography>
              )}
            </Box>
            {message.can_retry && (
              <Button
                size="small"
                onClick={() => retryTarget({ messageId: message.id })}
                loading={retrying({ messageId: message.id })}
                disabled={retry.isPending}
                aria-label={`Retry the message to ${message.candidate.full_name}`}
                sx={{ minWidth: 0, py: 0 }}
              >
                Retry
              </Button>
            )}
            <StatusChip status={message.status} />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}
