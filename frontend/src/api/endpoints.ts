import client from "./client";
import {
  AnalyticsData,
  AlertHistoryItem,
  AssistantQueryResponse,
  FacultyPerformanceData,
  GridChallengeResponse,
  LoginResponse,
  InterventionRecord,
  InterventionAssistResponse,
  InterventionSaveResponse,
  InterventionStudentOverview,
  PredictionHistoryItem,
  PredictionResult,
  RecommendationsData,
  SecurityGridResetConfirmResponse,
  SecurityGridPreviewResponse,
  StudentDetail,
  StudentListItem,
  StudentListResponse,
  RiskLevel,
} from "../types";

type CacheEntry<T> = {
  expiresAt: number;
  promise: Promise<T>;
};

const apiCache = new Map<string, CacheEntry<unknown>>();

const cacheKey = (name: string, params?: unknown) => `${name}:${JSON.stringify(params ?? {})}`;

const cachedRequest = <T>(key: string, ttlMs: number, request: () => Promise<T>) => {
  const cached = apiCache.get(key) as CacheEntry<T> | undefined;
  if (cached && cached.expiresAt > Date.now()) {
    return cached.promise;
  }

  const promise = request().catch((error) => {
    apiCache.delete(key);
    throw error;
  });
  apiCache.set(key, { expiresAt: Date.now() + ttlMs, promise });
  return promise;
};

const clearCachedRequests = (...prefixes: string[]) => {
  Array.from(apiCache.keys()).forEach((key) => {
    if (prefixes.some((prefix) => key.startsWith(prefix))) {
      apiCache.delete(key);
    }
  });
};

export const login = async (username: string, password: string) => {
  const { data } = await client.post<LoginResponse>("/ren/auth/login", { username, password });
  return data;
};

export const refreshLogin = async (refresh_token: string) => {
  const { data } = await client.post<LoginResponse>("/auth/refresh", { refresh_token });
  return data;
};

export const logoutSession = async () => {
  const { data } = await client.post<{ detail: string }>("/auth/logout");
  return data;
};

export const fetchSecurityGridPreview = async (username: string) => {
  const { data } = await client.get<SecurityGridPreviewResponse>("/auth/security-grid-preview", { params: { username } });
  return data;
};

export const fetchGridChallenge = async (username: string) => {
  const { data } = await client.get<GridChallengeResponse>("/auth/login/grid-challenge", { params: { username } });
  return data;
};

export const completeGridLogin = async (
  username: string,
  password: string,
  challenge_token: string,
  answers: Record<string, string>
) => {
  const { data } = await client.post<LoginResponse>("/auth/login/complete", {
    username,
    password,
    challenge_token,
    answers,
  });
  return data;
};

export const requestPasswordReset = async (username: string) => {
  const { data } = await client.post<{ detail: string }>("/auth/forgot-password/request", { username });
  return data;
};

export const confirmPasswordReset = async (username: string, otp: string, new_password: string) => {
  const { data } = await client.post<{ detail: string }>("/auth/forgot-password/confirm", { username, otp, new_password });
  return data;
};

export const requestSecurityGridReset = async (username: string) => {
  const { data } = await client.post<{ detail: string }>("/auth/security-grid-reset/request", { username });
  return data;
};

export const confirmSecurityGridReset = async (username: string, otp: string) => {
  const { data } = await client.post<SecurityGridResetConfirmResponse>("/auth/security-grid-reset/confirm", { username, otp });
  return data;
};

