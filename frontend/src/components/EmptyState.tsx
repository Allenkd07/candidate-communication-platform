import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";

const ILLUSTRATION_BOX = 220;

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  /** Line breaks are kept. */
  description?: string;
  action?: ReactNode;
}) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1, textAlign: "center" }}>
      <Box
        sx={{ width: ILLUSTRATION_BOX, height: ILLUSTRATION_BOX, display: "grid", placeItems: "center" }}
        aria-hidden
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- a static SVG gains nothing from next/image */}
        <img src="/empty-state.svg" alt="" width={209} height={151} />
      </Box>
      <Typography sx={{ fontSize: 18, lineHeight: "24px", fontWeight: 700 }}>{title}</Typography>
      {description && (
        <Typography sx={{ fontSize: 16, lineHeight: "18px", whiteSpace: "pre-line" }}>{description}</Typography>
      )}
      {action && <Box sx={{ mt: 1 }}>{action}</Box>}
    </Box>
  );
}
