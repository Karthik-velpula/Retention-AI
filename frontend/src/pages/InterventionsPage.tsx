import { CalendarClock, ChevronRight, CircleAlert, ClipboardList, Save, Search, Sparkles, UserRoundCheck } from "lucide-react";
import { useEffect, useMemo, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";

import { fetchInterventionAssist, fetchInterventions, saveIntervention } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";
import { FollowUpOutcome, InterventionRecord, InterventionStatus, InterventionStudentOverview } from "../types";

type InterventionDraft = {
  contacted_student: boolean;
  parent_informed: boolean;
  counselor_assigned: boolean;
  fee_issue_escalated: boolean;
  next_follow_up_date: string;
  follow_up_outcome: FollowUpOutcome | null;
  status: InterventionStatus;
  notes: string;
};

const emptyRecord: InterventionDraft = {
  contacted_student: false,
  parent_informed: false,
  counselor_assigned: false,
  fee_issue_escalated: false,
  next_follow_up_date: "",
  follow_up_outcome: null,
  status: "pending" as InterventionStatus,
  notes: "",
};

export default function InterventionsPage() {
  const { role } = useAuth();
  const [records, setRecords] = useState<InterventionStudentOverview[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const [historyStudentId, setHistoryStudentId] = useState<number | null>(null);
  const [draft, setDraft] = useState<InterventionDraft>({ ...emptyRecord });
  const [searchTerm, setSearchTerm] = useState("");
  const [historySearchTerm, setHistorySearchTerm] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isGeneratingAssist, setIsGeneratingAssist] = useState(false);
  const [assistMessage, setAssistMessage] = useState("");

  useEffect(() => {
    fetchInterventions()
      .then((response) => {
        setRecords(response);
        if (response.length > 0) {
          setSelectedStudentId(response[0].student_id);
        }
      })
      .catch(() => setError("Unable to load intervention records."));
  }, []);

  const filteredRecords = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return records;
    return records.filter((record) =>
      [record.student_name, record.student_email, record.registration_number, record.counselor_name]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(query))
    );
  }, [records, searchTerm]);

  useEffect(() => {
    if (filteredRecords.length === 0) {
      setSelectedStudentId(null);
      setHistoryStudentId(null);
      setDraft({ ...emptyRecord });
      setAssistMessage("");
      return;
    }

    const selected = filteredRecords.find((item) => item.student_id === selectedStudentId);
    const activeRecord = selected ?? filteredRecords[0];
    if (activeRecord.student_id !== selectedStudentId) {
      setSelectedStudentId(activeRecord.student_id);
    }
    if (historyStudentId && !filteredRecords.some((item) => item.student_id === historyStudentId)) {
      setHistoryStudentId(null);
    }
    hydrateDraft(activeRecord.intervention, setDraft);
    setAssistMessage("");
  }, [filteredRecords, historyStudentId, selectedStudentId]);

  const selectedRecord = filteredRecords.find((item) => item.student_id === selectedStudentId) ?? null;
  const selectedHistoryRecord = filteredRecords.find((item) => item.student_id === historyStudentId) ?? null;
  const historyRecords = useMemo(() => (selectedHistoryRecord ? [selectedHistoryRecord] : filteredRecords), [filteredRecords, selectedHistoryRecord]);
  const filteredHistory = useMemo(() => {
    const query = historySearchTerm.trim().toLowerCase();
    return historyRecords
      .flatMap((record) =>
        record.history.map((entry) => ({
          entry,
          student: record,
        }))
      )
      .filter(({ entry, student }) => {
        if (!query) return true;
        return [
          student.student_name,
          student.registration_number,
          entry.changed_by,
          entry.changed_fields,
          entry.change_summary,
        ]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));
      });
  }, [historyRecords, historySearchTerm]);

  const updateDraftWithGeneratedNotes = (
    updater: (current: InterventionDraft) => InterventionDraft
  ) => {
    if (!selectedRecord) return;
    setDraft((current) => {
      const nextDraft = updater(current);
      return {
        ...nextDraft,
        notes: buildInterventionNotes(selectedRecord, nextDraft, role),
      };
    });
  };

  const handleSave = async () => {
    if (!selectedRecord) return;
    try {
      setIsSaving(true);
      setError("");
      setStatusMessage("");
      const saved = await saveIntervention(selectedRecord.student_id, {
        ...draft,
        next_follow_up_date: draft.next_follow_up_date || null,
        follow_up_outcome: draft.follow_up_outcome,
      });
      setRecords((current) =>
        current.map((item) =>
          item.student_id === selectedRecord.student_id
            ? {
                ...item,
                intervention: saved.intervention,
                history: saved.history_entry ? [saved.history_entry, ...item.history] : item.history,
              }
            : item
        )
      );
      setStatusMessage(`Intervention saved for ${selectedRecord.student_name}. ${saved.email_detail}`);
    } catch {
      setError("Unable to save the intervention record.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleAIAssist = async () => {
    if (!selectedRecord) return;
    try {
      setIsGeneratingAssist(true);
      setError("");
      const response = await fetchInterventionAssist(selectedRecord.student_id, {
        contacted_student: draft.contacted_student,
        parent_informed: draft.parent_informed,
        counselor_assigned: draft.counselor_assigned,
        fee_issue_escalated: draft.fee_issue_escalated,
        status: draft.status,
      });
      setDraft((current) => ({
        ...current,
        parent_informed: response.suggest_parent_informed,
        next_follow_up_date: response.recommended_follow_up_date ?? "",
        notes: response.suggested_note,
      }));
      setAssistMessage(response.parent_informed_reason);
    } catch {
      setError("Unable to generate AI assist suggestions.");
    } finally {
      setIsGeneratingAssist(false);
    }
  };

  useEffect(() => {
    if (draft.status === "resolved" && draft.next_follow_up_date) {
      setDraft((current) => ({
        ...current,
        next_follow_up_date: "",
      }));
    }
  }, [draft.status, draft.next_follow_up_date]);

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[2.25rem] bg-[linear-gradient(135deg,#f6fbff_0%,#edf4fb_55%,#e4eef8_100%)] shadow-soft">
        <div className="grid gap-6 p-8 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-tide">Follow-up Actions</p>
            <h1 className="mt-3 font-display text-4xl text-ink">Interventions</h1>
            <p className="mt-4 max-w-2xl text-[15px] leading-7 text-slate-600">
              Work through intervention cases with a cleaner case-management flow: open the student, log the actions taken,
              capture next steps, and keep the record ready for review.
              {role === "admin" ? " DEO can also confirm counselor assignment when a case needs formal ownership." : ""}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            <SummaryStatCard
              icon={ClipboardList}
              label="Cases In View"
              value={String(filteredRecords.length)}
              helper="Medium and high-risk students ready for action"
            />
            <SummaryStatCard
              icon={CalendarClock}
              label="Needs Follow-Up"
              value={String(records.filter((record) => record.intervention?.status !== "resolved" && record.intervention?.next_follow_up_date).length)}
              helper="Students already carrying a planned review date"
            />
            <SummaryStatCard
              icon={UserRoundCheck}
              label="Resolved"
              value={String(records.filter((record) => record.intervention?.status === "resolved").length)}
              helper="Cases marked closed by faculty or DEO"
            />
          </div>
        </div>
      </section>

      <div className="overflow-x-auto">
        <section className="grid min-w-[1100px] gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="rounded-[2.1rem] bg-white p-5 shadow-soft xl:sticky xl:top-6 xl:self-start">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-tide">Student Queue</p>
              <h2 className="mt-2 text-2xl font-semibold text-ink">Open a Case</h2>
              <p className="mt-1 text-sm text-slate-500">Select one student to work on at a time.</p>
            </div>
            <div className="rounded-2xl bg-mist px-4 py-3 text-right">
              <div className="text-xs uppercase tracking-[0.22em] text-tide">Visible</div>
              <div className="mt-1 text-2xl font-semibold text-ink">{filteredRecords.length}</div>
            </div>
          </div>

          <div className="relative mt-5">
            <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search by student, register number, email, or counselor"
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 py-3 pl-11 pr-4 text-sm text-ink outline-none transition focus:border-tide focus:bg-white"
            />
          </div>

          <div className="mt-5 max-h-[calc(100vh-18rem)] space-y-2 overflow-y-auto pr-1">
            {filteredRecords.length > 0 ? (
              filteredRecords.map((record) => {
                const isSelected = selectedStudentId === record.student_id;
                return (
                  <button
                    key={record.student_id}
                    type="button"
                    onClick={() => {
                      setSelectedStudentId(record.student_id);
                      setHistoryStudentId(record.student_id);
                      hydrateDraft(record.intervention, setDraft);
                      setHistorySearchTerm("");
                    }}
                    className={`w-full rounded-[1.5rem] border px-4 py-4 text-left transition ${
                      isSelected
                        ? "border-transparent bg-ink text-white shadow-lg shadow-slate-300/50"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className={`truncate font-semibold ${isSelected ? "text-white" : "text-ink"}`}>{record.student_name}</div>
                        <div className={`mt-1 text-sm ${isSelected ? "text-white/70" : "text-slate-500"}`}>{record.registration_number}</div>
                        <div className={`mt-1 truncate text-xs ${isSelected ? "text-white/55" : "text-slate-400"}`}>{record.student_email}</div>
                      </div>
                      <ChevronRight size={18} className={isSelected ? "text-white/70" : "text-slate-400"} />
                    </div>

                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <RiskBadge risk={record.latest_risk_level} inverted={isSelected} />
                      <StatusBadge status={record.intervention?.status ?? "pending"} inverted={isSelected} />
                    </div>

                    {role === "admin" ? (
                      <div className={`mt-3 text-sm ${isSelected ? "text-white/72" : "text-slate-500"}`}>
                        Counselor: {record.counselor_name || "Unassigned"}
                      </div>
                    ) : null}
                  </button>
                );
              })
            ) : (
              <div className="rounded-[1.5rem] border border-dashed border-slate-300 px-5 py-8 text-center text-sm text-slate-500">
                No students match the current search.
              </div>
            )}
          </div>
          </aside>

        <section className="space-y-4">
          {selectedRecord ? (
            <>
              <section className="overflow-hidden rounded-[2.1rem] bg-white shadow-soft">
                <div className="grid gap-0 lg:grid-cols-[1.15fr_0.85fr]">
                  <div className="p-7">
                    <p className="text-xs uppercase tracking-[0.24em] text-tide">Selected Student</p>
                    <h2 className="mt-3 font-display text-3xl text-ink">{selectedRecord.student_name}</h2>
                    <p className="mt-2 text-slate-600">
                      {selectedRecord.registration_number} · {selectedRecord.student_email}
                    </p>
                    {role === "admin" ? (
                      <p className="mt-1 text-slate-500">Counselor: {selectedRecord.counselor_name || "Unassigned"}</p>
                    ) : null}

                    <div className="mt-6 flex flex-wrap items-center gap-2">
                      <RiskBadge risk={selectedRecord.latest_risk_level} />
                      <StatusBadge status={draft.status} />
                    </div>

                    <div className="mt-6 grid gap-3 sm:grid-cols-3">
                      <QuickInfoCard label="Current Risk" value={selectedRecord.latest_risk_level} helper="Latest case risk band" />
                      <QuickInfoCard
                        label="Last Updated By"
                        value={selectedRecord.intervention?.updated_by ?? "No update yet"}
                        helper="Most recent intervention owner"
                      />
                      <QuickInfoCard
                        label="Resolution"
                        value={
                          selectedRecord.intervention?.resolved_at
                            ? new Date(selectedRecord.intervention.resolved_at).toLocaleString("en-IN", {
                                dateStyle: "medium",
                                timeStyle: "short",
                              })
                            : "Open"
                        }
                        helper={selectedRecord.intervention?.resolved_at ? "Case closed timestamp" : "Still active"}
                      />
                    </div>
                  </div>

                  <div className="bg-[linear-gradient(180deg,#edf5ff_0%,#f8fbff_100%)] p-7 lg:border-l lg:border-slate-100">
                    <p className="text-xs uppercase tracking-[0.24em] text-tide">Case Workspace</p>
                    <h3 className="mt-2 text-2xl font-semibold text-ink">What happened here?</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      Update the intervention checklist, set the case status, and keep a concise note for future review.
                    </p>

                    <div className="mt-6 space-y-3">
                      <FieldCard label="Status" compact>
                        <select
                          value={draft.status}
                          onChange={(event) =>
                            updateDraftWithGeneratedNotes((current) => ({
                              ...current,
                              status: event.target.value as InterventionStatus,
                            }))
                          }
                          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 transition"
                        >
                          <option value="pending">pending</option>
                          <option value="in_progress">in progress</option>
                          <option value="resolved">resolved</option>
                        </select>
                      </FieldCard>

                      <FieldCard label="Next Follow-up Date" compact helper={draft.status === "resolved" ? "Disabled because the case is resolved." : "Choose the next planned review date."}>
                        <input
                          type="date"
                          value={draft.next_follow_up_date}
                          onChange={(event) => updateDraftWithGeneratedNotes((current) => ({ ...current, next_follow_up_date: event.target.value }))}
                          disabled={draft.status === "resolved"}
                          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 transition disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                        />
                      </FieldCard>
                    </div>
                  </div>
                </div>
              </section>

              <section className="space-y-4">
                <div className="grid gap-4 xl:grid-cols-[1.02fr_0.98fr]">
                  <section className="rounded-[2.1rem] bg-white p-6 shadow-soft">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.24em] text-tide">Action Checklist</p>
                        <h3 className="mt-2 text-2xl font-semibold text-ink">Intervention Actions</h3>
                      </div>
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-2">
                      <ToggleCard
                        label="Contacted Student"
                        description="Record direct outreach to the student."
                        checked={draft.contacted_student}
                        onChange={(checked) => updateDraftWithGeneratedNotes((current) => ({ ...current, contacted_student: checked }))}
                      />
                      <ToggleCard
                        label="Parent Informed"
                        description="Capture whether the family was contacted."
                        checked={draft.parent_informed}
                        onChange={(checked) => updateDraftWithGeneratedNotes((current) => ({ ...current, parent_informed: checked }))}
                      />
                      {role === "admin" ? (
                        <ToggleCard
                          label="Counselor Assigned"
                          description="Track if a counselor assignment is confirmed."
                          checked={draft.counselor_assigned}
                          onChange={(checked) => updateDraftWithGeneratedNotes((current) => ({ ...current, counselor_assigned: checked }))}
                        />
                      ) : null}
                      <ToggleCard
                        label="Fee Issue Escalated"
                        description="Mark when the financial concern is raised to admin."
                        checked={draft.fee_issue_escalated}
                        onChange={(checked) => updateDraftWithGeneratedNotes((current) => ({ ...current, fee_issue_escalated: checked }))}
                      />
                    </div>
                  </section>

                  <section className="rounded-[2.1rem] bg-white p-6 shadow-soft">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.24em] text-tide">Narrative</p>
                        <h3 className="mt-2 text-2xl font-semibold text-ink">Notes and AI Assist</h3>
                      </div>
                      <button
                        type="button"
                        onClick={handleAIAssist}
                        disabled={isGeneratingAssist}
                        className="inline-flex items-center gap-2 rounded-2xl border border-tide/30 bg-mist px-4 py-2 text-sm font-semibold text-ink transition hover:bg-[#dfe8f0] disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <Sparkles size={16} />
                        {isGeneratingAssist ? "Generating AI Assist..." : "AI Assist"}
                      </button>
                    </div>

                    {assistMessage ? (
                      <div className="mt-4 flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                        <CircleAlert size={18} className="mt-0.5 shrink-0" />
                        <span>{assistMessage}</span>
                      </div>
                    ) : null}

                    <textarea
                      value={draft.notes}
                      onChange={(event) => setDraft((current) => ({ ...current, notes: event.target.value }))}
                      rows={8}
                      placeholder="Record follow-up notes, commitments, or escalation details. Use AI Assist to draft this automatically."
                      className="mt-4 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 transition outline-none focus:border-tide focus:bg-white"
                    />
                  </section>
                </div>

                <section className="rounded-[2.1rem] bg-white p-6 shadow-soft">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.24em] text-tide">Save Changes</p>
                      <h3 className="mt-2 text-2xl font-semibold text-ink">Commit This Update</h3>
                      <div className="mt-2 text-sm text-slate-500">
                        <div>Last updated by {selectedRecord.intervention?.updated_by ?? "no one yet"}</div>
                        {selectedRecord.intervention?.resolved_at ? (
                          <div>
                            Resolved on{" "}
                            {new Date(selectedRecord.intervention.resolved_at).toLocaleString("en-IN", {
                              dateStyle: "medium",
                              timeStyle: "short",
                            })}
                          </div>
                        ) : (
                          <div>Save this record to log the latest intervention state.</div>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={handleSave}
                      disabled={isSaving}
                      className="inline-flex items-center gap-2 rounded-2xl bg-ink px-5 py-3 font-semibold text-white transition hover:bg-slate-900 disabled:cursor-not-allowed disabled:bg-slate-300"
                    >
                      <Save size={18} />
                      {isSaving ? "Saving..." : "Save Intervention"}
                    </button>
                  </div>
                </section>
              </section>

              <section className="rounded-[2.1rem] bg-white p-6 shadow-soft">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-tide">Audit Trail</p>
                    <h3 className="mt-2 text-2xl font-semibold text-ink">
                      {selectedHistoryRecord ? `${selectedHistoryRecord.student_name}'s Intervention History` : "Intervention History"}
                    </h3>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    {selectedHistoryRecord ? (
                      <button
                        type="button"
                        onClick={() => {
                          setHistoryStudentId(null);
                          setHistorySearchTerm("");
                        }}
                        className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                      >
                        <ChevronRight size={16} className="rotate-180" />
                        Show All History
                      </button>
                    ) : null}
                    <div className="rounded-2xl bg-slate-50 px-4 py-2 text-sm text-slate-500">
                      {filteredHistory.length} {filteredHistory.length === 1 ? "entry" : "entries"}
                    </div>
                  </div>
                </div>

                <div className="relative mt-5">
                  <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    value={historySearchTerm}
                    onChange={(event) => setHistorySearchTerm(event.target.value)}
                    placeholder="Search history by updater or change details"
                    className="w-full rounded-2xl border border-slate-200 bg-slate-50 py-3 pl-11 pr-4 text-sm text-ink outline-none transition focus:border-tide focus:bg-white"
                  />
                </div>
                <div className="mt-4 space-y-3">
                  {filteredHistory.length > 0 ? (
                    filteredHistory.map(({ entry, student }) => (
                      <div key={`${student.student_id}-${entry.id}`} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                        {!selectedHistoryRecord ? (
                          <div className="mb-3 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
                            <div>
                              <div className="font-semibold text-ink">{student.student_name}</div>
                              <div className="mt-1 text-sm text-slate-500">{student.registration_number}</div>
                            </div>
                            <RiskBadge risk={student.latest_risk_level} />
                          </div>
                        ) : null}
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div className="font-semibold text-ink">{entry.changed_by}</div>
                          <div className="text-sm text-slate-500">
                            {new Date(entry.created_at).toLocaleString("en-IN", {
                              dateStyle: "medium",
                              timeStyle: "short",
                            })}
                          </div>
                        </div>
                        <div className="mt-2 text-sm font-medium text-slate-600">Changed: {entry.changed_fields}</div>
                        <div className="mt-2 text-sm text-slate-600">{entry.change_summary}</div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                      {historyRecords.some((record) => record.history.length > 0)
                        ? "No intervention history entries match the current search."
                        : "No intervention history recorded yet."}
                    </div>
                  )}
                </div>
              </section>
            </>
          ) : (
            <section className="rounded-[2rem] bg-white p-8 text-slate-500 shadow-soft">
              Select a student to record intervention details.
            </section>
          )}
        </section>
        </section>
      </div>

      {statusMessage ? <div className="rounded-3xl bg-mist px-5 py-4 text-ink shadow-soft">{statusMessage}</div> : null}
      {error ? <div className="rounded-3xl bg-red-50 px-5 py-4 text-red-700 shadow-soft">{error}</div> : null}
    </div>
  );
}

function hydrateDraft(
  intervention: InterventionRecord | null,
  setDraft: Dispatch<
    SetStateAction<InterventionDraft>
  >
) {
  setDraft(
    intervention
      ? {
          contacted_student: intervention.contacted_student,
          parent_informed: intervention.parent_informed,
          counselor_assigned: intervention.counselor_assigned,
          fee_issue_escalated: intervention.fee_issue_escalated,
          next_follow_up_date: intervention.next_follow_up_date ?? "",
          follow_up_outcome: intervention.follow_up_outcome ?? null,
          status: intervention.status,
          notes: intervention.notes,
        }
      : { ...emptyRecord }
  );
}

function buildInterventionNotes(
  selectedRecord: InterventionStudentOverview,
  draft: InterventionDraft,
  role: "admin" | "faculty" | null
) {
  const actions: string[] = [];
  if (draft.contacted_student) actions.push("student contacted");
  if (draft.parent_informed) actions.push("parent informed");
  if (role === "admin" && draft.counselor_assigned) actions.push("counselor assignment confirmed");
  if (draft.fee_issue_escalated) actions.push("fee issue escalated");

  const summary =
    actions.length > 0 ? `${actions[0].charAt(0).toUpperCase()}${actions[0].slice(1)}${actions.length > 1 ? `, ${actions.slice(1).join(", ")}` : ""}.` : "Intervention review started.";

  const followUp = draft.status !== "resolved" && draft.next_follow_up_date
    ? ` Next follow-up scheduled for ${new Date(draft.next_follow_up_date).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      })}.`
    : "";

  const statusText =
    draft.status === "resolved"
      ? " Case marked as resolved."
      : draft.status === "in_progress"
        ? " Case is currently in progress."
        : " Case is pending further action.";

  return `${selectedRecord.latest_risk_level} risk intervention note for ${selectedRecord.student_name}. ${summary}${followUp}${statusText}`.trim();
}

function ToggleCard({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 transition hover:border-slate-300 hover:bg-white">
      <div>
        <div className="font-medium text-ink">{label}</div>
        <div className="mt-1 text-sm text-slate-500">{description}</div>
      </div>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="mt-1 h-5 w-5 shrink-0" />
    </label>
  );
}

function SummaryStatCard({
  icon: Icon,
  label,
  value,
  helper,
}: {
  icon: typeof ClipboardList;
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-[1.5rem] border border-white/60 bg-white/70 px-4 py-4 backdrop-blur-sm">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs uppercase tracking-[0.22em] text-tide">{label}</span>
        <Icon size={18} className="text-tide" />
      </div>
      <div className="mt-3 text-3xl font-semibold text-ink">{value}</div>
      <div className="mt-1 text-sm text-slate-500">{helper}</div>
    </div>
  );
}

function QuickInfoCard({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-4">
      <div className="text-xs uppercase tracking-[0.22em] text-tide">{label}</div>
      <div className="mt-2 text-lg font-semibold text-ink">{value}</div>
      <div className="mt-1 text-sm text-slate-500">{helper}</div>
    </div>
  );
}

function FieldCard({
  label,
  helper,
  compact = false,
  children,
}: {
  label: string;
  helper?: string;
  compact?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={`rounded-[1.5rem] border border-slate-200 bg-white ${compact ? "px-4 py-4" : "px-5 py-5"}`}>
      <div className="text-sm font-medium text-slate-600">{label}</div>
      {helper ? <div className="mt-1 text-xs text-slate-500">{helper}</div> : null}
      <div className="mt-3">{children}</div>
    </div>
  );
}

function RiskBadge({ risk, inverted = false }: { risk: string; inverted?: boolean }) {
  const styles = inverted
    ? risk === "High"
      ? "bg-red-500/18 text-red-100 ring-1 ring-red-300/20"
      : risk === "Medium"
        ? "bg-amber-400/18 text-amber-100 ring-1 ring-amber-200/20"
        : risk === "Low"
          ? "bg-lime-400/18 text-lime-100 ring-1 ring-lime-200/20"
          : "bg-emerald-400/18 text-emerald-100 ring-1 ring-emerald-200/20"
    : risk === "High"
      ? "bg-red-100 text-red-700"
      : risk === "Medium"
        ? "bg-amber-100 text-amber-700"
        : risk === "Low"
          ? "bg-lime-100 text-lime-700"
          : "bg-emerald-100 text-emerald-700";

  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${styles}`}>{risk}</span>;
}

function StatusBadge({ status, inverted = false }: { status: InterventionStatus | string; inverted?: boolean }) {
  const styles = inverted
    ? status === "resolved"
      ? "bg-emerald-500/18 text-emerald-100 ring-1 ring-emerald-200/20"
      : status === "in_progress"
        ? "bg-sky-400/18 text-sky-100 ring-1 ring-sky-200/20"
        : "bg-white/12 text-white/86 ring-1 ring-white/10"
    : status === "resolved"
      ? "bg-emerald-100 text-emerald-700"
      : status === "in_progress"
        ? "bg-sky-100 text-sky-700"
        : "bg-slate-200 text-slate-700";

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${styles}`}>
      {status === "in_progress" ? "in progress" : status}
    </span>
  );
}
