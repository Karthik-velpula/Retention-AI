import { BellRing, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { fetchAlertHistory, fetchStudent, fetchStudents, sendAlertEmail } from "../api/endpoints";
import { AlertHistoryItem, StudentListItem } from "../types";

type AlertFilter = "High" | "Medium";

export default function AlertsPage() {
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [filter, setFilter] = useState<AlertFilter>("High");
  const [searchTerm, setSearchTerm] = useState("");
  const [historySearchTerm, setHistorySearchTerm] = useState("");
  const [historyRiskFilter, setHistoryRiskFilter] = useState<"All" | "High" | "Medium">("All");
  const [historyStatusFilter, setHistoryStatusFilter] = useState<"All" | "sent" | "failed">("All");
  const [historyDateFrom, setHistoryDateFrom] = useState("");
  const [historyDateTo, setHistoryDateTo] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [status, setStatus] = useState("");
  const [busyStudentId, setBusyStudentId] = useState<number | null>(null);
  const [isBulkSending, setIsBulkSending] = useState(false);
  const [error, setError] = useState("");
  const [alertHistory, setAlertHistory] = useState<AlertHistoryItem[]>([]);
  const [subjectAttendanceRows, setSubjectAttendanceRows] = useState<
    Array<{
      registrationNumber: string;
      name: string;
      counselorName: string;
      subjectAttendance: Record<string, string>;
    }>
  >([]);
  const [subjectAttendanceTitle, setSubjectAttendanceTitle] = useState("Subject-Wise Attendance");
  const attendanceSectionRef = useRef<HTMLElement | null>(null);
  const pageSize = 10;

  const buildAlertContent = (student: StudentListItem) => {
    const reasons: string[] = [];
    const recommendations: string[] = [];
    const riskLevel = student.latest_risk_level ?? "Medium";

    if (student.attendance < 75) {
      reasons.push(`attendance is low at ${student.attendance.toFixed(0)}%`);
      recommendations.push("Improve class attendance and avoid missing upcoming sessions.");
    }
    if (student.marks < 50) {
      reasons.push(`marks are low at ${student.marks.toFixed(1)}%`);
      recommendations.push("Spend extra time on weak subjects and meet the faculty mentor for academic support.");
    }
    if (student.lms_activity_percentage < 60) {
      reasons.push(`LMS activity is low at ${student.lms_activity_percentage.toFixed(0)}%`);
      recommendations.push("Complete pending LMS work and stay active in the weekly coding activities.");
    }
    if (student.fees_paid_status !== "Paid") {
      reasons.push("fee status is pending");
      recommendations.push("Clear the pending fee dues or contact the accounts team for guidance.");
    }
    if (student.gpa < 7) {
      reasons.push(`CGPA is at ${student.gpa.toFixed(2)}`);
      recommendations.push("Focus on consistent preparation to improve the overall CGPA.");
    }

    if (reasons.length === 0) {
      if (riskLevel === "High") {
        if (student.lms_activity_percentage < 80) {
          reasons.push(`LMS activity needs improvement at ${student.lms_activity_percentage.toFixed(0)}%`);
        } else if (student.marks < 60) {
          reasons.push(`marks need improvement at ${student.marks.toFixed(1)}%`);
        } else if (student.gpa < 8) {
          reasons.push(`CGPA needs improvement at ${student.gpa.toFixed(2)}`);
        } else {
          reasons.push("multiple academic and engagement indicators placed the student in high risk");
        }
      } else {
        if (student.lms_activity_percentage < 80) {
          reasons.push(`LMS activity needs improvement at ${student.lms_activity_percentage.toFixed(0)}%`);
        } else if (student.marks < 60) {
          reasons.push(`marks need improvement at ${student.marks.toFixed(1)}%`);
        } else if (student.gpa < 8) {
          reasons.push(`CGPA needs improvement at ${student.gpa.toFixed(2)}`);
        } else if (student.fees_paid_status !== "Paid") {
          reasons.push("fee status needs attention");
        } else {
          reasons.push("current academic and engagement indicators placed the student in medium risk");
        }
      }
    }

    if (recommendations.length === 0) {
      recommendations.push("Stay in touch with the counselor and follow the academic improvement plan closely.");
      recommendations.push("Review attendance, LMS activity, and assessment performance every week.");
    }

    return {
      riskLevel,
      reasons,
      explanation: `The student is marked as ${riskLevel} risk because ${reasons.join(", ")}.`,
      recommendations: Array.from(new Set(recommendations)).slice(0, 4),
    };
  };

  useEffect(() => {
    fetchStudents()
      .then((response) => {
        setStudents(response);
        setError("");
      })
      .catch(() => setError("Unable to load students for alerts."));

    fetchAlertHistory()
      .then((response) => setAlertHistory(response))
      .catch(() => setError("Unable to load alert history."));
  }, []);

  const filteredStudents = useMemo(() => {
    return students.filter((student) => {
      const risk = student.latest_risk_level ?? "Low";
      const matchesRisk = risk === filter;

      const query = searchTerm.trim().toLowerCase();
      const matchesSearch =
        !query ||
        [student.name, student.email, student.registration_number, student.counselor_name ?? ""]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));

      return matchesRisk && matchesSearch;
    });
  }, [filter, searchTerm, students]);

  const totalPages = Math.max(1, Math.ceil(filteredStudents.length / pageSize));

  useEffect(() => {
    setCurrentPage(1);
  }, [filter, searchTerm]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const paginatedStudents = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredStudents.slice(startIndex, startIndex + pageSize);
  }, [currentPage, filteredStudents]);

  const subjectAttendanceColumns = useMemo(() => {
    const columns = new Set<string>();
    subjectAttendanceRows.forEach((row) => {
      Object.keys(row.subjectAttendance).forEach((subject) => columns.add(subject));
    });
    return Array.from(columns).sort((a, b) => a.localeCompare(b));
  }, [subjectAttendanceRows]);

  const filteredAlertHistory = useMemo(() => {
    const query = historySearchTerm.trim().toLowerCase();
    return alertHistory.filter((entry) => {
      const matchesSearch =
        !query ||
        [entry.sent_by, entry.recipient_name, entry.recipient_email, entry.risk_level, entry.status, entry.error_message]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));

      const matchesRisk = historyRiskFilter === "All" || entry.risk_level === historyRiskFilter;
      const matchesStatus = historyStatusFilter === "All" || entry.status.toLowerCase() === historyStatusFilter;

      const createdAt = new Date(entry.created_at);
      const from = historyDateFrom ? new Date(`${historyDateFrom}T00:00:00`) : null;
      const to = historyDateTo ? new Date(`${historyDateTo}T23:59:59`) : null;
      const matchesFrom = !from || createdAt >= from;
      const matchesTo = !to || createdAt <= to;

      return matchesSearch && matchesRisk && matchesStatus && matchesFrom && matchesTo;
    });
  }, [alertHistory, historyDateFrom, historyDateTo, historyRiskFilter, historySearchTerm, historyStatusFilter]);

  const handleDownloadHistoryCsv = () => {
    if (filteredAlertHistory.length === 0) {
      setStatus("No alert history rows match the current filters.");
      return;
    }

    const rows = [
      ["Sent By", "Recipient Name", "Recipient Email", "When", "Risk", "Status", "Error Message"],
      ...filteredAlertHistory.map((entry) => [
        entry.sent_by,
        entry.recipient_name,
        entry.recipient_email,
        new Date(entry.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }),
        entry.risk_level,
        entry.status,
        entry.error_message ?? "",
      ]),
    ];

    const csv = rows
      .map((row) => row.map((value) => `"${String(value).replace(/"/g, `""`)}"`).join(","))
      .join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "alert-history.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleSendAlert = async (student: StudentListItem) => {
    try {
      setBusyStudentId(student.id);
      setError("");
      setStatus("");

      await fetchStudent(student.id);
      const alertContent = buildAlertContent(student);

      await sendAlertEmail({
        student_id: student.id,
        student_name: student.name,
        student_email: student.email,
        risk_level: alertContent.riskLevel,
        explanation: alertContent.explanation,
        recommendations: alertContent.recommendations,
      });
      const history = await fetchAlertHistory();
      setAlertHistory(history);
      setStatus(`Alert email sent to ${student.name} (${student.email}) with the risk reasons and recommendations.`);
    } catch {
      fetchAlertHistory().then(setAlertHistory).catch(() => undefined);
      setError(`Unable to send alert for ${student.name}. Check SMTP configuration and backend status.`);
    } finally {
      setBusyStudentId(null);
    }
  };

  const handleSendBulkAlerts = async () => {
    if (filteredStudents.length === 0) {
      setStatus("No students match the current alert filter.");
      return;
    }

    try {
      setIsBulkSending(true);
      setError("");
      setStatus("");

      let sentCount = 0;

      for (const student of filteredStudents) {
        await fetchStudent(student.id);
        const alertContent = buildAlertContent(student);

        await sendAlertEmail({
          student_id: student.id,
          student_name: student.name,
          student_email: student.email,
          risk_level: alertContent.riskLevel,
          explanation: alertContent.explanation,
          recommendations: alertContent.recommendations,
        });
        sentCount += 1;
      }

      setAlertHistory(await fetchAlertHistory());
      setStatus(
        `Bulk alert completed. Sent ${sentCount} email(s) with risk reasons and recommendations.`
      );
    } catch {
      fetchAlertHistory().then(setAlertHistory).catch(() => undefined);
      setError("Unable to complete the bulk alert action. Check SMTP configuration and backend status.");
    } finally {
      setIsBulkSending(false);
    }
  };

  const viewSingleStudentAttendance = async (student: StudentListItem) => {
    try {
      setError("");
      const detail = await fetchStudent(student.id);
      setSubjectAttendanceRows([
        {
          registrationNumber: detail.registration_number,
          name: detail.name,
          counselorName: detail.counselor_name ?? "",
          subjectAttendance: Object.fromEntries(
            detail.subject_attendance.map((subject) => [subject.subject_name, subject.attendance_percentage.toFixed(2)])
          ),
        },
      ]);
      setSubjectAttendanceTitle(`Subject-Wise Attendance - ${detail.name}`);
      window.requestAnimationFrame(() => {
        attendanceSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch {
      setError(`Unable to load subject-wise attendance for ${student.name}.`);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-white p-8 shadow-soft">
        <p className="text-xs uppercase tracking-[0.3em] text-tide">Admin Alerts</p>
        <h1 className="mt-3 font-display text-4xl text-ink">Alert Students</h1>
        <p className="mt-3 text-slate-600">Filter High and Medium risk students, then send alert emails directly to the selected student with reasons and recommendations.</p>
      </section>

      <section className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[1.1fr_0.6fr_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search by name, register number, email, or counselor"
              className="w-full rounded-2xl border border-slate-200 py-3 pl-11 pr-4 text-sm text-ink outline-none focus:border-tide"
            />
          </div>
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value as AlertFilter)}
            className="rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
          >
            <option>High</option>
            <option>Medium</option>
          </select>
          <button
            onClick={handleSendBulkAlerts}
            disabled={isBulkSending || filteredStudents.length === 0}
            className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-ink px-5 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300 md:w-auto"
          >
            <BellRing size={18} />
            {isBulkSending ? "Sending Bulk Alerts..." : "Alert All Filtered Students"}
          </button>
        </div>
      </section>

      <section className="rounded-[2rem] bg-white shadow-soft">
        <div className="overflow-x-auto rounded-[2rem]">
        <table className="min-w-[980px] table-fixed text-left text-sm">
          <colgroup>
            <col className="w-[14%]" />
            <col className="w-[25%]" />
            <col className="w-[22%]" />
            <col className="w-[10%]" />
            <col className="w-[8%]" />
            <col className="w-[15%]" />
            <col className="w-[6%]" />
          </colgroup>
          <thead className="bg-ink text-white">
            <tr>
              <th className="px-5 py-4 font-medium">Reg No</th>
              <th className="px-5 py-4 font-medium">Student</th>
              <th className="px-5 py-4 font-medium">Counselor</th>
              <th className="px-5 py-4 font-medium">Attendance</th>
              <th className="px-5 py-4 font-medium">Risk</th>
              <th className="px-5 py-4 font-medium">Why Risk</th>
              <th className="px-5 py-4 font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {paginatedStudents.length > 0 ? (
              paginatedStudents.map((student) => {
                const alertContent = buildAlertContent(student);
                return (
                <tr key={student.id} className="border-b border-slate-100 bg-white align-top">
                  <td className="px-5 py-4">{student.registration_number}</td>
                  <td className="px-5 py-4">
                    <div className="font-semibold text-ink">{student.name}</div>
                    <div className="text-slate-500">{student.email}</div>
                  </td>
                  <td className="px-5 py-4">{student.counselor_name ?? "Unassigned"}</td>
                  <td className={`px-5 py-4 font-semibold ${student.attendance < 75 ? "text-red-600" : "text-ink"}`}>
                    <button
                      type="button"
                      onClick={() => viewSingleStudentAttendance(student)}
                      className="underline-offset-4 hover:underline"
                    >
                      {student.attendance.toFixed(0)}%
                    </button>
                  </td>
                  <td className="px-5 py-4">{student.latest_risk_level ?? "Low"}</td>
                  <td className="px-5 py-4 text-slate-600">
                    <div className="max-w-[16rem] space-y-2 xl:max-w-[18rem]">
                      {alertContent.reasons.length > 0 ? (
                        alertContent.reasons.map((reason) => (
                          <div key={reason} className="break-words rounded-2xl bg-mist px-3 py-2 leading-relaxed">
                            {reason}
                          </div>
                        ))
                      ) : (
                        <div className="break-words rounded-2xl bg-mist px-3 py-2 leading-relaxed">No specific reason available.</div>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <button
                      onClick={() => handleSendAlert(student)}
                      disabled={busyStudentId === student.id}
                      className="inline-flex w-full min-w-[6.5rem] items-center justify-center gap-2 rounded-2xl bg-coral px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
                    >
                      <BellRing size={16} />
                      {busyStudentId === student.id ? "Sending..." : "Alert"}
                    </button>
                  </td>
                </tr>
              )})
            ) : (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center text-slate-500">
                  No students match the current alert filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </div>
      </section>

      {subjectAttendanceRows.length > 0 ? (
        <section ref={attendanceSectionRef} className="rounded-[2rem] bg-white p-6 shadow-soft">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-tide">Attendance View</p>
              <h2 className="mt-2 font-display text-2xl text-ink">{subjectAttendanceTitle}</h2>
            </div>
            <button
              type="button"
              onClick={() => {
                setSubjectAttendanceRows([]);
                setSubjectAttendanceTitle("Subject-Wise Attendance");
              }}
              className="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white p-2 text-slate-600 transition hover:border-slate-300 hover:text-ink"
              aria-label="Close subject-wise attendance view"
            >
              <X size={18} />
            </button>
          </div>

          <div className="overflow-x-auto rounded-3xl border border-slate-100">
            <table className="min-w-[1000px] text-left text-sm">
              <thead className="bg-ink text-white">
                <tr>
                  <th className="px-5 py-4 font-medium">Reg No</th>
                  <th className="px-5 py-4 font-medium">Name</th>
                  <th className="px-5 py-4 font-medium">Counselor</th>
                  {subjectAttendanceColumns.map((subject) => (
                    <th key={subject} className="px-5 py-4 font-medium">
                      {subject}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {subjectAttendanceRows.map((row) => (
                  <tr key={row.registrationNumber} className="border-t border-slate-100 bg-white">
                    <td className="px-5 py-4 font-medium text-ink">{row.registrationNumber}</td>
                    <td className="px-5 py-4 text-ink">{row.name}</td>
                    <td className="px-5 py-4 text-slate-600">{row.counselorName || "-"}</td>
                    {subjectAttendanceColumns.map((subject) => (
                      <td key={subject} className="px-5 py-4 font-medium text-ink">
                        {row.subjectAttendance[subject] ?? "-"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="flex flex-col gap-4 rounded-[2rem] bg-white px-5 py-4 shadow-soft sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="text-sm text-slate-600">
          Page {currentPage} of {totalPages}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
            disabled={currentPage === 1}
            className="rounded-2xl border border-slate-200 px-4 py-2 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
            disabled={currentPage === totalPages}
            className="rounded-2xl bg-ink px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Next
          </button>
        </div>
      </section>

      {status ? <div className="rounded-3xl bg-mist px-5 py-4 text-ink shadow-soft">{status}</div> : null}
      {error ? <div className="rounded-3xl bg-red-50 px-5 py-4 text-red-700 shadow-soft">{error}</div> : null}

      <section className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
        <div className="mb-4">
          <p className="text-xs uppercase tracking-[0.24em] text-tide">Alert History</p>
          <h2 className="mt-2 font-display text-2xl text-ink">Recent Email Activity</h2>
          <p className="mt-2 text-sm text-slate-600">Track who sent the alert, to whom it was sent, when it was sent, risk level, and whether it succeeded or failed.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-[1.2fr_0.5fr_0.5fr_0.55fr_0.55fr_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              value={historySearchTerm}
              onChange={(event) => setHistorySearchTerm(event.target.value)}
              placeholder="Search alert history by sender, recipient, email, risk, or status"
              className="w-full rounded-2xl border border-slate-200 py-3 pl-11 pr-4 text-sm text-ink outline-none focus:border-tide"
            />
          </div>
          <select
            value={historyRiskFilter}
            onChange={(event) => setHistoryRiskFilter(event.target.value as "All" | "High" | "Medium")}
            className="rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
          >
            <option value="All">All Risks</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
          </select>
          <select
            value={historyStatusFilter}
            onChange={(event) => setHistoryStatusFilter(event.target.value as "All" | "sent" | "failed")}
            className="rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
          >
            <option value="All">All Status</option>
            <option value="sent">sent</option>
            <option value="failed">failed</option>
          </select>
          <input
            type="date"
            value={historyDateFrom}
            onChange={(event) => setHistoryDateFrom(event.target.value)}
            className="rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
          />
          <input
            type="date"
            value={historyDateTo}
            onChange={(event) => setHistoryDateTo(event.target.value)}
            className="rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
          />
          <button
            onClick={handleDownloadHistoryCsv}
            className="rounded-2xl bg-ink px-5 py-3 text-sm font-semibold text-white sm:col-span-2 xl:col-span-1"
          >
            Download CSV
          </button>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-500">
          <span>{filteredAlertHistory.length} {filteredAlertHistory.length === 1 ? "history row" : "history rows"}</span>
          {(historyRiskFilter !== "All" || historyStatusFilter !== "All" || historyDateFrom || historyDateTo) ? (
            <button
              onClick={() => {
                setHistoryRiskFilter("All");
                setHistoryStatusFilter("All");
                setHistoryDateFrom("");
                setHistoryDateTo("");
              }}
              className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-ink"
            >
              Clear Filters
            </button>
          ) : null}
        </div>

        <div className="overflow-x-auto rounded-[1.5rem] border border-slate-200">
          <table className="min-w-[780px] text-left text-sm">
            <thead className="bg-slate-100 text-slate-700">
              <tr>
                <th className="px-4 py-3 font-medium">Sent By</th>
                <th className="px-4 py-3 font-medium">Recipient</th>
                <th className="px-4 py-3 font-medium">When</th>
                <th className="px-4 py-3 font-medium">Risk</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlertHistory.length > 0 ? (
                filteredAlertHistory.map((entry) => (
                  <tr key={entry.id} className="border-t border-slate-100">
                    <td className="px-4 py-4 text-slate-700">{entry.sent_by}</td>
                    <td className="px-4 py-4">
                      <div className="font-semibold text-ink">{entry.recipient_name}</div>
                      <div className="text-slate-500">{entry.recipient_email}</div>
                    </td>
                    <td className="px-4 py-4 text-slate-600">
                      {new Date(entry.created_at).toLocaleString("en-IN", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </td>
                    <td className="px-4 py-4">{entry.risk_level}</td>
                    <td className="px-4 py-4">
                      <div className={entry.status === "failed" ? "font-semibold text-red-700" : "font-semibold text-emerald-700"}>
                        {entry.status}
                      </div>
                      {entry.error_message ? <div className="mt-1 text-xs text-red-600">{entry.error_message}</div> : null}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                    No alert history entries match the current search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
