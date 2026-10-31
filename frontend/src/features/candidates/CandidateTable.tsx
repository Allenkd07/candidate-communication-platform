"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Skeleton from "@mui/material/Skeleton";
import type { SxProps, Theme } from "@mui/material/styles";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";
import Typography from "@mui/material/Typography";
import type { ComponentProps, ReactNode } from "react";

import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { StatusChip } from "@/features/communications/StatusChip";
import type { CandidateListItem, CandidatePage, CandidateSort } from "@/lib/api/types";
import { formatDate, formatPhone } from "@/lib/format";

import { ColumnFilter, DateRangeFilter, StatusFilterField, TextFilter } from "./ColumnFilter";
import {
  type ColumnFilters,
  FILTER_LIMITS,
  hasFilters,
  nextSort,
  PAGE_SIZE_OPTIONS,
  type SortColumn,
} from "./useCandidatesUrlState";

const SKELETON_ROWS = 10;
// Position of the empty and error states below the header row.
const OVERLAY_OFFSET = { pt: "108px", pl: "8px" };

export type SelectedCandidate = Pick<CandidateListItem, "id" | "full_name" | "code">;

type CandidateTableProps = {
  data: CandidatePage | undefined;
  isPending: boolean;
  isFetching: boolean;
  error: unknown;
  onRetry: () => void;
  search: string;
  filters: ColumnFilters;
  onFiltersChange: (changes: Partial<ColumnFilters>) => void;
  onClearFilters: () => void;
  sort: CandidateSort | "";
  onSortChange: (sort: CandidateSort | "") => void;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  selected: ReadonlyMap<string, SelectedCandidate>;
  onToggle: (candidate: SelectedCandidate) => void;
  onTogglePage: (candidates: SelectedCandidate[], select: boolean) => void;
  onOpenHistory: (candidateId: string) => void;
};

// Checkbox and name stay pinned while the other columns scroll, from tablet width up; on a
// phone the whole row scrolls. Pinned cells need an opaque background.
const pinned = (theme: Theme, left: number) => ({
  [theme.breakpoints.up("md")]: { position: "sticky" as const, left, zIndex: 1 },
  bgcolor: "background.paper",
  ".MuiTableRow-head > &": { bgcolor: theme.palette.table.header, zIndex: 3 },
  ".Mui-selected > &": { bgcolor: theme.palette.table.rowSelected },
});

const checkboxCell: SxProps<Theme> = (theme) => ({
  ...pinned(theme, 0),
  width: theme.size.checkboxColumnWidth,
  px: "3px",
  py: 0,
  "& .MuiCheckbox-root": { p: "8px 9px" },
});
const nameHeaderCell: SxProps<Theme> = (theme) => ({
  ...pinned(theme, theme.size.checkboxColumnWidth),
  width: theme.size.stickyNameColumnWidth - theme.size.checkboxColumnWidth,
});
const nameCell: SxProps<Theme> = (theme) => ({
  ...pinned(theme, theme.size.checkboxColumnWidth),
  p: "8px 8px 7px",
});
const dataColumn: SxProps<Theme> = (theme) => ({ width: theme.size.dataColumnWidth });

// Row lines continue below the last row to the bottom of the table.
const ruledBackground = (theme: Theme) => ({
  backgroundImage: `linear-gradient(to bottom, transparent ${theme.size.tableRowHeight - 1}px, ${theme.palette.table.rowBorder} ${theme.size.tableRowHeight - 1}px)`,
  backgroundSize: `100% ${theme.size.tableRowHeight}px`,
  backgroundPosition: `0 ${theme.size.tableHeaderHeight}px`,
  backgroundAttachment: "local",
});

