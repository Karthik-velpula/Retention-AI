import RiskBadge from "./RiskBadge";
import { PredictionResult, StudentListItem } from "../types";

export default function StudentTable({
  students,
  selectedStudentId,
  onSelect,
  latestPrediction
}: {
  students: StudentListItem[];
  selectedStudentId: number | null;
  onSelect: (studentId: number) => void;
  latestPrediction: PredictionResult | null;
}) {
  return (
    <div className="rounded-[2rem] bg-white shadow-soft">
      <div className="space-y-3 p-3 md:hidden">
        {students.map((student) => (
          <button
            key={student.id}
            type="button"
            onClick={() => onSelect(student.id)}
            className={`w-full rounded-[1.5rem] border px-4 py-4 text-left transition ${
              selectedStudentId === student.id
                ? "border-tide bg-mist"
                : "border-slate-200 bg-white hover:border-slate-300"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-base font-semibold text-ink">{student.name}</p>
                <p className="truncate text-sm text-slate-500">{student.email}</p>
                <p className="mt-1 text-sm text-slate-500">{student.registration_number}</p>
              </div>
              <div>
                {selectedStudentId === student.id && latestPrediction ? (
                  <RiskBadge level={latestPrediction.risk_level} />
                ) : student.latest_risk_level ? (
                  <RiskBadge level={student.latest_risk_level} />
                ) : (
                  <span className="text-slate-400">Not scored</span>
                )}
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-2xl bg-slate-50 px-3 py-2">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">GPA</p>
                <p className="mt-1 font-semibold text-ink">{student.gpa.toFixed(2)}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-3 py-2">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Attendance</p>
                <p className="mt-1 font-semibold text-ink">{student.attendance.toFixed(0)}%</p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-3 py-2">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">LMS</p>
                <p className="mt-1 font-semibold text-ink">{student.lms_activity_percentage.toFixed(0)}%</p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-3 py-2">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Fees</p>
                <p className="mt-1 font-semibold text-ink">{student.fees_paid_status}</p>
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="hidden overflow-x-auto md:block">
        <table className="min-w-[900px] w-full table-fixed text-left text-sm">
          <colgroup>
            <col className="w-[34%]" />
            <col className="w-[15%]" />
            <col className="w-[10%]" />
            <col className="w-[11%]" />
            <col className="w-[9%]" />
            <col className="w-[9%]" />
            <col className="w-[12%]" />
          </colgroup>
          <thead className="bg-ink text-white">
            <tr>
              <th className="px-5 py-4 font-medium">Student</th>
              <th className="px-5 py-4 font-medium">Reg No</th>
              <th className="px-5 py-4 font-medium">GPA</th>
              <th className="px-5 py-4 font-medium">Attendance</th>
              <th className="px-5 py-4 font-medium">LMS %</th>
              <th className="px-5 py-4 font-medium">Fees</th>
              <th className="px-5 py-4 font-medium">Risk</th>
            </tr>
          </thead>
          <tbody>
            {students.map((student) => (
              <tr
                key={student.id}
                onClick={() => onSelect(student.id)}
                className={`cursor-pointer border-b border-slate-100 transition hover:bg-mist ${
                  selectedStudentId === student.id ? "bg-mist" : "bg-white"
                }`}
              >
                <td className="px-5 py-4 align-top">
                  <div className="space-y-1">
                    <p className="truncate font-semibold text-ink">{student.name}</p>
                    <p className="truncate text-slate-500">{student.email}</p>
                  </div>
                </td>
                <td className="px-5 py-4 align-top font-medium text-ink">{student.registration_number}</td>
                <td className="px-5 py-4 align-top">{student.gpa.toFixed(2)}</td>
                <td className="px-5 py-4 align-top">{student.attendance.toFixed(0)}%</td>
                <td className="px-5 py-4 align-top">{student.lms_activity_percentage.toFixed(0)}%</td>
                <td className="px-5 py-4 align-top">{student.fees_paid_status}</td>
                <td className="px-5 py-4 align-top">
                  {selectedStudentId === student.id && latestPrediction ? (
                    <RiskBadge level={latestPrediction.risk_level} />
                  ) : student.latest_risk_level ? (
                    <RiskBadge level={student.latest_risk_level} />
                  ) : (
                    <span className="text-slate-400">Not scored</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
