"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { DrawerShell } from "@/components/DrawerShell";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { useToast } from "@/components/ToastProvider";
import { useCandidate } from "@/features/candidates/api";
import { errorMessage } from "@/lib/api/errors";
import type { Message } from "@/lib/api/types";
import { formatDate, formatDateTime, formatPhone, formatTime } from "@/lib/format";

import { useCandidateHistory, useRetryMessages } from "./api";
import { StatusChip } from "./StatusChip";

/** A candidate's communication history, newest first. Open while `candidateId` is set. */
export function HistoryDrawer({ candidateId, onClose }: { candidateId: string | null; onClose: () => void }) {
  const candidate = useCandidate(candidateId);
  const history = useCandidateHistory(candidateId);
  const retry = useRetryMessages();
  const toast = useToast();
  const retryingId = retry.isPending && "messageId" in retry.variables ? retry.variables.messageId : null;
  const retryMessage = (messageId: string) =>
    retry.mutate({ messageId }, { onError: (error) => toast(errorMessage(error), "error") });
  const messages = history.data?.pages.flatMap((page) => page.results) ?? [];

  let content;
  if (candidate.isError || (history.isError && !history.data)) {
    content = (
      <ErrorState
        error={candidate.error ?? history.error}
        onRetry={() => {
          void candidate.refetch();
          void history.refetch();
        }}
      />
    );
  } else if (!candidate.data || !history.data) {
    content = <HistorySkeleton />;
  } else {
    const { data } = candidate;
    content = (
      <>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Typography variant="caption" component="p" sx={{ color: "text.secondary" }}>
            Candidate ID: {data.code}
          </Typography>
          <Typography component="h3" sx={{ fontSize: 24, lineHeight: "28.8px", fontWeight: 700, color: "common.black" }}>
            {data.full_name}
          </Typography>
          <Typography sx={bodyText}>{formatPhone(data.phone)}</Typography>
          <Typography sx={bodyText}>{data.email}</Typography>
        </Box>
        {messages.length === 0 ? (
          <Box sx={{ mt: 6 }}>
            <EmptyState
              title="No communication history"
              description={"You have not communicated with this candidate yet.\nWhen you send them a message, it will appear here."}
            />
          </Box>
        ) : (
          <Box component="ol" sx={{ listStyle: "none", m: 0, mt: 4, p: 0 }}>
            {messages.map((message) => (
              <HistoryItem
                key={message.id}
                message={message}
                onRetry={() => retryMessage(message.id)}
                retrying={retryingId === message.id}
                retryDisabled={retry.isPending}
              />
            ))}
          </Box>
        )}
        {history.hasNextPage && (
          <Box sx={{ textAlign: "center", mt: 2 }}>
            <Button onClick={() => void history.fetchNextPage()} loading={history.isFetchingNextPage}>
              Load older messages
            </Button>
          </Box>
        )}
      </>
    );
  }

  return (
    <DrawerShell open={candidateId !== null} title="Communication history" onClose={onClose}>
      {content}
    </DrawerShell>
  );
}

function HistoryItem({
  message,
  onRetry,
  retrying,
  retryDisabled,
}: {
  message: Message;
  onRetry: () => void;
  retrying: boolean;
  retryDisabled: boolean;
}) {
  return (
    <Box
      component="li"
      sx={{
        py: 3,
        display: "flex",
        flexDirection: "column",
        gap: 1,
        borderTop: 1,
        borderColor: "dialog.border",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 4, height: 24 }}>
        <Typography variant="caption" sx={{ color: "text.secondary", display: "flex", gap: 1 }}>
          <span>{formatDate(message.created_at)}</span>
          <span aria-hidden>|</span>
          <span>{formatTime(message.created_at)}</span>
          {message.channel === "email" && (
            <>
              <span aria-hidden>|</span>
              <span>Email</span>
            </>
          )}
          {message.status === "scheduled" && message.scheduled_for && (
            <>
              <span aria-hidden>|</span>
              <span>Sends {formatDateTime(message.scheduled_for)}</span>
            </>
          )}
          {message.retry_of_id && (
            <>
              <span aria-hidden>|</span>
              <span>Retry</span>
            </>
          )}
        </Typography>
        <StatusChip status={message.status} />
      </Box>
      <Typography sx={[bodyText, { whiteSpace: "pre-wrap", overflowWrap: "anywhere" }]}>{message.body}</Typography>
      {message.status === "failed" && (message.failure_reason || message.can_retry) && (
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
          <Typography variant="body2" sx={{ color: "error.main" }}>
            {message.failure_reason}
          </Typography>
          {message.can_retry && (
            <Button size="small" onClick={onRetry} loading={retrying} disabled={retryDisabled} sx={{ flexShrink: 0 }}>
              Retry
            </Button>
          )}
        </Box>
      )}
    </Box>
  );
}

function HistorySkeleton() {
  return (
    <Stack spacing={2} aria-label="Loading history">
      <Skeleton width="40%" />
      <Skeleton width="55%" />
      {Array.from({ length: 3 }, (_, index) => (
        <Skeleton key={index} variant="rounded" height={72} />
      ))}
    </Stack>
  );
}

const bodyText = { fontSize: 16, lineHeight: "22px" } as const;
