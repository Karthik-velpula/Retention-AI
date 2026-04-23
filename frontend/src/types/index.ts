export type UserRole = "admin" | "faculty";
export type RiskLevel = "Safe" | "Low" | "Medium" | "High";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  name: string;
  last_login_at?: string | null;
}

export interface GridChallengeResponse {
  challenge_token: string;
  positions: string[];
}

export interface SecurityGridPreviewResponse {
  username: string;
  grid: Record<string, string>;
}

export interface SecurityGridResetConfirmResponse {
  detail: string;
  download_token: string;
}

export interface AssistantQueryResponse {
  answer: string;
}

export interface StudentListItem {
  id: number;
  registration_number: string;
  name: string;
  email: string;
  student_mobile: string;
  parent_mobile: string;
  counselor_name?: string | null;
  codechef_username: string;
  codechef_contests_participated: number;
  codechef_problems_solved: number;
  codechef_participation_status: string;
  codechef_last_synced_at?: string | null;
  section: string;
  gender: string;
  age?: number | null;
  gpa: number;
  attendance: number;
  lms_activity_percentage: number;
  fees_paid_status: "Paid" | "Not Paid" | string;
  marks: number;
  pre_t1_marks: number;
  t1_marks: number;
  t2_marks: number;
  t3_marks: number;
  t4_marks: number;
  t5_marks: number;
  department: string;
  year: number;
  latest_risk_level?: RiskLevel | null;
  latest_risk_score?: number | null;
}

export interface StudentDetail extends StudentListItem {
  career_interest: string;
  skills: string;
  subject_attendance: {
    subject_name: string;
    attendance_percentage: number;
    pre_t1_marks: number;
    t1_marks: number;
    t2_marks: number;
    t3_marks: number;
    t4_marks: number;
    t5_marks: number;
    t5_assignment_1: number;
    t5_assignment_2: number;
    t5_assignment_3: number;
    t5_assignment_4: number;
    total_marks: number;
  }[];
  lms_activity: {
    weekly_logins: number;
    avg_time_spent: number;
    assignment_submission_rate: number;
    missed_assignments: number;
  };
  financial: {
    fee_due: number;
    payment_delay_days: number;
    scholarship_amount: number;
  };
}

export interface StudentListResponse {
  items: StudentListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface FeatureImportance {
  feature: string;
  importance: number;
  actual_value?: string | number | null;
}

export interface PredictionResult {
  risk_level: RiskLevel;
  probability: number;
  feature_importance: FeatureImportance[];
  explanation: string;
  recommendations: string[];
  comparison_model_probability: number;
}

export interface PredictionHistoryItem {
  id: number;
  student_id: number;
  risk_score: number;
  risk_level: RiskLevel;
  model_name: string;
  explanation: string;
  feature_importance: FeatureImportance[];
  recommendations: string[];
  created_at: string;
}

export interface AlertHistoryItem {
  id: number;
  student_id: number | null;
  sent_by: string;
  recipient_name: string;
  recipient_email: string;
  risk_level: RiskLevel | string;
  status: string;
  error_message: string;
  created_at: string;
}

export interface RecommendationsData {
  academic: string[];
  career: string[];
  learning_pathways: string[];
  meeting_plan: {
    discuss_first: string;
    faculty_questions: string[];
    student_actions: string[];
    parent_involvement_needed: boolean;
    parent_involvement_reason: string;
  };
}

export interface AnalyticsData {
  kpis: {
    total_students: number;
    high_risk_students: number;
    action_needed_today: number;
    medium_risk_students: number;
    low_risk_students: number;
    safe_risk_students: number;
    average_gpa: number;
    average_attendance: number;
  };
  risk_distribution: { label: string; value: number }[];
  department_risk: { label: string; value: number }[];
  attendance_vs_gpa: { student: string; attendance: number; gpa: number }[];
}

export interface FacultyPerformanceItem {
  faculty_name: string;
  assigned_students: number;
  high_risk_students: number;
  medium_risk_students: number;
  overdue_followups: number;
  resolved_this_week: number;
  average_attendance: number;
}

export interface FacultyPerformanceData {
  faculty_summary: FacultyPerformanceItem[];
}

export type InterventionStatus = "pending" | "in_progress" | "resolved";
export type FollowUpOutcome = "attended" | "missed" | "rescheduled" | "resolved";

export interface InterventionRecord {
  id: number;
  student_id: number;
  contacted_student: boolean;
  parent_informed: boolean;
  counselor_assigned: boolean;
  fee_issue_escalated: boolean;
  next_follow_up_date: string | null;
  follow_up_outcome: FollowUpOutcome | null;
  status: InterventionStatus;
  resolved_at: string | null;
  notes: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}

export interface InterventionHistoryRecord {
  id: number;
  intervention_id: number;
  student_id: number;
  changed_by: string;
  changed_fields: string;
  change_summary: string;
  created_at: string;
}

export interface InterventionSaveResponse {
  intervention: InterventionRecord;
  history_entry: InterventionHistoryRecord | null;
  email_status: string;
  email_detail: string;
}

export interface InterventionAssistResponse {
  suggested_note: string;
  recommended_follow_up_date: string | null;
  suggest_parent_informed: boolean;
  parent_informed_reason: string;
}

export interface InterventionStudentOverview {
  student_id: number;
  registration_number: string;
  student_name: string;
  student_email: string;
  counselor_name: string;
  attendance: number;
  latest_risk_level: RiskLevel;
  latest_risk_score: number;
  intervention: InterventionRecord | null;
  history: InterventionHistoryRecord[];
}
