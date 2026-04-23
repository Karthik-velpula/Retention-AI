import { AlertCircle, CalendarClock, CheckCircle2, ChevronDown, Clock3, Download, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { fetchInterventions, saveIntervention } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";
import { FollowUpOutcome, InterventionStudentOverview } from "../types";

function dayLabel(dateValue: string) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const followUpDate = new Date(dateValue);
  followUpDate.setHours(0, 0, 0, 0);
  const diffDays = Math.round((followUpDate.getTime() - today.getTime()) / 86400000);

  if (diffDays < 0) return `${Math.abs(diffDays)} day(s) overdue`;
  if (diffDays === 0) return "Due today";
  return `Due in ${diffDays} day(s)`;
}

function priorityWeight(dateValue: string) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const followUpDate = new Date(dateValue);
  followUpDate.setHours(0, 0, 0, 0);
  return followUpDate.getTime() - today.getTime();
}

function isOverdue(dateValue: string) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const followUpDate = new Date(dateValue);
  followUpDate.setHours(0, 0, 0, 0);
  return followUpDate.getTime() < today.getTime();
}

function isDueToday(dateValue: string) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const followUpDate = new Date(dateValue);
  followUpDate.setHours(0, 0, 0, 0);
  return followUpDate.getTime() === today.getTime();
}

function riskChipClass(risk: string) {
  if (risk === "High") return "bg-red-100 text-red-700";
  if (risk === "Medium") return "bg-amber-100 text-amber-700";
  if (risk === "Low") return "bg-lime-100 text-lime-700";
  return "bg-emerald-100 text-emerald-700";
}

function statusChipClass(status: string) {
  if (status === "resolved") return "bg-emerald-100 text-emerald-700";
  if (status === "in_progress") return "bg-sky-100 text-sky-700";
  return "bg-slate-200 text-slate-700";
}

function dueChipClass(dateValue: string) {
  if (isOverdue(dateValue)) return "bg-red-100 text-red-700";
  if (isDueToday(dateValue)) return "bg-amber-100 text-amber-700";
  return "bg-slate-100 text-slate-700";
}

function buildCsvRows(records: InterventionStudentOverview[], role: string | null) {
  return [
    [
      "Student Name",
      "Register Number",
      "Email",
      ...(role === "admin" ? ["Counselor Name"] : []),
      "Risk",
      "Status",
      "Follow-Up Outcome",
      "Next Follow-up",
      "Due Summary",
    ],
    ...records.map((record) => [
      record.student_name,
      record.registration_number,
      record.student_email,
      ...(role === "admin" ? [record.counselor_name] : []),
      record.latest_risk_level,
      record.intervention?.status ?? "pending",
      record.intervention?.follow_up_outcome ?? "",
      record.intervention?.next_follow_up_date ?? "",
      record.intervention?.next_follow_up_date ? dayLabel(record.intervention.next_follow_up_date) : "",
    ]),
  ];
}

function SummaryCard({
  icon: Icon,
  label,
  value,
  helper,
}: {
  icon: typeof CalendarClock;
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <article className="border-r border-slate-200 bg-white px-6 py-5 last:border-r-0 xl:last:border-r-0">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-tide">{label}</p>
          <div className="mt-3 text-3xl font-semibold text-ink">{value}</div>
          <p className="mt-2 text-sm leading-6 text-slate-500">{helper}</p>
        </div>
        <div className="rounded-xl bg-slate-100 p-3 text-slate-700">
          <Icon size={20} />
        </div>
      </div>
    </article>
  );
}

