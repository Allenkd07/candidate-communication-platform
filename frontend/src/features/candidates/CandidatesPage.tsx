"use client";

import Box from "@mui/material/Box";
import { useEffect, useRef, useState } from "react";

import { AppHeader } from "@/components/AppHeader";
import { useToast } from "@/components/ToastProvider";
import { HistoryDrawer } from "@/features/communications/HistoryDrawer";
import { POLL_MS, useLiveMessageUpdates } from "@/features/communications/liveUpdates";
import { SendMessageDrawer } from "@/features/communications/SendMessageDrawer";
import { OutageBanner } from "@/features/health/OutageBanner";
import { ServiceStatus } from "@/features/health/ServiceStatus";
import { ApiError } from "@/lib/api/errors";

import { AddCandidateDialog } from "./AddCandidateDialog";
import { useCandidates } from "./api";
import { CandidateTable, type SelectedCandidate } from "./CandidateTable";
import { DeleteCandidatesDialog } from "./DeleteCandidatesDialog";
import { NO_FILTERS, useCandidatesUrlState } from "./useCandidatesUrlState";

type OpenPanel = "add" | "delete" | "send" | null;

// The API accepts at most this many candidates in one send or bulk delete.
const MAX_SELECTION = 500;

export function CandidatesPage() {
  const toast = useToast();
  const [url, setUrl] = useCandidatesUrlState();
  const live = useLiveMessageUpdates();
  const candidates = useCandidates(
    {
      search: url.search,
      page: url.page,
      pageSize: url.pageSize,
      filters: { name: url.name, phone: url.phone, code: url.code, status: url.status, from: url.from, to: url.to },
    },
    { pollMs: live ? POLL_MS.candidates.live : POLL_MS.candidates.fallback },
  );

  // Kept across pages and searches, so one send can include candidates from several pages.
  const [selected, setSelected] = useState<ReadonlyMap<string, SelectedCandidate>>(new Map());
  const [panel, setPanel] = useState<OpenPanel>(null);
  // Snapshot taken on open, so the panel's text stays fixed while it animates closed.
  const [targets, setTargets] = useState<SelectedCandidate[]>([]);

  // A page past the end returns 404: step back towards the last known page.
  const { data, error } = candidates;
  useEffect(() => {
    if (!(error instanceof ApiError) || error.code !== "not_found" || url.page <= 1) return;
    const lastKnown = data ? Math.max(1, Math.ceil(data.count / url.pageSize)) : 1;
    setUrl({ page: Math.min(url.page - 1, lastKnown) });
  }, [error, data, url.page, url.pageSize, setUrl]);

  // Closing history goes back when opening it added a browser history entry.
  const historyPushed = useRef(false);
  useEffect(() => {
    if (url.candidateId === null) historyPushed.current = false;
  }, [url.candidateId]);

  const openHistory = (candidateId: string) => {
    historyPushed.current = true;
    setUrl({ candidateId }, "push");
  };
  const closeHistory = () => {
    if (historyPushed.current) window.history.back();
    else setUrl({ candidateId: null });
  };

  const openWithSelection = (next: "delete" | "send") => {
    if (selected.size > MAX_SELECTION) {
      const action = next === "send" ? "message" : "delete";
      toast(`You can ${action} up to ${MAX_SELECTION} candidates at a time. ${selected.size} are selected.`, "error");
      return;
    }
    setTargets([...selected.values()]);
    setPanel(next);
  };

  const toggle = (candidate: SelectedCandidate) =>
    setSelected((current) => {
      const next = new Map(current);
      if (next.has(candidate.id)) next.delete(candidate.id);
      else next.set(candidate.id, candidate);
      return next;
    });

  const togglePage = (pageCandidates: SelectedCandidate[], select: boolean) =>
    setSelected((current) => {
      const next = new Map(current);
      for (const candidate of pageCandidates) {
        if (select) next.set(candidate.id, candidate);
        else next.delete(candidate.id);
      }
      return next;
    });

  const clearSelection = () => setSelected(new Map());

  return (
    <Box sx={{ height: "100dvh", display: "flex", flexDirection: "column", bgcolor: "background.default" }}>
      <AppHeader
        status={<ServiceStatus />}
        selectedCount={selected.size}
        search={url.search}
        onSearchChange={(search) => setUrl({ search, page: 1 })}
        onAdd={() => setPanel("add")}
        onDelete={() => openWithSelection("delete")}
        onSend={() => openWithSelection("send")}
      />
      <OutageBanner />
      <Box component="main" sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        <CandidateTable
          data={candidates.data}
          isPending={candidates.isPending}
          isFetching={candidates.isFetching}
          error={candidates.error}
          onRetry={() => void candidates.refetch()}
          search={url.search}
          filters={url}
          onFiltersChange={(changes) => setUrl({ ...changes, page: 1 })}
          onClearFilters={() => setUrl({ ...NO_FILTERS, page: 1 })}
          page={url.page}
          pageSize={url.pageSize}
          onPageChange={(page) => setUrl({ page })}
          onPageSizeChange={(pageSize) => setUrl({ pageSize, page: 1 })}
          selected={selected}
          onToggle={toggle}
          onTogglePage={togglePage}
          onOpenHistory={openHistory}
        />
      </Box>

      <AddCandidateDialog
        open={panel === "add"}
        onClose={() => setPanel(null)}
        onAdded={() => setUrl({ page: 1 })}
      />
      <DeleteCandidatesDialog
        open={panel === "delete"}
        candidates={targets}
        onClose={() => setPanel(null)}
        onDeleted={clearSelection}
      />
      <SendMessageDrawer
        open={panel === "send"}
        recipients={targets}
        onClose={() => setPanel(null)}
        onSent={clearSelection}
        pollMs={live ? POLL_MS.batch.live : POLL_MS.batch.fallback}
      />
      <HistoryDrawer candidateId={url.candidateId} onClose={closeHistory} />
    </Box>
  );
}
