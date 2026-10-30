"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { type KeyboardEvent, useRef, useState } from "react";

import { DialogShell } from "@/components/DialogShell";
import { DrawerShell } from "@/components/DrawerShell";
import { useToast } from "@/components/ToastProvider";
import type { SelectedCandidate } from "@/features/candidates/CandidateTable";
import { errorMessage } from "@/lib/api/errors";
import { pluralize } from "@/lib/format";

import { useSendMessage } from "./api";
import { RecipientChips } from "./RecipientChips";
import { SendResults } from "./SendResults";

export const MESSAGE_MAX_LENGTH = 1000;
// Seven 24px lines plus padding make a 200px box.
const MESSAGE_MIN_ROWS = 7;

type SendMessageDrawerProps = {
  open: boolean;
  recipients: SelectedCandidate[];
  onClose: () => void;
  /** Called once the send is accepted, e.g. to clear the table selection. */
  onSent: () => void;
  /** Poll interval for live results when the live-update stream is down. */
  pollMs?: number;
};

export function SendMessageDrawer({ open, recipients, onClose, onSent, pollMs }: SendMessageDrawerProps) {
  const toast = useToast();
  const sendMessage = useSendMessage();
  const [body, setBody] = useState("");
  const [sent, setSent] = useState<{ batchId: string; total: number } | null>(null);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  // Reused when a failed send is retried, so the server never sends it twice; cleared on edit.
  const idempotencyKey = useRef<string | null>(null);
  const batchId = sent?.batchId ?? null;

  const trimmed = body.trim();
  const tooLong = body.length > MESSAGE_MAX_LENGTH;
  const canSend = trimmed !== "" && !tooLong && recipients.length > 0 && !sendMessage.isPending;

  const finish = () => {
    // While the drawer is open the toast would cover its footer.
    if (sent) {
      toast(`Message sent to ${pluralize(sent.total, "candidate")}`);
    }
    setBody("");
    setSent(null);
    setConfirmDiscard(false);
    idempotencyKey.current = null;
    sendMessage.reset();
    onClose();
  };

  const requestClose = () => {
    if (sendMessage.isPending) return;
    if (!batchId && trimmed !== "") {
      setConfirmDiscard(true);
      return;
    }
    finish();
  };

  const send = () => {
    if (!canSend) return;
    idempotencyKey.current ??= crypto.randomUUID();
    sendMessage.mutate(
      {
        candidate_ids: recipients.map(({ id }) => id),
        body: trimmed,
        channel: "sms",
        idempotency_key: idempotencyKey.current,
      },
      {
        onSuccess: (batch) => {
          setSent({ batchId: batch.id, total: batch.total });
          onSent();
        },
      },
    );
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      send();
    }
  };

  const footer = batchId ? (
    <Button variant="contained" onClick={finish}>
      Done
    </Button>
  ) : (
    <>
      <Button variant="outlined" onClick={requestClose} disabled={sendMessage.isPending}>
        Cancel
      </Button>
      <Button variant="contained" onClick={send} disabled={!canSend} loading={sendMessage.isPending}>
        Send message
      </Button>
    </>
  );

  return (
    <>
      <DrawerShell open={open} title="Send Message" onClose={requestClose} footer={footer}>
        {batchId ? (
          <SendResults batchId={batchId} pollMs={pollMs} />
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              <Typography sx={sectionLabel}>{pluralize(recipients.length, "Recipient")}</Typography>
              <RecipientChips names={recipients.map(({ full_name }) => full_name)} />
            </Box>
            <Box>
              <Typography component="label" htmlFor="message-body" sx={[sectionLabel, { display: "block" }]}>
                Message
                <Box component="span" sx={{ color: "error.main", ml: 0.5 }} aria-hidden>
                  *
                </Box>
              </Typography>
              <Typography sx={{ mt: "2px", mb: 1, fontSize: 12, lineHeight: "19.9px", letterSpacing: 0.4, color: "text.secondary" }}>
                Type, or paste the message you want to send.
              </Typography>
              {sendMessage.isError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {errorMessage(sendMessage.error)}
                </Alert>
              )}
              <TextField
                id="message-body"
                multiline
                minRows={MESSAGE_MIN_ROWS}
                fullWidth
                required
                placeholder="Type or paste here..."
                value={body}
                onChange={(event) => {
                  setBody(event.target.value);
                  idempotencyKey.current = null;
                }}
                onKeyDown={onKeyDown}
                error={tooLong}
                helperText={
                  <Box component="span" sx={{ display: "flex", justifyContent: "space-between" }}>
                    <span>{tooLong ? `Keep the message under ${MESSAGE_MAX_LENGTH} characters.` : "Ctrl + Enter to send"}</span>
                    <span>
                      {body.length}/{MESSAGE_MAX_LENGTH}
                    </span>
                  </Box>
                }
                slotProps={{ htmlInput: { style: { resize: "vertical" } } }}
                sx={{ "& textarea::placeholder": { color: "dialog.border" } }}
              />
            </Box>
          </Box>
        )}
      </DrawerShell>
      <DialogShell
        open={confirmDiscard}
        title="Discard message?"
        onClose={() => setConfirmDiscard(false)}
        actions={
          <>
            <Button variant="outlined" onClick={() => setConfirmDiscard(false)}>
              Keep editing
            </Button>
            <Button variant="contained" color="error" onClick={finish}>
              Discard
            </Button>
          </>
        }
      >
        <Typography sx={{ mt: 2 }}>Your message hasn&apos;t been sent and will be lost.</Typography>
      </DialogShell>
    </>
  );
}

const sectionLabel = { fontSize: 16, lineHeight: "22px" } as const;
