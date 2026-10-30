"use client";

import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";

import { useServiceHealth } from "./api";

/** Explains a provider outage and what happens to messages meanwhile. */
export function OutageBanner() {
  const { data } = useServiceHealth();
  if (!data || data.status === "operational") return null;

  const affected = data.providers.filter((provider) => provider.status !== "operational");
  const names = affected.map((provider) => provider.display_name).join(" and ");

  return data.status === "down" ? (
    <Alert severity="error" sx={{ mx: 1, mt: 1, mb: 0 }}>
      <AlertTitle>{names} provider unavailable</AlertTitle>
      Messages can&apos;t be delivered right now. They are retried automatically for a while; any that still fail
      can be retried once the service is back.
    </Alert>
  ) : (
    <Alert severity="warning" sx={{ mx: 1, mt: 1, mb: 0 }}>
      <AlertTitle>{names} provider is having problems</AlertTitle>
      Some messages may be slow or fail. Failed attempts are retried automatically.
    </Alert>
  );
}