export const downloadResetSecurityGrid = async (downloadToken: string) => {
  const response = await client.get("/auth/security-grid-reset/download", {
    params: { token: downloadToken },
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "security-grid.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const downloadSecurityGridReport = async () => {
  const response = await client.get("/auth/security-grid-report", { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "user-security-grid-report.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const fetchStudents = async () => {
  return cachedRequest(cacheKey("students"), 120000, async () => {
    const { data } = await client.get<StudentListItem[]>("/students");
    return data;
  });
};

export const fetchCounselors = async () => {
  return cachedRequest(cacheKey("counselors"), 300000, async () => {
    const { data } = await client.get<string[]>("/students/counselors");
    return data;
  });
};

export const fetchStudentsPage = async (params: {
  page?: number;
  page_size?: number;
  query?: string;
  risk_level?: string;
  attendance_filter?: string;
  fee_status?: string;
  counselor_name?: string;
  section?: string;
  gender?: string;
  year?: number;
  min_cgpa?: number;
  max_cgpa?: number;
}) => {
  return cachedRequest(cacheKey("students-page", params), 120000, async () => {
    const { data } = await client.get<StudentListResponse>("/students/paged", { params });
    return data;
  });
};

export const fetchStudent = async (studentId: number) => {
  const { data } = await client.get<StudentDetail>(`/students/${studentId}`);
  return data;
};

export const fetchAnalytics = async () => {
  return cachedRequest(cacheKey("analytics"), 300000, async () => {
    const { data } = await client.get<AnalyticsData>("/analytics");
    return data;
  });
};

export const fetchFacultyPerformance = async () => {
  return cachedRequest(cacheKey("faculty-performance"), 120000, async () => {
    const { data } = await client.get<FacultyPerformanceData>("/analytics/faculty-performance");
    return data;
  });
};

export const askAssistant = async (query: string) => {
  const { data } = await client.post<AssistantQueryResponse>("/assistant/query", { query });
  return data;
};

export const predictRisk = async (studentId: number, payload: StudentDetail) => {
  const { data } = await client.post<PredictionResult>("/predict-risk", {
    student_id: studentId,
    gpa: payload.gpa,
    attendance: payload.attendance,
    marks: payload.marks,
    department: payload.department,
    year: payload.year,
    career_interest: payload.career_interest,
    skills: payload.skills,
    ...payload.lms_activity,
    ...payload.financial
  });
  return data;
};

export const fetchRecommendations = async (studentId: number) => {
  const { data } = await client.get<RecommendationsData>(`/recommendations/${studentId}`);
  return data;
};

export const fetchPredictionHistory = async (studentId: number) => {
  const { data } = await client.get<PredictionHistoryItem[]>(`/students/${studentId}/predictions`);
  return data;
};

export const downloadParentReport = async (studentId: number, studentName: string) => {
  const response = await client.get(`/students/${studentId}/parent-report`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  const safeName = studentName.trim().toLowerCase().replace(/\s+/g, "-") || `student-${studentId}`;
  link.href = url;
  link.download = `${safeName}-parent-report.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const createParentReportLink = async (studentId: number) => {
  const { data } = await client.get<{ report_url: string }>(`/students/${studentId}/parent-report-link`);
  return data.report_url;
};

export const uploadDataset = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await client.post("/students/upload-csv", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
};

export const trainModel = async () => {
  const { data } = await client.post("/train-model");
  return data;
};

export const sendAlertEmail = async (payload: {
  student_id?: number;
  student_name: string;
  student_email: string;
  risk_level: RiskLevel;
  explanation: string;
  recommendations: string[];
}) => {
  const { data } = await client.post("/send-alert-email", payload);
  clearCachedRequests("alert-history");
  return data;
};

export const fetchAlertHistory = async () => {
  return cachedRequest(cacheKey("alert-history"), 30000, async () => {
    const { data } = await client.get<AlertHistoryItem[]>("/alerts/history");
    return data;
  });
};

export const fetchInterventions = async () => {
  return cachedRequest(cacheKey("interventions"), 60000, async () => {
    const { data } = await client.get<InterventionStudentOverview[]>("/interventions");
    return data;
  });
};

export const downloadInterventionHistoryPdf = async (counselorName: string, studentId?: number) => {
  const response = await client.get("/interventions/report/pdf", {
    params: {
      counselor_name: counselorName,
      ...(studentId ? { student_id: studentId } : {}),
    },
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = studentId ? "student-intervention-history.pdf" : "intervention-history.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const saveIntervention = async (
  studentId: number,
  payload: {
    contacted_student: boolean;
    parent_informed: boolean;
    counselor_assigned: boolean;
    fee_issue_escalated: boolean;
    next_follow_up_date: string | null;
    follow_up_outcome: "attended" | "missed" | "rescheduled" | "resolved" | null;
    status: "pending" | "in_progress" | "resolved";
    notes: string;
  }
) => {
  const { data } = await client.put<InterventionSaveResponse>(`/interventions/${studentId}`, payload);
  clearCachedRequests("interventions", "faculty-performance", "students-page", "students");
  return data;
};

export const fetchInterventionAssist = async (
  studentId: number,
  payload: {
    contacted_student: boolean;
    parent_informed: boolean;
    counselor_assigned: boolean;
    fee_issue_escalated: boolean;
    status: "pending" | "in_progress" | "resolved";
  }
) => {
  const { data } = await client.post<InterventionAssistResponse>(`/interventions/${studentId}/ai-assist`, payload);
  return data;
};
