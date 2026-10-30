"use client";

import Alert from "@mui/material/Alert";
import FormControlLabel from "@mui/material/FormControlLabel";
import Link from "@mui/material/Link";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";
import { type KeyboardEvent, useRef, useState } from "react";

import { DialogShell } from "@/components/DialogShell";
import { DrawerShell } from "@/components/DrawerShell";
import { useToast } from "@/components/ToastProvider";
import type { SelectedCandidate } from "@/features/candidates/CandidateTable";
import { useServiceHealth } from "@/features/health/api";
import { fillIn, hasPlaceholders, toTemplate } from "@/features/templates/placeholders";
import { TemplateToolbar } from "@/features/templates/TemplateToolbar";
import { errorMessage } from "@/lib/api/errors";
import type { Channel } from "@/lib/api/types";
import { formatDateTime, pluralize } from "@/lib/format";

import { useSendMessage } from "./api";
import { RecipientChips } from "./RecipientChips";
import { SendResults } from "./SendResults";

export const MESSAGE_MAX_LENGTH = 1000;
const SCHEDULE_MIN_LEAD_MINUTES = 1;
const SCHEDULE_MAX_AHEAD_DAYS = 30;
const LOCAL_INPUT_FORMAT = "YYYY-MM-DDTHH:mm";
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
  const [sent, setSent] = useState<{ batchId: string; total: number; scheduledFor: string | null } | null>(null);
  const [when, setWhen] = useState<"now" | "later">("now");
  const [channel, setChannel] = useState<Channel>("sms");
  const channels = useServiceHealth().data?.providers ?? [];
  const [scheduledLocal, setScheduledLocal] = useState("");
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  // Reused when a failed send is retried, so the server never sends it twice; cleared on edit.
  const idempotencyKey = useRef<string | null>(null);
  // On after applying a template with placeholders: the first recipient's details in the box
  // are sent as each recipient's own.
  const [personalised, setPersonalised] = useState(false);
  const batchId = sent?.batchId ?? null;

  const changeBody = (next: string) => {
    setBody(next);
    idempotencyKey.current = null;
  };

  const firstRecipient = recipients[0];

  const applyTemplate = (template: string) => {
    changeBody(firstRecipient ? fillIn(template, firstRecipient) : template);
    setPersonalised(hasPlaceholders(template));
  };
  const trimmed = body.trim();
  const tooLong = body.length > MESSAGE_MAX_LENGTH;
  const scheduleError = when === "later" ? scheduleProblem(scheduledLocal) : null;
  const canSend =
    trimmed !== "" && !tooLong && !scheduleError && recipients.length > 0 && !sendMessage.isPending;

  const finish = () => {
    // While the drawer is open the toast would cover its footer.
    if (sent) {
      toast(
        sent.scheduledFor
          ? `Message to ${pluralize(sent.total, "candidate")} scheduled for ${formatDateTime(sent.scheduledFor)}`
          : `Message sent to ${pluralize(sent.total, "candidate")}`,
      );
    }
    setBody("");
    setSent(null);
    setWhen("now");
    setScheduledLocal("");
    setChannel("sms");
    setPersonalised(false);
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
        body: personalised && firstRecipient ? toTemplate(trimmed, firstRecipient) : trimmed,
        channel,
        idempotency_key: idempotencyKey.current,
        scheduled_at: when === "later" ? dayjs(scheduledLocal).toISOString() : undefined,
      },
      {
        onSuccess: (batch) => {
          const scheduledFor = batch.messages.find((message) => message.scheduled_for)?.scheduled_for ?? null;
          setSent({ batchId: batch.id, total: batch.total, scheduledFor });
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
        {when === "later" ? "Schedule message" : "Send message"}
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
              <TemplateToolbar body={body} candidate={firstRecipient} onApply={applyTemplate} />
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
                onChange={(event) => changeBody(event.target.value)}
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
              {personalised && firstRecipient && recipients.length > 1 && (
                <Typography variant="caption" component="p" sx={{ color: "text.secondary", mt: 1 }}>
                  Written for {firstRecipient.full_name}. Each candidate gets the message with their own
                  name.{" "}
                  <Link component="button" type="button" variant="caption" onClick={() => setPersonalised(false)}>
                    Send exactly as written
                  </Link>
                </Typography>
              )}
            </Box>
            {channels.length > 1 && (
              <Box>
                <Typography component="p" sx={sectionLabel}>
                  Send as
                </Typography>
                <RadioGroup
                  row
                  value={channel}
                  onChange={(event) => {
                    setChannel(event.target.value === "email" ? "email" : "sms");
                    idempotencyKey.current = null;
                  }}
                >
                  {channels.map((provider) => (
                    <FormControlLabel
                      key={provider.name}
                      value={provider.channel}
                      control={<Radio />}
                      label={provider.display_name}
                    />
                  ))}
                </RadioGroup>
                <Typography variant="caption" component="p" sx={{ color: "text.secondary" }}>
                  {channel === "email"
                    ? "Sent to each candidate's email address."
                    : "Sent to each candidate's mobile number."}
                </Typography>
              </Box>
            )}
            <Box>
              <Typography component="p" sx={sectionLabel}>
                When
              </Typography>
              <RadioGroup
                row
                value={when}
                onChange={(event) => {
                  setWhen(event.target.value === "later" ? "later" : "now");
                  idempotencyKey.current = null;
                }}
              >
                <FormControlLabel value="now" control={<Radio />} label="Send now" />
                <FormControlLabel value="later" control={<Radio />} label="Schedule for later" />
              </RadioGroup>
              {when === "later" && (
                <TextField
                  type="datetime-local"
                  label="Send at"
                  size="small"
                  value={scheduledLocal}
                  onChange={(event) => {
                    setScheduledLocal(event.target.value);
                    idempotencyKey.current = null;
                  }}
                  error={Boolean(scheduledLocal) && Boolean(scheduleError)}
                  helperText={(scheduledLocal && scheduleError) || "Your local time"}
                  sx={{ mt: 1, width: 260 }}
                  slotProps={{
                    inputLabel: { shrink: true },
                    htmlInput: {
                      min: dayjs().add(SCHEDULE_MIN_LEAD_MINUTES, "minute").format(LOCAL_INPUT_FORMAT),
                      max: dayjs().add(SCHEDULE_MAX_AHEAD_DAYS, "day").format(LOCAL_INPUT_FORMAT),
                    },
                  }}
                />
              )}
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

/** Why the schedule time can't be used, or null. */
function scheduleProblem(local: string): string | null {
  const at = dayjs(local);
  if (!local || !at.isValid()) return "Pick a date and time.";
  if (at.isBefore(dayjs().add(SCHEDULE_MIN_LEAD_MINUTES, "minute"))) return "Pick a time at least a minute from now.";
  if (at.isAfter(dayjs().add(SCHEDULE_MAX_AHEAD_DAYS, "day"))) {
    return `Pick a time within the next ${SCHEDULE_MAX_AHEAD_DAYS} days.`;
  }
  return null;
}
