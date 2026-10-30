"use client";

import dayjs from "dayjs";
import { usePathname, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

import type { StatusFilter } from "./api";

export const PAGE_SIZE_OPTIONS = [10, 25, 50] as const;
const DEFAULT_PAGE_SIZE = PAGE_SIZE_OPTIONS[0];

export type CandidatesUrlState = {
  search: string;
  page: number;
  pageSize: number;
  /** Candidate whose history drawer is open. */
  candidateId: string | null;
  /** Column filters. Dates are YYYY-MM-DD in the recruiter's time zone. */
  name: string;
  phone: string;
  code: string;
  status: StatusFilter[];
  from: string;
  to: string;
};

export type ColumnFilters = Pick<CandidatesUrlState, "name" | "phone" | "code" | "status" | "from" | "to">;

export const NO_FILTERS: ColumnFilters = { name: "", phone: "", code: "", status: [], from: "", to: "" };

const PARAM = {
  search: "q",
  page: "page",
  pageSize: "rows",
  candidateId: "candidate",
  name: "name",
  phone: "phone",
  code: "id",
  status: "status",
  from: "from",
  to: "to",
} as const;

const DEFAULTS: CandidatesUrlState = { search: "", page: 1, pageSize: DEFAULT_PAGE_SIZE, candidateId: null, ...NO_FILTERS };

/** The list endpoint's limits on each filter. */
export const FILTER_LIMITS = { name: 100, phone: 20, code: 6 } as const;
export const STATUS_OPTIONS: StatusFilter[] = ["scheduled", "queued", "sent", "delivered", "read", "failed", "none"];
const PHONE_FILTER = /^[\d\s()+-]*$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function textParam(value: string | null, maxLength: number, pattern?: RegExp): string {
  if (!value || value.length > maxLength || (pattern && !pattern.test(value))) return "";
  return value;
}

function dateParam(value: string | null): string {
  // dayjs rolls impossible dates such as 2026-13-45 over, so the date must round-trip.
  return value && ISO_DATE.test(value) && dayjs(value).format("YYYY-MM-DD") === value ? value : "";
}

export function hasFilters(filters: ColumnFilters): boolean {
  return (Object.keys(NO_FILTERS) as (keyof ColumnFilters)[]).some((key) => filters[key].length > 0);
}

function positiveInt(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

/** Reads the view from URL parameters, dropping values the API would reject. */
export function parseUrlState(searchParams: Pick<URLSearchParams, "get">): CandidatesUrlState {
  const pageSize = positiveInt(searchParams.get(PARAM.pageSize), DEFAULT_PAGE_SIZE);
  const statuses = searchParams.get(PARAM.status)?.split(",") ?? [];
  return {
    search: searchParams.get(PARAM.search) ?? "",
    page: positiveInt(searchParams.get(PARAM.page), 1),
    pageSize: (PAGE_SIZE_OPTIONS as readonly number[]).includes(pageSize) ? pageSize : DEFAULT_PAGE_SIZE,
    candidateId: searchParams.get(PARAM.candidateId),
    name: textParam(searchParams.get(PARAM.name), FILTER_LIMITS.name),
    phone: textParam(searchParams.get(PARAM.phone), FILTER_LIMITS.phone, PHONE_FILTER),
    code: textParam(searchParams.get(PARAM.code), FILTER_LIMITS.code),
    status: STATUS_OPTIONS.filter((status) => statuses.includes(status)),
    from: dateParam(searchParams.get(PARAM.from)),
    to: dateParam(searchParams.get(PARAM.to)),
  };
}

/**
 * Table and drawer state kept in the URL, so a refresh or a shared link restores the view and
 * the back button closes the history drawer. Writes use the History API, which Next keeps in
 * sync with useSearchParams without a server round trip.
 */
export function useCandidatesUrlState() {
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const state = useMemo(() => parseUrlState(searchParams), [searchParams]);

  const update = useCallback(
    (changes: Partial<CandidatesUrlState>, mode: "push" | "replace" = "replace") => {
      // The live URL, not the rendered state, so successive updates in one tick compose.
      const next = new URLSearchParams(window.location.search);
      for (const [key, value] of Object.entries(changes) as [keyof CandidatesUrlState, unknown][]) {
        if (value === undefined) continue;
        const serialized = Array.isArray(value) ? value.join(",") : value;
        if (serialized === null || serialized === "" || serialized === DEFAULTS[key]) {
          next.delete(PARAM[key]);
        } else {
          next.set(PARAM[key], String(serialized));
        }
      }
      const query = next.toString();
      const url = query ? `${pathname}?${query}` : pathname;
      if (mode === "push") {
        window.history.pushState(null, "", url);
      } else {
        window.history.replaceState(null, "", url);
      }
    },
    [pathname],
  );

  return [state, update] as const;
}
