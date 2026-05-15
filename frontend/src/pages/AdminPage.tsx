import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock3, Download, Search, Users, X } from "lucide-react";

import StatCard from "../components/StatCard";
import RiskBadge from "../components/RiskBadge";
import { downloadInterventionHistoryPdf, fetchFacultyPerformance, fetchInterventions, fetchStudentsPage } from "../api/endpoints";
import { FacultyPerformanceItem, InterventionStudentOverview, StudentListItem } from "../types";

const HISTORY_FIELD_LABELS: Record<string, string> = {
  notes: "Notes",
  contacted_student: "Student Contacted",
  parent_informed: "Parent Informed",
  counselor_assigned: "Counselor Assigned",
  fee_issue_escalated: "Fee Issue Escalated",
  next_follow_up_date: "Next Follow-Up Date",
  status: "Status",
  follow_up_outcome: "Follow-Up Outcome",
  resolved_at: "Resolved At",
};

function formatHistoryFields(changedFields: string) {
  return changedFields
    .split(",")
    .map((field) => field.trim())
    .filter(Boolean)
    .map((field) => HISTORY_FIELD_LABELS[field] ?? field.replace(/_/g, " "))
    .join(", ");
}

function formatHistorySummary(summary: string) {
  const segments = summary
    .split(";")
    .map((segment) => segment.trim())
    .filter(Boolean);

  const formatted = segments.map((segment) => {
    let match = segment.match(/^contacted student:\s*(.+?)\s*->\s*(.+)$/i);
    if (match) {
      return match[2].trim().toLowerCase() === "true" ? "The student was contacted." : "The student was not contacted.";
    }

    match = segment.match(/^parent informed:\s*(.+?)\s*->\s*(.+)$/i);
    if (match) {
      return match[2].trim().toLowerCase() === "true" ? "The parent was informed." : "The parent was not informed.";
    }

    match = segment.match(/^fee issue escalated:\s*(.+?)\s*->\s*(.+)$/i);
    if (match) {
      return match[2].trim().toLowerCase() === "true"
        ? "The fee issue was escalated."
        : "The fee issue was not escalated.";
    }

    match = segment.match(/^next follow-up date:\s*(.+?)\s*->\s*(.+)$/i);
    if (match) {
      const nextDate = match[2].trim();
      return nextDate.toLowerCase() === "empty" ? "The next follow-up date was cleared." : `The next follow-up date was set to ${nextDate}.`;
    }

    match = segment.match(/^status:\s*(.+?)\s*->\s*(.+)$/i);
    if (match) {
      const nextStatus = match[2].trim().replace(/_/g, " ");
      return `The status was updated to ${nextStatus}.`;
    }

    match = segment.match(/^follow-up outcome:\s*(.+?)\s*->\s*(.+)$/i);
    if (match) {
      const outcome = match[2].trim().replace(/_/g, " ");
      return `The follow-up outcome was recorded as ${outcome}.`;
    }

    match = segment.match(/^resolved at:\s*(.+?)\s*->\s*(.+)$/i);
    if (match) {
      return `The case was marked resolved at ${match[2].trim()}.`;
    }

    match = segment.match(/^notes:\s*(.+?)\s*->\s*(.+)$/i);
    if (match) {
      const nextNotes = match[2].trim();
      return nextNotes.toLowerCase() === "empty" ? "The intervention notes were cleared." : `Updated notes: ${nextNotes}`;
    }

    return `${segment.replace(/\s*->\s*/g, " changed to ").replace(/\bempty changed to\b/gi, "set to")}.`;
  });

  return formatted.join(" ");
}

