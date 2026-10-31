// Short names for the generated API types. Edit the backend serializers, then run
// `npm run gen:api`; never write response types by hand.
import type { components, operations } from "./schema";

type Schemas = components["schemas"];
type CandidateListQuery = NonNullable<operations["candidates_list"]["parameters"]["query"]>;

export type ErrorCode = Schemas["ErrorCodeEnum"];
export type ErrorResponse = Schemas["ErrorResponse"];

export type Candidate = Schemas["CandidateOutput"];
export type CandidateListItem = Schemas["CandidateListOutput"];
export type CandidatePage = Schemas["CandidatePage"];
export type CandidateCreateInput = Schemas["CandidateCreateInputRequest"];
/** A column to sort the candidate list by, prefixed with "-" for descending. */
export type CandidateSort = Exclude<CandidateListQuery["sort"], "" | undefined>;

export type Message = Schemas["MessageOutput"];
export type MessagePage = Schemas["MessagePage"];
export type MessageSendInput = Schemas["MessageSendInputRequest"];
export type MessageStatus = Schemas["MessageStatusEnum"];
export type Channel = Schemas["ChannelEnum"];
export type Batch = Schemas["BatchOutput"];
export type BatchMessage = Schemas["BatchMessage"];

export type MessageTemplate = Schemas["TemplateOutput"];
export type TemplateInput = Schemas["TemplateInputRequest"];

export type ServiceHealth = Schemas["ServiceHealth"];
export type HealthStatus = Schemas["HealthStatusEnum"];

// The SSE stream is not part of the OpenAPI schema, so its event is derived from the
// generated message type: `message.status` carries these fields of the changed message.
export type MessageStatusEvent = Pick<
  Message,
  "batch_id" | "candidate_id" | "status" | "status_changed_at" | "failure_code" | "failure_reason" | "is_retryable" | "can_retry"
> & { message_id: Message["id"] };
