"use client";

import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Divider from "@mui/material/Divider";
import Popover from "@mui/material/Popover";
import Typography from "@mui/material/Typography";
import { useState } from "react";

import type { HealthStatus } from "@/lib/api/types";

import { useServiceHealth } from "./api";

const LABELS: Record<HealthStatus, string> = {
  operational: "Operational",
  degraded: "Degraded",
  down: "Down",
};

const DOT_COLOR: Record<HealthStatus, string> = {
  operational: "success.main",
  degraded: "warning.main",
  down: "error.main",
};

/** Header pill showing the messaging service's health; opens per-provider status and counts. */
export function ServiceStatus() {
  const health = useServiceHealth();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const status = health.data?.status;

  return (
    <>
      <ButtonBase
        onClick={(event) => setAnchor(event.currentTarget)}
        aria-label={`Communication service: ${status ? LABELS[status] : "status unknown"}. Show details`}
        sx={{ display: "flex", alignItems: "center", gap: 1, px: 1.5, py: 0.5, borderRadius: 100, border: 1, borderColor: "divider" }}
      >
        <Dot color={status ? DOT_COLOR[status] : "text.disabled"} />
        <Typography variant="body2">{status ? LABELS[status] : "Status unknown"}</Typography>
      </ButtonBase>
      <Popover
        open={anchor !== null}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
      >
        <Box sx={{ width: 300, p: 2 }}>
          <Typography sx={{ fontWeight: 700, mb: 1.5 }}>Communication service</Typography>
          {health.data ? (
            health.data.providers.map((provider, index) => (
              <Box key={provider.name}>
                {index > 0 && <Divider sx={{ my: 1.5 }} />}
                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="body2">{provider.display_name}</Typography>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Dot color={DOT_COLOR[provider.status]} />
                    <Typography variant="body2">{LABELS[provider.status]}</Typography>
                  </Box>
                </Box>
                <Count label="Messages sent" value={provider.sent} />
                <Count label="Messages delivered" value={provider.delivered} />
                <Count label="Messages failed" value={provider.failed} />
              </Box>
            ))
          ) : (
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              {health.isError ? "Couldn't check the service. Retrying shortly." : "Checking…"}
            </Typography>
          )}
          {health.data && (
            <Typography variant="caption" component="p" sx={{ color: "text.secondary", mt: 1.5 }}>
              Counts cover the last {health.data.window_hours} hours.
            </Typography>
          )}
        </Box>
      </Popover>
    </>
  );
}

function Dot({ color }: { color: string }) {
  return <Box component="span" aria-hidden sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: color }} />;
}

function Count({ label, value }: { label: string; value: number }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "space-between" }}>
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontVariantNumeric: "tabular-nums" }}>
        {value}
      </Typography>
    </Box>
  );
}