export default function FollowUpsPage() {
  const { role } = useAuth();
  const [records, setRecords] = useState<InterventionStudentOverview[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [savingStudentId, setSavingStudentId] = useState<number | null>(null);
  const [rescheduleDates, setRescheduleDates] = useState<Record<number, string>>({});

  useEffect(() => {
    fetchInterventions()
      .then((response) => setRecords(response))
      .catch(() => setError("Unable to load follow-up records."));
  }, []);

  const summary = useMemo(() => {
    const activeFollowUps = records.filter((record) => record.intervention?.next_follow_up_date);
    const overdue = activeFollowUps.filter((record) => isOverdue(record.intervention?.next_follow_up_date ?? ""));
    const dueToday = activeFollowUps.filter((record) => isDueToday(record.intervention?.next_follow_up_date ?? ""));
    const resolved = records.filter(
      (record) => record.intervention?.status === "resolved" || record.intervention?.follow_up_outcome === "resolved"
    );
    const highRisk = activeFollowUps.filter((record) => record.latest_risk_level === "High");

    return {
      total: activeFollowUps.length,
      overdue: overdue.length,
      dueToday: dueToday.length,
      resolved: resolved.length,
      highRisk: highRisk.length,
    };
  }, [records]);

  const followUps = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();

    return records
      .filter((record) => record.intervention?.next_follow_up_date)
      .filter((record) => {
        if (!query) return true;
        return [record.student_name, record.student_email, record.registration_number, record.counselor_name]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));
      })
      .sort((left, right) => {
        const leftDate = left.intervention?.next_follow_up_date ?? "";
        const rightDate = right.intervention?.next_follow_up_date ?? "";
        return priorityWeight(leftDate) - priorityWeight(rightDate);
      });
  }, [records, searchTerm]);

  const handleDownload = () => {
    if (followUps.length === 0) return;

    const rows = buildCsvRows(followUps, role);
    const csv = rows
      .map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(","))
      .join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "next-follow-ups.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleOutcomeChange = async (record: InterventionStudentOverview, value: string) => {
    const intervention = record.intervention;
    if (!intervention) return;

    const normalizedValue = (value || null) as FollowUpOutcome | null;
    if (normalizedValue === "rescheduled") {
      setRescheduleDates((current) => ({
        ...current,
        [record.student_id]: intervention.next_follow_up_date ?? "",
      }));
      setStatusMessage(`Choose the new next follow-up date for ${record.student_name}.`);
      setError("");
      return;
    }

    const nextStatus = normalizedValue === "resolved" ? "resolved" : intervention.status;
    const nextFollowUpDate = normalizedValue === "resolved" ? null : intervention.next_follow_up_date;

    try {
      setSavingStudentId(record.student_id);
      setError("");
      setStatusMessage("");

      const saved = await saveIntervention(record.student_id, {
        contacted_student: intervention.contacted_student,
        parent_informed: intervention.parent_informed,
        counselor_assigned: intervention.counselor_assigned,
        fee_issue_escalated: intervention.fee_issue_escalated,
        next_follow_up_date: nextFollowUpDate,
        follow_up_outcome: normalizedValue,
        status: nextStatus,
        notes: intervention.notes,
      });

      setRecords((current) =>
        current.map((item) =>
          item.student_id === record.student_id
            ? {
                ...item,
                intervention: saved.intervention,
                history: saved.history_entry ? [saved.history_entry, ...item.history] : item.history,
              }
            : item
        )
      );

      setStatusMessage(
        normalizedValue === "resolved"
          ? `${record.student_name} was marked resolved and removed from active follow-ups.`
          : `Follow-up outcome updated for ${record.student_name}.`
      );
    } catch {
      setError("Unable to update the follow-up outcome.");
    } finally {
      setSavingStudentId(null);
    }
  };

  const handleRescheduleSave = async (record: InterventionStudentOverview) => {
    const intervention = record.intervention;
    const nextFollowUpDate = rescheduleDates[record.student_id];
    if (!intervention) return;
    if (!nextFollowUpDate) {
      setError(`Select a new next follow-up date for ${record.student_name}.`);
      setStatusMessage("");
      return;
    }

    try {
      setSavingStudentId(record.student_id);
      setError("");
      setStatusMessage("");

      const saved = await saveIntervention(record.student_id, {
        contacted_student: intervention.contacted_student,
        parent_informed: intervention.parent_informed,
        counselor_assigned: intervention.counselor_assigned,
        fee_issue_escalated: intervention.fee_issue_escalated,
        next_follow_up_date: nextFollowUpDate,
        follow_up_outcome: "rescheduled",
        status: intervention.status,
        notes: intervention.notes,
      });

      setRecords((current) =>
        current.map((item) =>
          item.student_id === record.student_id
            ? {
                ...item,
                intervention: saved.intervention,
                history: saved.history_entry ? [saved.history_entry, ...item.history] : item.history,
              }
            : item
        )
      );
      setRescheduleDates((current) => {
        const next = { ...current };
        delete next[record.student_id];
        return next;
      });
      setStatusMessage(`Follow-up rescheduled for ${record.student_name} to ${nextFollowUpDate}.`);
    } catch {
      setError("Unable to reschedule the follow-up.");
    } finally {
      setSavingStudentId(null);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-[1.75rem] border border-slate-200 bg-white shadow-soft">
        <div className="border-b border-slate-200 px-8 py-6">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-tide">Faculty Follow-Up Register</p>
          <h1 className="mt-2 font-display text-4xl text-ink">Next Follow-Ups</h1>
          <p className="mt-3 max-w-3xl text-[15px] leading-7 text-slate-600">
            Review the active follow-up queue, identify overdue cases, and record the latest outcome after each student
            interaction in a structured academic workflow.
          </p>
        </div>

        <div className="grid gap-px bg-slate-200 md:grid-cols-2 xl:grid-cols-5">
          <SummaryCard icon={CalendarClock} label="Total Follow-Ups" value={String(summary.total)} helper="Active review entries" />
          <SummaryCard icon={AlertCircle} label="Overdue" value={String(summary.overdue)} helper="Past the scheduled date" />
          <SummaryCard icon={Clock3} label="Due Today" value={String(summary.dueToday)} helper="Requires action today" />
          <SummaryCard icon={CheckCircle2} label="Resolved" value={String(summary.resolved)} helper="Closed intervention cases" />
          <SummaryCard icon={AlertCircle} label="High-Risk Follow-Ups" value={String(summary.highRisk)} helper="Priority students in queue" />
        </div>
      </section>

      <section className="rounded-[1.75rem] border border-slate-200 bg-white shadow-soft">
        <div className="border-b border-slate-200 px-6 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-tide">Search And Export</p>
              <h2 className="mt-2 text-2xl font-semibold text-ink">Follow-Up Student List</h2>
            </div>
            <button
              onClick={handleDownload}
              disabled={followUps.length === 0}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-ink px-5 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              <Download size={18} />
              Download List
            </button>
          </div>

          <div className="relative mt-5">
            <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search by student, register number, email, or counselor"
              className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-11 pr-4 text-sm text-ink outline-none focus:border-tide"
            />
          </div>
        </div>

        {followUps.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-[980px] w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-700">
                <tr>
                  <th className="px-6 py-4 font-semibold">Student</th>
                  {role === "admin" ? <th className="px-6 py-4 font-semibold">Counselor</th> : null}
                  <th className="px-6 py-4 font-semibold">Risk</th>
                  <th className="px-6 py-4 font-semibold">Status</th>
                  <th className="px-6 py-4 font-semibold">Outcome</th>
                  <th className="px-6 py-4 font-semibold">Next Follow-Up</th>
                </tr>
              </thead>
              <tbody>
                {followUps.map((record) => {
                  const isRescheduling =
                    (record.intervention?.follow_up_outcome === "rescheduled" || record.student_id in rescheduleDates) &&
                    record.intervention?.status !== "resolved";
                  const rescheduleDate = rescheduleDates[record.student_id] ?? record.intervention?.next_follow_up_date ?? "";

                  return (
                  <tr key={record.student_id} className="border-b border-slate-100 bg-white align-top last:border-b-0">
                    <td className="px-6 py-5">
                      <div className="font-semibold text-ink">{record.student_name}</div>
                      <div className="mt-1 text-slate-500">{record.registration_number}</div>
                      <div className="mt-1 text-slate-500">{record.student_email}</div>
                    </td>
                    {role === "admin" ? <td className="px-6 py-5 text-slate-600">{record.counselor_name}</td> : null}
                    <td className="px-6 py-5">
                      <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${riskChipClass(record.latest_risk_level)}`}>
                        {record.latest_risk_level}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold capitalize ${statusChipClass(record.intervention?.status ?? "pending")}`}>
                        {record.intervention?.status === "in_progress" ? "in progress" : record.intervention?.status ?? "pending"}
                      </span>
                    </td>
                    <td className="px-6 py-5 min-w-[220px]">
                      <div className="w-full min-w-[190px] max-w-[260px] space-y-2">
                        <div className="relative">
                        <select
                          value={record.intervention?.follow_up_outcome ?? ""}
                          onChange={(event) => void handleOutcomeChange(record, event.target.value)}
                          disabled={savingStudentId === record.student_id}
                          className="w-full appearance-none rounded-xl border border-slate-300 bg-white px-4 py-2.5 pr-10 text-sm text-ink outline-none transition focus:border-tide disabled:cursor-not-allowed disabled:bg-slate-100"
                        >
                          <option value="">Record outcome</option>
                          <option value="attended">Attended</option>
                          <option value="missed">Missed</option>
                          <option value="rescheduled">Rescheduled</option>
                          <option value="resolved">Resolved</option>
                        </select>
                        <ChevronDown
                          size={16}
                          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
                        />
                        </div>
                        {isRescheduling ? (
                          <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
                            <div className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">New Follow-Up Date</div>
                            <input
                              type="date"
                              value={rescheduleDate}
                              onChange={(event) =>
                                setRescheduleDates((current) => ({
                                  ...current,
                                  [record.student_id]: event.target.value,
                                }))
                              }
                              disabled={savingStudentId === record.student_id}
                              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-ink outline-none transition focus:border-tide disabled:cursor-not-allowed disabled:bg-slate-100"
                            />
                            <button
                              type="button"
                              onClick={() => void handleRescheduleSave(record)}
                              disabled={savingStudentId === record.student_id}
                              className="inline-flex w-full items-center justify-center rounded-xl bg-ink px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                            >
                              {savingStudentId === record.student_id ? "Saving..." : "Save New Date"}
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <div className="font-semibold text-ink">{record.intervention?.next_follow_up_date}</div>
                      {record.intervention?.next_follow_up_date ? (
                        <div className="mt-2">
                          <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${dueChipClass(record.intervention.next_follow_up_date)}`}>
                            {dayLabel(record.intervention.next_follow_up_date)}
                          </span>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                )})}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-8 text-slate-500">No follow-up dates are recorded yet for the current student list.</div>
        )}
      </section>

      {statusMessage ? <div className="rounded-3xl bg-emerald-50 px-5 py-4 text-emerald-700 shadow-soft">{statusMessage}</div> : null}
      {error ? <div className="rounded-3xl bg-red-50 px-5 py-4 text-red-700 shadow-soft">{error}</div> : null}
    </div>
  );
}
