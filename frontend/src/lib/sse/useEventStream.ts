"use client";

import { useEffect, useRef, useState } from "react";

// EventSource retries on its own after a dropped connection (the server sets the delay).
// When the browser gives up entirely (readyState CLOSED), reopen after this long.
const REOPEN_DELAY_MS = 5000;

type Handlers = Record<string, (data: unknown) => void>;

/**
 * Subscribes to a Server-Sent Events stream and calls the handler for each named event.
 *
 * Returns whether the stream is currently connected, so callers can fall back to polling.
 * `onReconnect` runs when the connection comes back, to catch up on events missed meanwhile.
 */
export function useEventStream(url: string, handlers: Handlers, onReconnect?: () => void): boolean {
  const [connected, setConnected] = useState(false);
  const handlersRef = useRef(handlers);
  const onReconnectRef = useRef(onReconnect);

  useEffect(() => {
    handlersRef.current = handlers;
    onReconnectRef.current = onReconnect;
  });

  useEffect(() => {
    let source: EventSource | null = null;
    let reopenTimer: ReturnType<typeof setTimeout> | undefined;
    let hasConnectedBefore = false;
    let disposed = false;

    const open = () => {
      source = new EventSource(url);
      source.onopen = () => {
        setConnected(true);
        if (hasConnectedBefore) onReconnectRef.current?.();
        hasConnectedBefore = true;
      };
      source.onerror = () => {
        setConnected(false);
        if (source?.readyState === EventSource.CLOSED && !disposed) {
          source.close();
          reopenTimer = setTimeout(open, REOPEN_DELAY_MS);
        }
      };
      for (const eventType of Object.keys(handlersRef.current)) {
        source.addEventListener(eventType, (event) => {
          try {
            handlersRef.current[eventType]?.(JSON.parse((event as MessageEvent<string>).data));
          } catch {
            // A malformed event is skipped; the next refetch or event corrects the view.
          }
        });
      }
    };

    open();
    return () => {
      disposed = true;
      clearTimeout(reopenTimer);
      source?.close();
    };
  }, [url]);

  return connected;
}
