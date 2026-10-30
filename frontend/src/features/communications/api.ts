import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { candidateKeys } from "@/features/candidates/api";
import { api, unwrap } from "@/lib/api/client";
import type { Batch, MessageSendInput, MessageStatus } from "@/lib/api/types";

const HISTORY_PAGE_SIZE = 20;

export const messageKeys = {
  batch: (id: string) => ["batches", id] as const,
  histories: () => ["history"] as const,
  history: (candidateId: string) => [...messageKeys.histories(), candidateId] as const,
};

// Statuses that can still change.
const IN_FLIGHT: ReadonlySet<MessageStatus> = new Set(["scheduled", "queued", "sent"]);

export function batchInFlight(batch: Batch | undefined): boolean {
  return batch === undefined || batch.messages.some((message) => IN_FLIGHT.has(message.status));
}

export function useSendMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: MessageSendInput) => unwrap(api.POST("/api/v1/messages/", { body })),
    onSuccess: (batch) => {
      queryClient.setQueryData(messageKeys.batch(batch.id), batch);
      void queryClient.invalidateQueries({ queryKey: candidateKeys.lists() });
      void queryClient.invalidateQueries({ queryKey: messageKeys.histories() });
    },
  });
}

/** Sends failed messages again: one message, or every retryable one in a send. */
export function useRetryMessages() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (target: { messageId: string } | { batchId: string }) =>
      unwrap(
        "messageId" in target
          ? api.POST("/api/v1/messages/{message_id}/retry/", { params: { path: { message_id: target.messageId } } })
          : api.POST("/api/v1/batches/{batch_id}/retry-failed/", { params: { path: { batch_id: target.batchId } } }),
      ),
    onSuccess: (batch) => {
      queryClient.setQueryData(messageKeys.batch(batch.id), batch);
      void queryClient.invalidateQueries({ queryKey: candidateKeys.lists() });
      void queryClient.invalidateQueries({ queryKey: messageKeys.histories() });
    },
  });
}

/** A send's live results. `pollMs` is the fallback for when live updates are unavailable. */
export function useBatch(id: string | null, options: { pollMs?: number } = {}) {
  return useQuery({
    queryKey: messageKeys.batch(id ?? ""),
    queryFn: ({ signal }) =>
      unwrap(api.GET("/api/v1/batches/{batch_id}/", { params: { path: { batch_id: id! } }, signal })),
    enabled: id !== null,
    refetchInterval: (query) =>
      options.pollMs && batchInFlight(query.state.data) ? options.pollMs : false,
  });
}

/** A candidate's messages, newest first, loaded a page at a time. */
export function useCandidateHistory(candidateId: string | null) {
  return useInfiniteQuery({
    queryKey: messageKeys.history(candidateId ?? ""),
    queryFn: ({ pageParam, signal }) =>
      unwrap(
        api.GET("/api/v1/candidates/{candidate_id}/messages/", {
          params: {
            path: { candidate_id: candidateId! },
            query: { page: pageParam, page_size: HISTORY_PAGE_SIZE },
          },
          signal,
        }),
      ),
    initialPageParam: 1,
    getNextPageParam: (lastPage, _pages, lastPageParam) => (lastPage.next ? lastPageParam + 1 : undefined),
    enabled: candidateId !== null,
  });
}
