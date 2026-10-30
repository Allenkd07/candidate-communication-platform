import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { TemplateInput } from "@/lib/api/types";

export const templateKeys = { all: ["templates"] as const };

export function useTemplates() {
  return useQuery({
    queryKey: templateKeys.all,
    queryFn: ({ signal }) => unwrap(api.GET("/api/v1/templates/", { signal })),
  });
}

/** Creates a template, or replaces one when `templateId` is given. */
export function useSaveTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ templateId, ...body }: TemplateInput & { templateId?: string }) =>
      unwrap(
        templateId
          ? api.PUT("/api/v1/templates/{template_id}/", { params: { path: { template_id: templateId } }, body })
          : api.POST("/api/v1/templates/", { body }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: templateKeys.all }),
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) =>
      unwrap(api.DELETE("/api/v1/templates/{template_id}/", { params: { path: { template_id: templateId } } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: templateKeys.all }),
  });
}
