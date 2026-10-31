import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";

import { api, unwrap } from "@/lib/api/client";
import type { CandidateCreateInput, CandidateSort, MessageStatus } from "@/lib/api/types";

import type { ColumnFilters } from "./useCandidatesUrlState";

/** A message status, or "none" for candidates never messaged. */
export type StatusFilter = MessageStatus | "none";

export type CandidateListParams = {
  search: string;
  page: number;
  pageSize: number;
  filters: ColumnFilters;
  sort: CandidateSort | "";
};

export const candidateKeys = {
  all: ["candidates"] as const,
  lists: () => [...candidateKeys.all, "list"] as const,
  list: (params: CandidateListParams) => [...candidateKeys.lists(), params] as const,
  detail: (id: string) => [...candidateKeys.all, "detail", id] as const,
};

export function useCandidates(params: CandidateListParams, options: { pollMs?: number } = {}) {
  return useQuery({
    queryKey: candidateKeys.list(params),
    queryFn: ({ signal }) =>
      unwrap(
        api.GET("/api/v1/candidates/", {
          params: {
            query: {
              search: params.search || undefined,
              page: params.page,
              page_size: params.pageSize,
              ...filterQuery(params.filters),
              sort: params.sort || undefined,
            },
          },
          signal,
        }),
      ),
    placeholderData: keepPreviousData,
    refetchInterval: options.pollMs ?? false,
  });
}

export function useCandidate(id: string | null) {
  return useQuery({
    queryKey: candidateKeys.detail(id ?? ""),
    queryFn: ({ signal }) =>
      unwrap(api.GET("/api/v1/candidates/{candidate_id}/", { params: { path: { candidate_id: id! } }, signal })),
    enabled: id !== null,
  });
}

export function useCreateCandidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CandidateCreateInput) => unwrap(api.POST("/api/v1/candidates/", { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: candidateKeys.lists() }),
  });
}

export function useDeleteCandidates() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (candidateIds: string[]) =>
      unwrap(api.POST("/api/v1/candidates/bulk-delete/", { body: { candidate_ids: candidateIds } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: candidateKeys.all }),
  });
}

/** The date range covers whole days in the recruiter's time zone, "to" included. */
function filterQuery({ name, phone, code, status, from, to }: ColumnFilters) {
  return {
    name: name || undefined,
    phone: phone || undefined,
    code: code || undefined,
    status: status.length > 0 ? status : undefined,
    last_message_after: from ? dayjs(from).startOf("day").toISOString() : undefined,
    last_message_before: to ? dayjs(to).add(1, "day").startOf("day").toISOString() : undefined,
  };
}
