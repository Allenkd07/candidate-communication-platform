"use client";

import CheckIcon from "@mui/icons-material/Check";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlineOutlined";
import EventIcon from "@mui/icons-material/Event";
import ScheduleIcon from "@mui/icons-material/Schedule";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import type { ReactElement } from "react";

import type { MessageStatus } from "@/lib/api/types";

export const STATUS_LABELS: Record<MessageStatus, string> = {
  scheduled: "Scheduled",
  queued: "Queued",
  sent: "Sent",
  delivered: "Delivered",
  read: "Read",
  failed: "Failed",
};

// "Sent" has no icon in the design; the statuses we added get one in the same style.
const ICONS: Partial<Record<MessageStatus, ReactElement>> = {
  scheduled: <EventIcon />,
  queued: <ScheduleIcon />,
  delivered: <DoneAllIcon />,
  read: <CheckIcon />,
  failed: <ErrorOutlineIcon />,
};

export function StatusChip({
  status,
  failureReason,
}: {
  status: MessageStatus;
  /** Shown on hover for a failed message. */
  failureReason?: string | null;
}) {
  const icon = ICONS[status];
  const chip = (
    <Chip
      size="small"
      label={STATUS_LABELS[status]}
      {...(icon ? { icon } : {})}
      sx={(theme) => {
        const colors = theme.palette.status[status];
        return {
          height: 24,
          verticalAlign: "top",
          mt: "1px",
          px: 0.75,
          borderRadius: 100,
          bgcolor: colors.bg,
          color: colors.fg,
          fontSize: 13,
          lineHeight: "18px",
          letterSpacing: 0.16,
          "& .MuiChip-icon": { color: colors.fg, fontSize: 16, m: 0 },
          "& .MuiChip-label": { px: 0.75 },
        };
      }}
    />
  );

  if (status === "failed" && failureReason) {
    return (
      <Tooltip title={failureReason} arrow>
        {/* Tooltip needs a focusable child to also work from the keyboard. */}
        <span tabIndex={0}>{chip}</span>
      </Tooltip>
    );
  }
  return chip;
}
