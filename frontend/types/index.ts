export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

export type AvailabilityStatus =
  | "available"
  | "sold_out"
  | "not_open"
  | "unknown"
  | "unavailable"
  | "cancelled";

export type TicketCategory = "video_call" | "meet_greet" | "two_shot";

export interface MemberOut {
  id: number;
  external_id: string;
  name: string;
  nickname: string | null;
  team_code: string | null;
  generation_code: string | null;
  image_url: string | null;
  is_active: boolean;
  source: string;
  updated_at: string | null;
  is_favorite: boolean;
}

export interface MemberDetailOut extends MemberOut {
  total_sessions: number;
  sessions_available: number;
  tickets_remaining: number | null;
}

export interface EventOut {
  id: number;
  external_id: string;
  name: string;
  entry_type: string;
  category: string;
  category_code: string | null;
  starts_at: string | null;
  ends_at: string | null;
  sale_valid_from: string | null;
  sale_valid_to: string | null;
  total_quota: number | null;
  is_active: boolean;
  source: string;
  source_url: string | null;
  sessions: SessionOut[];
}

export interface SessionOut {
  id: number;
  session_label: string | null;
  session_number: number | null;
  track_number: number | null;
  ticket_category: string;
  member_id: number | null;
  member_name: string | null;
  starts_at: string | null;
  ends_at: string | null;
  total_quota: number | null;
}

export interface AvailabilityRow {
  session_id: number;
  event_id: number;
  event_external_id: string;
  event_name: string;
  entry_type: string;
  ticket_category: string;
  session_label: string | null;
  session_number: number | null;
  starts_at: string | null;
  member_id: number | null;
  member_name: string | null;
  status: AvailabilityStatus;
  tickets_remaining: number | null;
  total_quota: number | null;
  source: string;
  source_url: string | null;
  observed_at: string | null;
  source_updated_at: string | null;
}

export interface HistoryPoint {
  observed_at: string;
  status: string;
  tickets_remaining: number | null;
  sold_count: number | null;
  source: string;
  session_id: number;
  member_name: string | null;
  event_name: string;
}

export interface ChangeOut {
  session_id: number;
  event_name: string;
  member_name: string | null;
  ticket_category: string;
  field: string;
  previous: string | null;
  current: string | null;
  observed_at: string;
  source: string;
}

export interface SourceStatusOut {
  name: string;
  configured: boolean;
  available: boolean;
  supported_features: string[];
  message: string | null;
  base_url: string | null;
  docs_url: string | null;
  last_checked_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
}

export interface DashboardStats {
  total_members: number;
  active_members: number;
  total_events: number;
  active_events: number;
  total_sessions: number;
  available_sessions: number;
  sold_out_sessions: number;
  not_open_sessions: number;
  unknown_sessions: number;
  unavailable_sessions: number;
  sessions_with_declining_stock: number;
  data_available: boolean;
  last_observed_at: string | null;
  last_check_at: string | null;
  api_connected: boolean;
  notes: string[];
}

export interface DashboardOut {
  stats: DashboardStats;
  recent_changes: ChangeOut[];
  availability_by_category: Record<string, number>;
  sources: SourceStatusOut[];
}

export interface TokenOut {
  access_token: string;
  token_type: string;
}

export interface MonitorRefreshResult {
  started: boolean;
  message: string;
  members_synced: number;
  events_synced: number;
  sessions_synced: number;
  changes_detected: number;
  notifications_sent: number;
  errors: string[];
}

export interface MonitorStatus {
  running: boolean;
  last_run_at: string | null;
  last_success_at: string | null;
  consecutive_failures: number;
  last_error: string | null;
}

export interface NotificationSubscriptionOut {
  id: number;
  telegram_chat_id: string | null;
  event_type: string;
  member_id: number | null;
  enabled: boolean;
  created_at: string;
}

export interface NotificationLogOut {
  id: number;
  subscription_id: number | null;
  event_key: string;
  message: string;
  delivery_status: string;
  attempt_count: number;
  error_message: string | null;
  attempted_at: string;
  delivered_at: string | null;
}

export interface NotificationsOut {
  telegram_configured: boolean;
  subscriptions: NotificationSubscriptionOut[];
  logs: NotificationLogOut[];
}