export default function AdminPage() {
  const [facultyPerformance, setFacultyPerformance] = useState<FacultyPerformanceItem[]>([]);
  const [interventionRecords, setInterventionRecords] = useState<InterventionStudentOverview[]>([]);
  const [selectedFacultyStudents, setSelectedFacultyStudents] = useState<StudentListItem[]>([]);
  const [selectedFacultyName, setSelectedFacultyName] = useState<string | null>(null);
  const [selectedStudentForHistory, setSelectedStudentForHistory] = useState<StudentListItem | null>(null);
  const [isLoadingFacultyStudents, setIsLoadingFacultyStudents] = useState(false);
  const [performanceError, setPerformanceError] = useState("");
  const [facultySearchTerm, setFacultySearchTerm] = useState("");
  const drilldownSectionRef = useRef<HTMLElement | null>(null);
  const interventionActivityRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchFacultyPerformance()
      .then((response) => setFacultyPerformance(response.faculty_summary))
      .catch(() => setPerformanceError("Unable to load faculty performance dashboard."));

    fetchInterventions()
      .then((response) => setInterventionRecords(response))
      .catch(() => setPerformanceError("Unable to load counselor intervention activity."));
  }, []);

  const overview = useMemo(() => {
    return {
      facultyCount: facultyPerformance.length,
      assignedStudents: facultyPerformance.reduce((sum, item) => sum + item.assigned_students, 0),
      overdueFollowups: facultyPerformance.reduce((sum, item) => sum + item.overdue_followups, 0),
      resolvedThisWeek: facultyPerformance.reduce((sum, item) => sum + item.resolved_this_week, 0),
    };
  }, [facultyPerformance]);

  const filteredFacultyPerformance = useMemo(() => {
    const query = facultySearchTerm.trim().toLowerCase();
    if (!query) return facultyPerformance;
    return facultyPerformance.filter((item) => item.faculty_name.toLowerCase().includes(query));
  }, [facultyPerformance, facultySearchTerm]);

  const selectedFacultyOverview = useMemo(
    () => facultyPerformance.find((item) => item.faculty_name === selectedFacultyName) ?? null,
    [facultyPerformance, selectedFacultyName]
  );

  const selectedFacultyInterventions = useMemo(() => {
    const records = new Map<number, InterventionStudentOverview>();
    interventionRecords.forEach((record) => records.set(record.student_id, record));
    return records;
  }, [interventionRecords]);

  const selectedFacultySummary = useMemo(() => {
    const highRiskStudents = selectedFacultyStudents.filter((student) => student.latest_risk_level === "High").length;
    const mediumRiskStudents = selectedFacultyStudents.filter((student) => student.latest_risk_level === "Medium").length;
    const activeInterventions = selectedFacultyStudents.filter((student) => {
      const status = selectedFacultyInterventions.get(student.id)?.intervention?.status;
      return status === "pending" || status === "in_progress";
    }).length;
    const overdueFollowups = selectedFacultyStudents.filter((student) => {
      const record = selectedFacultyInterventions.get(student.id);
      if (!record?.intervention?.next_follow_up_date || record.intervention.status === "resolved") return false;
      const followUpDate = new Date(record.intervention.next_follow_up_date);
      const today = new Date();
      followUpDate.setHours(0, 0, 0, 0);
      today.setHours(0, 0, 0, 0);
      return followUpDate.getTime() < today.getTime();
    }).length;
    const resolvedThisWeek = selectedFacultyStudents.filter((student) => {
      const resolvedAt = selectedFacultyInterventions.get(student.id)?.intervention?.resolved_at;
      if (!resolvedAt) return false;
      const resolvedDate = new Date(resolvedAt);
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      return resolvedDate >= weekAgo;
    }).length;

    return {
      studentsInView: selectedFacultyStudents.length,
      highRiskStudents,
      mediumRiskStudents,
      activeInterventions,
      overdueFollowups,
      resolvedThisWeek,
    };
  }, [selectedFacultyInterventions, selectedFacultyStudents]);

  const selectedStudentHistoryRecord = useMemo(() => {
    if (!selectedStudentForHistory) return null;
    return selectedFacultyInterventions.get(selectedStudentForHistory.id) ?? null;
  }, [selectedFacultyInterventions, selectedStudentForHistory]);

  const studentsWithInterventionHistory = useMemo(
    () =>
      selectedFacultyStudents.filter((student) => {
        const record = selectedFacultyInterventions.get(student.id);
        return Boolean(record?.history.length);
      }),
    [selectedFacultyInterventions, selectedFacultyStudents]
  );

  useEffect(() => {
    if (!selectedFacultyName) {
      setSelectedFacultyStudents([]);
      setSelectedStudentForHistory(null);
      return;
    }

    setIsLoadingFacultyStudents(true);
    Promise.all([
      fetchStudentsPage({
        page: 1,
        page_size: 100,
        counselor_name: selectedFacultyName,
        risk_level: "High",
      }),
      fetchStudentsPage({
        page: 1,
        page_size: 100,
        counselor_name: selectedFacultyName,
        risk_level: "Medium",
      }),
    ])
      .then(([highResponse, mediumResponse]) => {
        setSelectedFacultyStudents([...highResponse.items, ...mediumResponse.items]);
        setSelectedStudentForHistory(null);
        setPerformanceError("");
      })
      .catch(() => setPerformanceError("Unable to load medium and high-risk students for this counselor."))
      .finally(() => setIsLoadingFacultyStudents(false));
  }, [selectedFacultyName]);

  useEffect(() => {
    if (!selectedFacultyName) return;
    window.requestAnimationFrame(() => {
      drilldownSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [selectedFacultyName]);

  const scrollToInterventionActivity = (studentId: number) => {
    const student = selectedFacultyStudents.find((item) => item.id === studentId) ?? null;
    setSelectedStudentForHistory(student);
    interventionActivityRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-tide">Administration</p>
        <h1 className="mt-3 font-display text-4xl text-ink">Admin Console</h1>
        <p className="mt-3 text-slate-600">Manage platform access and faculty performance insights from one place.</p>
      </section>

      <section className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-tide">Admin Insight</p>
        <h2 className="mt-3 font-display text-3xl text-ink">Faculty Performance Dashboard</h2>
        <p className="mt-3 text-slate-600">
          Track faculty workload, risk ownership, overdue follow-ups, and resolved intervention outcomes across the assigned student batches.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Faculty Accounts" value={String(overview.facultyCount)} icon={<Users size={20} />} tone="bg-mist" />
          <StatCard label="Assigned Students" value={String(overview.assignedStudents)} icon={<Users size={20} />} />
          <StatCard label="Overdue Follow-ups" value={String(overview.overdueFollowups)} icon={<Clock3 size={20} />} tone="bg-amber-50" />
          <StatCard label="Resolved This Week" value={String(overview.resolvedThisWeek)} icon={<CheckCircle2 size={20} />} tone="bg-emerald-50" />
        </div>

        <div className="mt-8 flex w-full justify-end">
          <div className="relative w-full max-w-md">
            <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              value={facultySearchTerm}
              onChange={(event) => setFacultySearchTerm(event.target.value)}
              placeholder="Search faculty by name"
              className="w-full rounded-2xl border border-slate-200 py-3 pl-11 pr-4 text-sm text-ink outline-none focus:border-tide"
            />
          </div>
        </div>

        <div className="mt-8 overflow-x-auto rounded-[1.5rem] border border-slate-100">
          <table className="min-w-[980px] table-fixed text-left text-sm">
            <colgroup>
              <col className="w-[32%]" />
              <col className="w-[10%]" />
              <col className="w-[10%]" />
              <col className="w-[12%]" />
              <col className="w-[14%]" />
              <col className="w-[14%]" />
              <col className="w-[18%]" />
            </colgroup>
            <thead className="bg-ink text-white">
              <tr>
                <th className="px-5 py-4 font-medium">Faculty</th>
                <th className="px-5 py-4 font-medium">Assigned</th>
                <th className="px-5 py-4 font-medium">High Risk</th>
                <th className="px-5 py-4 font-medium">Medium Risk</th>
                <th className="px-5 py-4 font-medium">Overdue Follow-ups</th>
                <th className="px-5 py-4 font-medium">Resolved This Week</th>
                <th className="px-5 py-4 font-medium">Avg Attendance</th>
              </tr>
            </thead>
            <tbody>
              {filteredFacultyPerformance.length > 0 ? (
                filteredFacultyPerformance.map((item) => (
                  <tr key={item.faculty_name} className="border-b border-slate-100 bg-white">
                    <td className="px-5 py-4 font-semibold text-ink">
                      <button
                        type="button"
                        onClick={() => setSelectedFacultyName(item.faculty_name)}
                        className="block max-w-full truncate text-left text-ink underline-offset-4 hover:text-[#26459d] hover:underline"
                      >
                        {item.faculty_name}
                      </button>
                    </td>
                    <td className="px-5 py-4">{item.assigned_students}</td>
                    <td className="px-5 py-4 text-red-600">{item.high_risk_students}</td>
                    <td className="px-5 py-4 text-amber-600">{item.medium_risk_students}</td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 ${item.overdue_followups > 0 ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"}`}>
                        <AlertTriangle size={14} />
                        {item.overdue_followups}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-emerald-700">{item.resolved_this_week}</td>
                    <td className="px-5 py-4">{item.average_attendance}%</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-5 py-6 text-center text-slate-500">
                    No faculty match the current search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {performanceError ? <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-red-700">{performanceError}</p> : null}
      </section>

      {selectedFacultyName ? (
        <section ref={drilldownSectionRef} className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-tide">Counselor Drilldown</p>
              <h2 className="mt-3 font-display text-3xl text-ink">{selectedFacultyName}</h2>
              <p className="mt-3 text-slate-600">
                Admin view of this counselor's current medium and high-risk students, follow-up state, and intervention work.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setSelectedFacultyName(null)}
              className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
            >
              <X size={16} />
              Close
            </button>
          </div>

          {selectedFacultyOverview ? (
            <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
              <StatCard label="Assigned Students" value={String(selectedFacultyOverview.assigned_students)} icon={<Users size={20} />} />
              <StatCard label="Students In View" value={String(selectedFacultySummary.studentsInView)} icon={<Users size={20} />} tone="bg-mist" />
              <StatCard label="High Risk Students" value={String(selectedFacultySummary.highRiskStudents)} icon={<AlertTriangle size={20} />} tone="bg-red-50" />
              <StatCard label="Medium Risk Students" value={String(selectedFacultySummary.mediumRiskStudents)} icon={<AlertTriangle size={20} />} tone="bg-amber-50" />
              <StatCard label="Going On Intervention" value={String(selectedFacultySummary.activeInterventions)} icon={<Clock3 size={20} />} tone="bg-sky-50" />
              <StatCard label="Overdue Follow-ups" value={String(selectedFacultySummary.overdueFollowups)} icon={<Clock3 size={20} />} tone="bg-amber-50" />
              <StatCard label="Resolved This Week" value={String(selectedFacultySummary.resolvedThisWeek)} icon={<CheckCircle2 size={20} />} tone="bg-emerald-50" />
            </div>
          ) : null}

          <div className="mt-8 overflow-x-auto rounded-[1.5rem] border border-slate-100">
            <table className="min-w-[980px] table-fixed text-left text-sm">
              <colgroup>
                <col className="w-[28%]" />
                <col className="w-[16%]" />
                <col className="w-[12%]" />
                <col className="w-[14%]" />
                <col className="w-[16%]" />
                <col className="w-[14%]" />
                <col className="w-[14%]" />
              </colgroup>
              <thead className="bg-ink text-white">
                <tr>
                  <th className="px-5 py-4 font-medium">Student</th>
                  <th className="px-5 py-4 font-medium">Reg No</th>
                  <th className="px-5 py-4 font-medium">Attendance</th>
                  <th className="px-5 py-4 font-medium">Risk</th>
                  <th className="px-5 py-4 font-medium">Intervention Status</th>
                  <th className="px-5 py-4 font-medium">Next Follow-Up</th>
                  <th className="px-5 py-4 font-medium">Updated By</th>
                </tr>
              </thead>
              <tbody>
                {isLoadingFacultyStudents ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-6 text-center text-slate-500">
                      Loading medium and high-risk students for this counselor.
                    </td>
                  </tr>
                ) : selectedFacultyStudents.length > 0 ? (
                  selectedFacultyStudents.map((student) => {
                    const record = selectedFacultyInterventions.get(student.id);
                    return (
                    <tr key={student.id} className="border-b border-slate-100 bg-white align-top">
                      <td className="px-5 py-4 align-top">
                        <button
                          type="button"
                          onClick={() => scrollToInterventionActivity(student.id)}
                          className="block max-w-full truncate text-left font-semibold text-ink underline-offset-4 hover:text-[#26459d] hover:underline"
                        >
                          {student.name}
                        </button>
                        <div className="mt-1 truncate text-sm text-slate-500">{student.email}</div>
                      </td>
                      <td className="px-5 py-4 align-top break-words">{student.registration_number}</td>
                      <td className="px-5 py-4">{student.attendance.toFixed(0)}%</td>
                      <td className="px-5 py-4">
                        <RiskBadge level={student.latest_risk_level ?? "High"} />
                      </td>
                      <td className="px-5 py-4 capitalize">{record?.intervention?.status === "in_progress" ? "in progress" : record?.intervention?.status ?? "pending"}</td>
                      <td className="px-5 py-4 break-words">
                        {record?.intervention?.next_follow_up_date
                          ? new Date(record.intervention.next_follow_up_date).toLocaleDateString("en-IN", {
                              day: "2-digit",
                              month: "short",
                              year: "numeric",
                            })
                          : "-"}
                      </td>
                      <td className="px-5 py-4 break-words">{record?.intervention?.updated_by || "-"}</td>
                    </tr>
                  )})
                ) : (
                  <tr>
                    <td colSpan={7} className="px-5 py-6 text-center text-slate-500">
                      No medium or high-risk students are currently visible for this counselor. The assigned students for this counselor are currently in safe or low risk.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div ref={interventionActivityRef} className="mt-8 space-y-4">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-tide">Intervention Activity</p>
              <h3 className="mt-2 text-2xl font-semibold text-ink">
                {selectedStudentForHistory ? `${selectedStudentForHistory.name}'s Intervention History` : "Students With Intervention History"}
              </h3>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-end">
              {selectedStudentForHistory ? (
                <button
                  type="button"
                  onClick={() => setSelectedStudentForHistory(null)}
                  className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                >
                  <X size={16} />
                  Close
                </button>
              ) : null}
              <button
                type="button"
                onClick={() =>
                  selectedFacultyName
                    ? downloadInterventionHistoryPdf(selectedFacultyName, selectedStudentForHistory?.id)
                    : Promise.resolve()
                }
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 sm:w-auto"
              >
                <Download size={16} />
                {selectedStudentForHistory ? "Download Student PDF" : "Download PDF"}
              </button>
            </div>
            {selectedStudentForHistory ? (
              selectedStudentHistoryRecord?.history.length ? (
                <div
                  id={`intervention-history-${selectedStudentForHistory.id}`}
                  className="rounded-[1.5rem] border border-slate-200 bg-slate-50 px-5 py-5"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-ink">{selectedStudentForHistory.name}</div>
                      <div className="mt-1 text-sm text-slate-500">{selectedStudentForHistory.registration_number}</div>
                    </div>
                    <RiskBadge level={selectedStudentForHistory.latest_risk_level ?? "High"} />
                  </div>

                  {selectedStudentHistoryRecord?.intervention?.notes ? (
                    <div className="mt-4 rounded-2xl bg-white px-4 py-4">
                      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Latest Note</div>
                      <div className="mt-2 text-sm leading-6 text-slate-700">{selectedStudentHistoryRecord.intervention.notes}</div>
                    </div>
                  ) : null}

                  <div className="mt-4 space-y-3">
                    {selectedStudentHistoryRecord.history.map((entry) => (
                        <div key={entry.id} className="rounded-2xl bg-white px-4 py-4">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="font-semibold text-ink">{entry.changed_by}</div>
                            <div className="text-sm text-slate-500">
                              {new Date(entry.created_at).toLocaleString("en-IN", {
                                dateStyle: "medium",
                                timeStyle: "short",
                              })}
                            </div>
                          </div>
                          <div className="mt-2 text-sm font-medium text-slate-600">
                            Changed: {formatHistoryFields(entry.changed_fields)}
                          </div>
                          <div className="mt-2 text-sm leading-6 text-slate-600">{formatHistorySummary(entry.change_summary)}</div>
                        </div>
                      ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-[1.5rem] border border-dashed border-slate-300 px-5 py-8 text-center text-sm text-slate-500">
                  No history is available for {selectedStudentForHistory.name}.
                </div>
              )
            ) : (
              studentsWithInterventionHistory.length > 0 ? (
                studentsWithInterventionHistory.map((student) => {
                  const record = selectedFacultyInterventions.get(student.id);
                  return (
                    <div
                      id={`intervention-history-${student.id}`}
                      key={`${student.id}-history`}
                      className="rounded-[1.5rem] border border-slate-200 bg-slate-50 px-5 py-5"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-ink">{student.name}</div>
                          <div className="mt-1 text-sm text-slate-500">{student.registration_number}</div>
                        </div>
                        <RiskBadge level={student.latest_risk_level ?? "High"} />
                      </div>

                      {record?.intervention?.notes ? (
                        <div className="mt-4 rounded-2xl bg-white px-4 py-4">
                          <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Latest Note</div>
                          <div className="mt-2 text-sm leading-6 text-slate-700">{record.intervention.notes}</div>
                        </div>
                      ) : null}

                      <div className="mt-4 space-y-3">
                        {record?.history.map((entry) => (
                          <div key={entry.id} className="rounded-2xl bg-white px-4 py-4">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <div className="font-semibold text-ink">{entry.changed_by}</div>
                              <div className="text-sm text-slate-500">
                                {new Date(entry.created_at).toLocaleString("en-IN", {
                                  dateStyle: "medium",
                                  timeStyle: "short",
                                })}
                              </div>
                            </div>
                            <div className="mt-2 text-sm font-medium text-slate-600">
                              Changed: {formatHistoryFields(entry.changed_fields)}
                            </div>
                            <div className="mt-2 text-sm leading-6 text-slate-600">{formatHistorySummary(entry.change_summary)}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="rounded-[1.5rem] border border-dashed border-slate-300 px-5 py-8 text-center text-sm text-slate-500">
                  No students with intervention history are available for this counselor right now because there are no medium or high-risk students in view.
                </div>
              )
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}
