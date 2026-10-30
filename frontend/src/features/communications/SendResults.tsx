"use client";

import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Skeleton from "@mui/material/Skeleton";
import Typography from "@mui/material/Typography";

import { ErrorState } from "@/components/ErrorState";
import type { Batch, MessageStatus } from "@/lib/api/types";
import { pluralize } from "@/lib/format";

import { batchInFlight, useBatch } from "./api";
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

  if (batch.isError && !batch.data) {
    return <ErrorState error={batch.error} onRetry={() => void batch.refetch()} />;
  }
  if (!batch.data) {
    return <Skeleton variant="rounded" height={160} />;
  }

  const { data } = batch;
  const inFlight = batchInFlight(data);

  return (
    <Box>
      <Typography sx={{ fontSize: 16, lineHeight: "21.6px" }}>
        Message sent to {pluralize(data.total, "candidate")}
      </Typography>
      <Typography sx={{ fontWeight: "fontWeightBold" }} aria-live="polite">
        {summarize(data.counts)}
      </Typography>
      <Typography
        variant="body2"
        sx={{ color: "text.secondary", mt: 0.5, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
      >
        {data.body}
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
            <StatusChip status={message.status} />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}