export function CandidateTable(props: CandidateTableProps) {
  const { data, isPending, isFetching, error, onRetry, search, filters, onFiltersChange, sort, onSortChange } = props;
  const { page, pageSize, selected } = props;
  const filtered = hasFilters(filters);
  const rows = data?.results ?? [];
  const selectedOnPage = rows.filter((row) => selected.has(row.id)).length;

  let body: ReactNode = null;
  let overlay: ReactNode = null;
  if (error && !data) {
    overlay = <ErrorState error={error} onRetry={onRetry} />;
  } else if (isPending) {
    body = Array.from({ length: Math.min(pageSize, SKELETON_ROWS) }, (_, index) => <SkeletonRow key={index} />);
  } else if (rows.length === 0) {
    overlay = filtered ? (
      <EmptyState
        title="No candidates match these filters"
        description={search ? `Searching for "${search}". Try changing the search or the filters.` : "Try changing the filters."}
        action={<Button onClick={props.onClearFilters}>Clear filters</Button>}
      />
    ) : search ? (
      <EmptyState title={`No candidates match "${search}"`} description="Try a different name, number, email or ID." />
    ) : (
      <EmptyState title="No candidates added" description="When you add a candidate, they will appear here." />
    );
  } else {
    body = rows.map((row) => (
      <CandidateRow
        key={row.id}
        candidate={row}
        selected={selected.has(row.id)}
        onToggle={props.onToggle}
        onOpenHistory={props.onOpenHistory}
      />
    ));
  }
  const ruled = !overlay && !search && !filtered;

  return (
    <Paper
      elevation={0}
      sx={{
        mt: 1,
        mr: 1,
        mb: 1,
        p: 1,
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        gap: 1,
        overflow: "hidden",
        position: "relative",
      }}
    >
      {isFetching && !isPending && (
        <LinearProgress aria-label="Refreshing" sx={{ position: "absolute", top: 0, left: 0, right: 0, height: 2 }} />
      )}
      <TableContainer sx={[{ flex: overlay ? "none" : 1 }, ruled && ruledBackground]}>
        <Table stickyHeader sx={{ tableLayout: "fixed", width: "100%", minWidth: 1416 }} aria-label="Candidates">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" sx={checkboxCell}>
                <Checkbox
                  indeterminate={selectedOnPage > 0 && selectedOnPage < rows.length}
                  checked={rows.length > 0 && selectedOnPage === rows.length}
                  disabled={rows.length === 0}
                  onChange={(event) =>
                    props.onTogglePage(
                      rows.map(({ id, full_name, code }) => ({ id, full_name, code })),
                      event.target.checked,
                    )
                  }
                  slotProps={{ input: { "aria-label": "Select all candidates on this page" } }}
                />
              </TableCell>
              <HeaderCell
                sx={nameHeaderCell}
                label="Full name"
                column="name"
                sort={sort}
                onSortChange={onSortChange}
                active={filters.name !== ""}
              >
                {(close, focusRef) => (
                  <TextFilter
                    label="Name"
                    maxLength={FILTER_LIMITS.name}
                    value={filters.name}
                    onChange={(name) => onFiltersChange({ name })}
                    close={close}
                    focusRef={focusRef}
                  />
                )}
              </HeaderCell>
              <HeaderCell
                sx={dataColumn}
                label="Mobile number"
                column="phone"
                sort={sort}
                onSortChange={onSortChange}
                active={filters.phone !== ""}
              >
                {(close, focusRef) => (
                  <TextFilter
                    label="Number"
                    inputMode="numeric"
                    maxLength={FILTER_LIMITS.phone}
                    allowed={/[\d\s()+-]/}
                    value={filters.phone}
                    onChange={(phone) => onFiltersChange({ phone })}
                    close={close}
                    focusRef={focusRef}
                  />
                )}
              </HeaderCell>
              <HeaderCell
                sx={dataColumn}
                label="Last message"
                column="last_message"
                sort={sort}
                onSortChange={onSortChange}
                active={filters.from !== "" || filters.to !== ""}
              >
                {(close, focusRef) => (
                  <DateRangeFilter
                    value={{ from: filters.from, to: filters.to }}
                    onChange={onFiltersChange}
                    close={close}
                    focusRef={focusRef}
                  />
                )}
              </HeaderCell>
              <HeaderCell
                sx={dataColumn}
                label="Status"
                column="status"
                sort={sort}
                onSortChange={onSortChange}
                active={filters.status.length > 0}
              >
                {(close, focusRef) => (
                  <StatusFilterField
                    value={filters.status}
                    onChange={(status) => onFiltersChange({ status })}
                    close={close}
                    focusRef={focusRef}
                  />
                )}
              </HeaderCell>
              <HeaderCell
                sx={dataColumn}
                label="Candidate ID"
                column="code"
                sort={sort}
                onSortChange={onSortChange}
                active={filters.code !== ""}
              >
                {(close, focusRef) => (
                  <TextFilter
                    label="ID"
                    maxLength={FILTER_LIMITS.code}
                    value={filters.code}
                    onChange={(code) => onFiltersChange({ code })}
                    close={close}
                    focusRef={focusRef}
                  />
                )}
              </HeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>{body}</TableBody>
        </Table>
      </TableContainer>
      {overlay && (
        <Box sx={{ flex: 1, display: "flex", justifyContent: "center", ...OVERLAY_OFFSET, overflowY: "auto" }}>
          {overlay}
        </Box>
      )}
      {overlay === null && (
        <TablePagination
          component="div"
          count={data?.count ?? 0}
          page={data ? page - 1 : 0}
          rowsPerPage={pageSize}
          rowsPerPageOptions={[...PAGE_SIZE_OPTIONS]}
          onPageChange={(_, zeroBasedPage) => props.onPageChange(zeroBasedPage + 1)}
          onRowsPerPageChange={(event) => props.onPageSizeChange(Number(event.target.value))}
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} of ${count}`}
          showFirstButton
          showLastButton
          sx={{
            flexShrink: 0,
            "& .MuiTablePagination-spacer": { display: "none" },
            "& .MuiTablePagination-toolbar": { minHeight: 48, px: 2, flexWrap: "wrap" },
            "& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows": {
              m: 0,
              fontSize: 14,
              lineHeight: "19px",
            },
            "& .MuiTablePagination-input": { ml: 1, mr: 3, fontSize: 14 },
            "& .MuiTablePagination-select.MuiSelect-select": { pl: 0, pr: 3, textAlign: "left", textAlignLast: "left" },
            "& .MuiTablePagination-toolbar .MuiTablePaginationActions-root": {
              ml: 3,
              display: "flex",
              gap: 2,
              "& .MuiIconButton-root": { p: 0, width: 24, height: 24 },
            },
          }}
        />
      )}
    </Paper>
  );
}

function CandidateRow({
  candidate,
  selected,
  onToggle,
  onOpenHistory,
}: {
  candidate: CandidateListItem;
  selected: boolean;
  onToggle: (candidate: SelectedCandidate) => void;
  onOpenHistory: (candidateId: string) => void;
}) {
  const toggle = () => onToggle({ id: candidate.id, full_name: candidate.full_name, code: candidate.code });

  return (
    <TableRow hover selected={selected}>
      <TableCell padding="checkbox" sx={checkboxCell}>
        <Checkbox
          checked={selected}
          onChange={toggle}
          slotProps={{ input: { "aria-label": `Select ${candidate.full_name}` } }}
        />
      </TableCell>
      <TableCell sx={nameCell}>
        <Link
          component="button"
          type="button"
          underline="hover"
          onClick={() => onOpenHistory(candidate.id)}
          sx={{ display: "block", font: "inherit", fontWeight: 600, textAlign: "left" }}
        >
          {candidate.full_name}
        </Link>
      </TableCell>
      <TableCell>{formatPhone(candidate.phone)}</TableCell>
      <TableCell>
        {candidate.last_message_at ? formatDate(candidate.last_message_at) : <NotAvailable />}
      </TableCell>
      <TableCell>
        {candidate.last_message_status ? (
          <StatusChip
            status={candidate.last_message_status}
            failureReason={candidate.last_message_failure_reason}
          />
        ) : (
          <NotAvailable />
        )}
      </TableCell>
      <TableCell>{candidate.code}</TableCell>
    </TableRow>
  );
}

function NotAvailable() {
  return (
    <Typography component="span" sx={{ font: "inherit", color: "muted" }}>
      NA
    </Typography>
  );
}

function SkeletonRow() {
  return (
    <TableRow aria-hidden>
      <TableCell padding="checkbox" sx={checkboxCell}>
        <Skeleton variant="rounded" width={15} height={15} sx={{ mx: "auto" }} />
      </TableCell>
      {[160, 120, 90, 70, 70].map((width, index) => (
        <TableCell key={index} sx={index === 0 ? nameCell : dataColumn}>
          <Skeleton width={width} />
        </TableCell>
      ))}
    </TableRow>
  );
}

/** Sortable header label with its column filter at the far right. */
function HeaderCell({
  sx,
  label,
  column,
  sort,
  onSortChange,
  active,
  children,
}: {
  sx: SxProps<Theme>;
  label: string;
  column: SortColumn;
  sort: CandidateSort | "";
  onSortChange: (sort: CandidateSort | "") => void;
  active: boolean;
  children: ComponentProps<typeof ColumnFilter>["children"];
}) {
  const direction = sort === column ? "asc" : sort === `-${column}` ? "desc" : null;
  return (
    <TableCell
      sx={sx}
      aria-sort={direction === "asc" ? "ascending" : direction === "desc" ? "descending" : undefined}
    >
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
        <TableSortLabel
          active={direction !== null}
          direction={direction ?? "asc"}
          onClick={() => onSortChange(nextSort(column, sort))}
        >
          {label}
        </TableSortLabel>
        <ColumnFilter label={label} active={active}>
          {children}
        </ColumnFilter>
      </Box>
    </TableCell>
  );
}
