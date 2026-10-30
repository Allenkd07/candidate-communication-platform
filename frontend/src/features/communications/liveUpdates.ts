"use client";

import { type InfiniteData, type QueryClient, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { candidateKeys } from "@/features/candidates/api";
import type { Batch, MessagePage, MessageStatusEvent } from "@/lib/api/types";
import { useEventStream } from "@/lib/sse/useEventStream";

import { messageKeys } from "./api";

const EVENTS_URL = "/api/v1/events/";
const MESSAGE_STATUS_EVENT = "message.status";
// A send to many candidates produces a burst of events; refresh the table once per burst.
const LIST_REFRESH_DEBOUNCE_MS = 1000;

/**
 * Poll intervals. While the stream is down, views poll quickly instead. While it is up, a
 * send's results still poll slowly: events published before the results were cached (e.g.
 * between the send response and the first render) would otherwise be missed.
 */
export const POLL_MS = {
  batch: { live: 10_000, fallback: 3000 },
  candidates: { live: undefined, fallback: 15_000 },
} as const;

/**
 * Keeps cached messages current from the server's status events. Returns whether the stream
 * is connected, which picks the poll intervals in POLL_MS.
 */
export function useLiveMessageUpdates(): boolean {
  const queryClient = useQueryClient();
  const listRefresh = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => () => clearTimeout(listRefresh.current), []);

  return useEventStream(
    EVENTS_URL,
    {
      [MESSAGE_STATUS_EVENT]: (data) => {
        const event = data as MessageStatusEvent;
        patchBatch(queryClient, event);
        patchHistory(queryClient, event);
        // The table row shows the candidate's latest message, which only the server knows,
        // so the list is refetched rather than patched.
        clearTimeout(listRefresh.current);
        listRefresh.current = setTimeout(
          () => void queryClient.invalidateQueries({ queryKey: candidateKeys.lists() }),
          LIST_REFRESH_DEBOUNCE_MS,
        );
      },
    },
    // Events sent while disconnected are lost, so refetch everything on screen.
    () => void queryClient.invalidateQueries(),
  );
}

function patchBatch(queryClient: QueryClient, event: MessageStatusEvent) {
  queryClient.setQueryData<Batch>(messageKeys.batch(event.batch_id), (batch) => {
    if (!batch) return batch;
    const messages = batch.messages.map((message) =>
      message.id === event.message_id ? applyEvent(message, event) : message,
    );
    const counts = { scheduled: 0, queued: 0, sent: 0, delivered: 0, read: 0, failed: 0 };
    for (const message of messages) counts[message.status] += 1;
    return { ...batch, messages, counts };
  });
}

/**
 * A message missing from the cached history is new, so that history is refetched instead.
 * Patching would also mark the outdated history as fresh.
 */
function patchHistory(queryClient: QueryClient, event: MessageStatusEvent) {
  const key = messageKeys.history(event.candidate_id);
  const cached = queryClient.getQueryData<InfiniteData<MessagePage>>(key);
  if (!cached) return;
  if (!cached.pages.some((page) => page.results.some((message) => message.id === event.message_id))) {
    void queryClient.invalidateQueries({ queryKey: key });
    return;
  }
  queryClient.setQueryData<InfiniteData<MessagePage>>(key, (history) => {
    if (!history) return history;
    return {
      ...history,
      pages: history.pages.map((page) => ({
        ...page,
        results: page.results.map((message) =>
          message.id === event.message_id ? applyEvent(message, event) : message,
        ),
      })),
    };
  });
}

/** Events can arrive out of order; one older than the cached status is ignored. */
export function applyEvent<T extends { status_changed_at: string }>(message: T, event: MessageStatusEvent): T {
  if (Date.parse(event.status_changed_at) < Date.parse(message.status_changed_at)) return message;
  return { ...message, ...pickStatus(event) };
}

function pickStatus(event: MessageStatusEvent) {
  const { status, status_changed_at, failure_code, failure_reason, is_retryable } = event;
  return { status, status_changed_at, failure_code, failure_reason, is_retryable };
}
