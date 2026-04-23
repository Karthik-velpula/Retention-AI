import { Search, X } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchRecommendations, fetchStudentsPage } from "../api/endpoints";
import { RecommendationsData, StudentListItem } from "../types";

export default function AdvisingPage() {
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [studentId, setStudentId] = useState<number | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationsData | null>(null);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [totalStudents, setTotalStudents] = useState(0);
  const pageSize = 25;

  useEffect(() => {
    fetchStudentsPage({
      page: 1,
      page_size: pageSize,
      query: searchTerm.trim() || undefined,
    })
      .then((response) => {
        setStudents(response.items);
        setTotalStudents(response.total);
        if (!response.items.length) {
          setStudentId(null);
          setRecommendations(null);
          return;
        }
        setStudentId((current) => (current && response.items.some((student) => student.id === current) ? current : null));
      })
      .catch(() => setError("Unable to load students for advising."));
  }, [searchTerm]);

  useEffect(() => {
    if (!studentId) {
      setRecommendations(null);
      return;
    }
    setError("");
    setRecommendations(null);
    fetchRecommendations(studentId)
      .then(setRecommendations)
      .catch(() => setError("Unable to load AI recommendations for the selected student."));
  }, [studentId]);

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-white p-8 shadow-soft">
        <p className="text-xs uppercase tracking-[0.3em] text-tide">AI Advising</p>
        <h1 className="mt-3 font-display text-4xl text-ink">Personalized Academic and Career Guidance</h1>
        <p className="mt-3 text-sm text-slate-500">Showing {students.length} of {totalStudents} matching students for quick advising access.</p>
        <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,380px)_1fr]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search by name, registration number, or email"
              className="w-full rounded-2xl border border-slate-200 py-3 pl-11 pr-4 text-sm text-ink outline-none focus:border-tide"
            />
          </div>
          <div className="flex gap-3">
            <select
              value={studentId ?? ""}
              onChange={(event) => setStudentId(event.target.value ? Number(event.target.value) : null)}
              className="min-w-0 flex-1 rounded-2xl border border-slate-200 px-4 py-3"
            >
              <option value="">
                Select a student
              </option>
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.name} • {student.registration_number}
                </option>
              ))}
            </select>
            {studentId ? (
              <button
                type="button"
                onClick={() => {
                  setStudentId(null);
                  setRecommendations(null);
                  setError("");
                }}
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 hover:text-ink"
                aria-label="Remove selected student"
              >
                <X size={18} />
                <span className="hidden sm:inline">Remove</span>
              </button>
            ) : null}
          </div>
        </div>
      </section>

      {error ? <div className="rounded-3xl bg-red-50 px-5 py-4 text-red-700 shadow-soft">{error}</div> : null}

      {recommendations ? (
        <div className="space-y-6">
          <section className="rounded-[2rem] bg-white p-6 shadow-soft">
            <p className="text-xs uppercase tracking-[0.24em] text-tide">Advising Meeting Plan</p>
            <h2 className="mt-2 font-display text-3xl text-ink">Faculty Counseling Guide</h2>
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              <MeetingPlanCard
                title="What To Discuss First"
                items={[recommendations.meeting_plan.discuss_first]}
                tone="bg-mist"
              />
              <MeetingPlanCard
                title="What Questions Faculty Should Ask"
                items={recommendations.meeting_plan.faculty_questions}
                tone="bg-sand/20"
              />
              <MeetingPlanCard
                title="What Action To Give The Student"
                items={recommendations.meeting_plan.student_actions}
                tone="bg-mint/20"
              />
              <div className="rounded-[2rem] bg-white p-5 shadow-soft ring-1 ring-slate-100">
                <h3 className="font-display text-2xl text-ink">Parent Involvement</h3>
                <div
                  className={`mt-4 inline-flex rounded-full px-4 py-2 text-sm font-semibold ring-1 ring-inset ${
                    recommendations.meeting_plan.parent_involvement_needed
                      ? "bg-red-50 text-red-700 ring-red-200"
                      : "bg-emerald-50 text-emerald-700 ring-emerald-200"
                  }`}
                >
                  {recommendations.meeting_plan.parent_involvement_needed ? "Recommended" : "Not Needed Now"}
                </div>
                <p className="mt-4 text-sm leading-7 text-slate-600">{recommendations.meeting_plan.parent_involvement_reason}</p>
              </div>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-3">
            <RecommendationColumn title="Academic Advising" items={recommendations.academic} tone="bg-white" />
            <RecommendationColumn title="Career Guidance" items={recommendations.career} tone="bg-sand/20" />
            <RecommendationColumn title="Adaptive Learning Pathways" items={recommendations.learning_pathways} tone="bg-mint/20" />
          </section>
        </div>
      ) : (
        <section className="rounded-[2rem] bg-white p-6 shadow-soft text-slate-500">
          Select a student to load personalized advising recommendations.
        </section>
      )}
    </div>
  );
}

function RecommendationColumn({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  return (
    <div className={`rounded-[2rem] p-6 shadow-soft ${tone}`}>
      <h2 className="font-display text-2xl text-ink">{title}</h2>
      <ul className="mt-4 space-y-3 text-slate-700">
        {items.map((item) => (
          <li key={item} className="rounded-2xl bg-white/70 px-4 py-3">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function MeetingPlanCard({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  return (
    <div className={`rounded-[2rem] p-5 shadow-soft ${tone}`}>
      <h3 className="font-display text-2xl text-ink">{title}</h3>
      <ul className="mt-4 space-y-3 text-slate-700">
        {items.map((item) => (
          <li key={item} className="rounded-2xl bg-white/80 px-4 py-3">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
