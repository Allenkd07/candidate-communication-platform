"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import { useLayoutEffect, useRef, useState } from "react";

const MAX_LINES = 2;
const GAP = 1;

const chipSx = {
  height: 32,
  bgcolor: "dialog.chip",
  fontSize: 13,
  lineHeight: "18px",
  letterSpacing: 0.16,
  "& .MuiChip-label": { px: 1.25 },
} as const;

/**
 * Recipient names as chips that wrap to at most two lines, then a "+ n" link that expands
 * the full list.
 */
export function RecipientChips({ names }: { names: string[] }) {
  const measureRef = useRef<HTMLDivElement>(null);
  const [visibleCount, setVisibleCount] = useState(names.length);
  const [expanded, setExpanded] = useState(false);

  useLayoutEffect(() => {
    const measurer = measureRef.current;
    if (!measurer || expanded) return;

    // An invisible copy lays out every chip at the real width; count how many fit on the
    // first two lines, leaving room on the last line for "+ n".
    const measure = () => {
      const chips = Array.from(measurer.children) as HTMLElement[];
      const lineTops = [...new Set(chips.map((chip) => chip.offsetTop))].sort((a, b) => a - b);
      if (lineTops.length <= MAX_LINES) {
        setVisibleCount(chips.length);
        return;
      }
      const lastLineTop = lineTops[MAX_LINES - 1]!;
      const fitting = chips.filter((chip) => chip.offsetTop <= lastLineTop).length;
      setVisibleCount(Math.max(1, fitting - 1));
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(measurer);
    return () => observer.disconnect();
  }, [names, expanded]);

  const shown = expanded ? names : names.slice(0, visibleCount);
  const hidden = names.length - shown.length;

  return (
    <Box sx={{ position: "relative" }}>
      <Box
        ref={measureRef}
        aria-hidden
        sx={{
          position: "absolute",
          inset: 0,
          overflow: "hidden",
          visibility: "hidden",
          display: "flex",
          flexWrap: "wrap",
          alignContent: "flex-start",
          gap: GAP,
        }}
      >
        {names.map((name, index) => (
          <Chip key={index} label={name} sx={chipSx} />
        ))}
      </Box>
      <Box component="ul" sx={{ display: "flex", flexWrap: "wrap", gap: GAP, m: 0, p: 0, listStyle: "none" }}>
        {shown.map((name, index) => (
          <li key={index}>
            <Chip label={name} sx={chipSx} />
          </li>
        ))}
        {hidden > 0 && (
          <Box component="li" sx={{ display: "flex", alignItems: "center" }}>
            <Link
              component="button"
              type="button"
              underline="hover"
              color="textPrimary"
              onClick={() => setExpanded(true)}
              aria-label={`Show ${hidden} more recipients`}
              sx={{ fontSize: 13, lineHeight: "18px", letterSpacing: 0.16 }}
            >
              + {hidden}
            </Link>
          </Box>
        )}
      </Box>
    </Box>
  );
}
