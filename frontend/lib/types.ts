export type Person = {
  id: string;
  display_name: string;
  notes: string;
  relationship_profile?: {
    id: string;
    person_id: string;
    status: string;
    notes: string;
  } | null;
};

export type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
};

export type Conversation = {
  id: string;
  title: string;
  person_id: string | null;
  created_at: string;
  updated_at: string;
  messages?: Message[];
};

export type Memory = {
  id: string;
  person_id: string | null;
  scope: "user" | "object" | "relationship" | "event" | "hypothesis";
  key: string;
  value: string;
  confidence: "high" | "medium" | "low" | null;
  source: string | null;
  occurred_at: string | null;
  created_at: string;
  updated_at: string;
};

