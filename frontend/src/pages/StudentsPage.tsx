import { ArrowLeft, BrainCircuit, ChevronDown, Download, MessageCircle, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { useSearchParams } from "react-router-dom";

import { downloadParentReport, fetchStudent, fetchStudentsPage, predictRisk } from "../api/endpoints";
import PredictionPanel from "../components/PredictionPanel";
import StudentTable from "../components/StudentTable";
import { useAuth } from "../context/AuthContext";
import { PredictionResult, StudentDetail, StudentListItem } from "../types";

export default function StudentsPage() {
  const { role } = useAuth();
  const [searchParams] = useSearchParams();
  const requestedRegNo = searchParams.get("regNo")?.trim() ?? "";
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const [selectedStudent, setSelectedStudent] = useState<StudentDetail | null>(null);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [error, setError] = useState("");
  const [isPredicting, setIsPredicting] = useState(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [isPreparingWhatsApp, setIsPreparingWhatsApp] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [sectionFilter, setSectionFilter] = useState("All");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalStudents, setTotalStudents] = useState(0);
  const [showSubjectAttendance, setShowSubjectAttendance] = useState(false);
  const predictionSectionRef = useRef<HTMLDivElement | null>(null);
  const subjectAttendanceRef = useRef<HTMLDivElement | null>(null);
  const pageSize = 25;

  useEffect(() => {
    if (requestedRegNo) {
      setSearchTerm(requestedRegNo);
      setCurrentPage(1);
    }
  }, [requestedRegNo]);

  useEffect(() => {
    if (requestedRegNo) {
      fetchStudentsPage({
        page: currentPage,
        page_size: pageSize,
        query: searchTerm.trim() || undefined,
        section: role === "admin" && sectionFilter !== "All" ? sectionFilter : undefined,
      })
        .then((response) => {
          setStudents(response.items);
          setTotalStudents(response.total);
          const exactMatch = response.items.find(
            (student) => student.registration_number.trim().toLowerCase() === requestedRegNo.toLowerCase()
          );
          if (exactMatch) {
            setSelectedStudentId(exactMatch.id);
            window.requestAnimationFrame(() => {
              predictionSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            });
          } else if (selectedStudentId && !response.items.some((student) => student.id === selectedStudentId)) {
            setSelectedStudentId(null);
          }
        })
        .catch(() => setError("Unable to load students. Check backend authentication and API status."));
      return;
    }

    fetchStudentsPage({
      page: currentPage,
      page_size: pageSize,
      query: searchTerm.trim() || undefined,
      section: role === "admin" && sectionFilter !== "All" ? sectionFilter : undefined,
    })
      .then((response) => {
        setStudents(response.items);
        setTotalStudents(response.total);
        if (selectedStudentId && !response.items.some((student) => student.id === selectedStudentId)) {
          setSelectedStudentId(null);
        }
      })
      .catch(() => setError("Unable to load students. Check backend authentication and API status."));
  }, [currentPage, requestedRegNo, role, searchTerm, sectionFilter, selectedStudentId]);

  const totalPages = Math.max(1, Math.ceil(totalStudents / pageSize));

  useEffect(() => {
    setCurrentPage(1);
  }, [role, searchTerm, sectionFilter]);

  const sectionOptions = useMemo(() => {
    const detectedSections = new Set(
      students.map((student) => student.section?.trim()).filter(Boolean) as string[]
    );
    for (let section = 1; section <= 19; section += 1) {
      detectedSections.add(String(section));
    }
    return Array.from(detectedSections).sort((a, b) => Number(a) - Number(b));
  }, [students]);

  const hasInternalMarks = (item: StudentDetail["subject_attendance"][number]) =>
    item.total_marks > 0 ||
    item.pre_t1_marks > 0 ||
    item.t1_marks > 0 ||
    item.t2_marks > 0 ||
    item.t3_marks > 0 ||
    item.t4_marks > 0 ||
    item.t5_marks > 0;

  const subjectInternalMarks = useMemo(() => {
    if (!selectedStudent) return [];
    const filledSubjects = selectedStudent.subject_attendance.filter(hasInternalMarks);
    const emptySubjects = selectedStudent.subject_attendance.filter((item) => !hasInternalMarks(item));
    return [...filledSubjects, ...emptySubjects];
  }, [selectedStudent]);

  const formatMark = (value: number) => value.toFixed(2).replace(/\.00$/, "");
  const EMPTY_MARK = "-";
  const displayMark = (value: number) => (value > 0 ? formatMark(value) : EMPTY_MARK);
  const isT5OnlySubject = (subjectName: string) => ["22CS958 CLSA", "22TP302 QALR"].includes(subjectName);
  const t5Assignments = (item: StudentDetail["subject_attendance"][number]) => [
    item.t5_assignment_1,
    item.t5_assignment_2,
    item.t5_assignment_3,
    item.t5_assignment_4,
  ];

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  useEffect(() => {
    if (!selectedStudentId) {
      setSelectedStudent(null);
      setPrediction(null);
      setShowSubjectAttendance(false);
      return;
    }
    if (!selectedStudentId) return;
    setError("");
    fetchStudent(selectedStudentId)
      .then((student) => {
        setSelectedStudent(student);
        setShowSubjectAttendance(false);
        const overview = students.find((item) => item.id === selectedStudentId) ?? null;
        setPrediction(buildFallbackPrediction(student, overview));
      })
      .catch(() => setError("Unable to load student details."));
  }, [selectedStudentId, students]);

  const handleRunPrediction = async () => {
    if (!selectedStudent || !selectedStudentId) return;
    await runPredictionForStudent(selectedStudent, selectedStudentId);
  };

  const handleSelectStudent = (studentId: number) => {
    setSelectedStudentId(studentId);
    window.requestAnimationFrame(() => {
      predictionSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const handleBackToList = () => {
    setSelectedStudentId(null);
    setSelectedStudent(null);
    setPrediction(null);
    setShowSubjectAttendance(false);
  };

  const handleAttendanceToggle = () => {
    setShowSubjectAttendance((current) => {
      const next = !current;
      if (!current) {
        window.requestAnimationFrame(() => {
          subjectAttendanceRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      }
      return next;
    });
  };

  const handleGenerateParentReport = async () => {
    if (!selectedStudent || !selectedStudentId) return;

    try {
      setError("");
      setIsGeneratingReport(true);
      await downloadParentReport(selectedStudentId, selectedStudent.name);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(`Unable to generate parent report: ${String(err.response.data.detail)}`);
      } else {
        setError("Unable to generate parent report. Confirm the backend is running and try again.");
      }
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const buildWhatsAppMessage = (target: "parent" | "student") => {
      if (!selectedStudent) return "";

      try {
      const attendanceLines = selectedStudent.subject_attendance.length
        ? selectedStudent.subject_attendance.map(
            (item) => `- ${item.subject_name}: ${item.attendance_percentage.toFixed(0)}%`
          )
        : ["- Subject-wise attendance is not available."];

      const recommendationLines =
        prediction?.recommendations?.length
          ? prediction.recommendations.map((item) => `- ${item}`)
          : ["- AI recommendations are not available right now."];

      if (target === "parent") {
        return [
          "Dear Parent,",
          "",
          `This message is to share the latest academic update for your child ${selectedStudent.name} (${selectedStudent.registration_number}).`,
          `Counselor: ${selectedStudent.counselor_name || "Unassigned"}`,
          `Section: ${selectedStudent.section || "-"}`,
          "",
          "Current Summary:",
          `- CGPA: ${selectedStudent.gpa.toFixed(2)}`,
          `- Overall Attendance: ${selectedStudent.attendance.toFixed(0)}%`,
          `- LMS Activity: ${selectedStudent.lms_activity.assignment_submission_rate.toFixed(0)}%`,
          `- Fee Status: ${
            selectedStudent.financial.fee_due <= 0 && selectedStudent.financial.payment_delay_days <= 0
              ? "Paid"
              : "Not Paid"
          }`,
          `- Risk Level: ${prediction?.risk_level ?? selectedStudent.latest_risk_level ?? "Low"}`,
          "",
          "Subject-wise Attendance:",
          ...attendanceLines,
          "",
          "AI Recommendations:",
          ...recommendationLines,
          "",
          "Please review this update and contact the counselor if any follow-up support is needed.",
          "",
          "Regards,",
          "Student Retention Support Team",
        ].join("\n");
      }

      return [
        `Hello ${selectedStudent.name},`,
        "",
        "Here is your latest academic update from the student retention system.",
        "",
        `Reg No: ${selectedStudent.registration_number}`,
        `Section: ${selectedStudent.section || "-"}`,
        `Counselor: ${selectedStudent.counselor_name || "Unassigned"}`,
        "",
        `CGPA: ${selectedStudent.gpa.toFixed(2)}`,
        `Attendance: ${selectedStudent.attendance.toFixed(0)}%`,
        `LMS Activity: ${selectedStudent.lms_activity.assignment_submission_rate.toFixed(0)}%`,
        `Fees: ${
          selectedStudent.financial.fee_due <= 0 && selectedStudent.financial.payment_delay_days <= 0
            ? "Paid"
            : "Not Paid"
        }`,
        `Risk Level: ${prediction?.risk_level ?? selectedStudent.latest_risk_level ?? "Low"}`,
        "",
        "Subject-wise Attendance:",
        ...attendanceLines,
        "",
        "AI Recommendations:",
        ...recommendationLines,
      ].join("\n");
    } catch {
      return "";
    }
  };

  const openWhatsAppFor = async (target: "parent" | "student") => {
    if (!selectedStudent || !selectedStudentId) return;
    const rawPhone = target === "parent" ? selectedStudent.parent_mobile : selectedStudent.student_mobile;
    if (!rawPhone) {
      setError(`${target === "parent" ? "Parent" : "Student"} mobile number is not available for this student.`);
      return;
    }

    const cleanedPhone = rawPhone.replace(/[^\d]/g, "");
    if (!cleanedPhone) {
      setError(`${target === "parent" ? "Parent" : "Student"} mobile number is not in a valid format.`);
      return;
    }

    try {
      setError("");
      setIsPreparingWhatsApp(true);
      const message = buildWhatsAppMessage(target);
      if (!message) {
        setError("Unable to prepare the WhatsApp message.");
        return;
      }
      window.location.href = `https://wa.me/${cleanedPhone}?text=${encodeURIComponent(message)}`;
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(`Unable to prepare WhatsApp message: ${String(err.response.data.detail)}`);
      } else {
        setError("Unable to prepare the WhatsApp message. Confirm the backend is running and try again.");
      }
    } finally {
      setIsPreparingWhatsApp(false);
    }
  };

  const handleOpenParentWhatsApp = async () => openWhatsAppFor("parent");

  const handleOpenStudentWhatsApp = async () => openWhatsAppFor("student");

  const selectedStudentOverview = useMemo(() => {
    if (!selectedStudent) return [];
    const selectedStudentListRisk = students.find((item) => item.id === selectedStudent.id)?.latest_risk_level;
    return [
      { label: "Counselor", value: selectedStudent.counselor_name || "Unassigned" },
      { label: "Section", value: selectedStudent.section || "-" },
      { label: "Gender", value: selectedStudent.gender || "-" },
      { label: "Age", value: selectedStudent.age ?? "-" },
      { label: "Year", value: selectedStudent.year },
      { label: "CGPA", value: selectedStudent.gpa.toFixed(2) },
      { label: "Attendance", value: `${selectedStudent.attendance.toFixed(0)}%` },
      { label: "LMS %", value: `${selectedStudent.lms_activity.assignment_submission_rate.toFixed(0)}%` },
      { label: "Student Mobile", value: selectedStudent.student_mobile || "Not Available" },
      { label: "Parent Mobile", value: selectedStudent.parent_mobile || "Not Available" },
      {
        label: "Fees",
        value:
          selectedStudent.financial.fee_due <= 0 && selectedStudent.financial.payment_delay_days <= 0
            ? "Paid"
            : "Not Paid",
      },
      { label: "Risk", value: prediction?.risk_level ?? selectedStudentListRisk ?? selectedStudent.latest_risk_level ?? "Low" },
    ];
  }, [prediction?.risk_level, selectedStudent, students]);

  const runPredictionForStudent = async (student: StudentDetail, studentId: number) => {
    try {
      setError("");
      setIsPredicting(true);
      const result = await predictRisk(studentId, student);
      setPrediction(result);
      setStudents((current) =>
        current.map((student) =>
          student.id === studentId
            ? { ...student, latest_risk_level: result.risk_level, latest_risk_score: result.probability }
            : student
        )
      );
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(`Prediction failed: ${String(err.response.data.detail)}`);
      } else {
        setError("Prediction failed. Train the model first and confirm the backend is reachable.");
      }
    } finally {
      setIsPredicting(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-tide">AI Engine</p>
            <h1 className="mt-3 font-display text-3xl text-ink sm:text-4xl">Early Warning Intelligence</h1>
          </div>
        </div>
        <p className="mt-4 text-sm text-slate-500">Click a student row to open AI Risk Intelligence for that student.</p>
      </section>

      {selectedStudent ? (
        <section ref={predictionSectionRef} className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <button
                type="button"
                onClick={handleBackToList}
                className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 px-4 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
              >
                <ArrowLeft size={16} />
                Back to Student List
              </button>
              <p className="mt-4 text-xs uppercase tracking-[0.24em] text-tide">Selected Student</p>
              <h2 className="mt-2 font-display text-3xl text-ink">{selectedStudent.name}</h2>
              <p className="mt-2 text-sm text-slate-500">
                {selectedStudent.registration_number} • Section {selectedStudent.section}
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-end">
              <button
                type="button"
                onClick={handleOpenStudentWhatsApp}
                disabled={!selectedStudent?.student_mobile || isPreparingWhatsApp}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#0f766e] px-5 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                <MessageCircle size={18} />
                {isPreparingWhatsApp ? "Preparing Message..." : "Student WhatsApp"}
              </button>
              <button
                type="button"
                onClick={handleOpenParentWhatsApp}
                disabled={!selectedStudent?.parent_mobile || isPreparingWhatsApp}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#1f9d55] px-5 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                <MessageCircle size={18} />
                {isPreparingWhatsApp ? "Preparing Message..." : "Parent WhatsApp"}
              </button>
              <button
                type="button"
                onClick={handleGenerateParentReport}
                disabled={!selectedStudent || isGeneratingReport}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-ink px-5 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                <Download size={18} />
                {isGeneratingReport ? "Generating Report..." : "Generate Parent Report"}
              </button>
              <button
                onClick={handleRunPrediction}
                disabled={!selectedStudent}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-coral px-5 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                <BrainCircuit size={18} /> {isPredicting ? "Running AI Risk Intelligence..." : "AI Risk Intelligence"}
              </button>
            </div>
          </div>

          <div className="mt-6">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
              {selectedStudentOverview.map((item) => (
                <div key={item.label} className="rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{item.label}</p>
                  <p className="mt-2 text-lg font-semibold text-ink">{item.value}</p>
                </div>
              ))}
            </div>

            <div className="mt-4">
              <button
                type="button"
                onClick={handleAttendanceToggle}
                className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-ink hover:bg-slate-50"
              >
                Subject Wise Attendance
                <ChevronDown size={16} className={`transition ${showSubjectAttendance ? "rotate-180" : ""}`} />
              </button>
            </div>

            <div className="mt-6">
              <PredictionPanel prediction={prediction} />
            </div>

            <section className="mt-6 rounded-[2rem] border border-slate-200 bg-slate-50 p-6">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-tide">Internal Marks</p>
                <h2 className="mt-2 font-display text-2xl text-ink">Subject-Wise Internal Marks</h2>
              </div>
              <div className="mt-5 overflow-x-auto rounded-[1.5rem] border border-slate-200 bg-white">
                <table className="min-w-full text-left text-sm text-ink">
                  <thead className="bg-slate-100 text-xs uppercase tracking-[0.16em] text-slate-500">
                    <tr>
                      <th className="px-4 py-3 font-semibold" rowSpan={2}>Subject</th>
                      <th className="px-4 py-3 text-center font-semibold" colSpan={7}>Mid-1 (M1)</th>
                    </tr>
                    <tr>
                      <th className="px-4 py-3 font-semibold">Pre T1</th>
                      <th className="px-4 py-3 font-semibold">T1</th>
                      <th className="px-4 py-3 font-semibold">T2</th>
                      <th className="px-4 py-3 font-semibold">T3</th>
                      <th className="px-4 py-3 font-semibold">T4</th>
                      <th className="px-4 py-3 font-semibold">T5</th>
                      <th className="px-4 py-3 font-semibold">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subjectInternalMarks.map((item) => (
                      <tr key={item.subject_name} className="border-t border-slate-100">
                        <td className="px-4 py-3 font-semibold text-ink">{item.subject_name}</td>
                        <td className="px-4 py-3">{hasInternalMarks(item) ? displayMark(item.pre_t1_marks) : EMPTY_MARK}</td>
                        <td className="px-4 py-3">{hasInternalMarks(item) ? displayMark(item.t1_marks) : EMPTY_MARK}</td>
                        <td className="px-4 py-3">{hasInternalMarks(item) ? displayMark(item.t2_marks) : EMPTY_MARK}</td>
                        <td className="px-4 py-3">{hasInternalMarks(item) ? displayMark(item.t3_marks) : EMPTY_MARK}</td>
                        <td className="px-4 py-3">{hasInternalMarks(item) ? displayMark(item.t4_marks) : EMPTY_MARK}</td>
                        <td className="px-4 py-3">
                          {hasInternalMarks(item) ? (
                            <div>
                              <div>{formatMark(item.t5_marks)}</div>
                              <div className="mt-1 text-xs text-slate-500">
                                {t5Assignments(item)
                                  .map((score, index) => `CLA-${index + 1}: ${formatMark(score)}`)
                                  .join("  ")}
                              </div>
                            </div>
                          ) : (
                            EMPTY_MARK
                          )}
                        </td>
                        <td className="px-4 py-3 font-semibold">
                          {hasInternalMarks(item)
                            ? isT5OnlySubject(item.subject_name)
                              ? EMPTY_MARK
                              : `${formatMark(item.total_marks)} / 60`
                            : EMPTY_MARK}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-5 overflow-x-auto rounded-[1.5rem] border border-slate-200 bg-white">
                <table className="min-w-full text-left text-sm text-ink">
                  <thead className="bg-slate-100 text-xs uppercase tracking-[0.16em] text-slate-500">
                    <tr>
                      <th className="px-4 py-3 font-semibold" rowSpan={2}>Subject</th>
                      <th className="px-4 py-3 text-center font-semibold" colSpan={7}>Mid-2 (M2)</th>
                    </tr>
                    <tr>
                      <th className="px-4 py-3 font-semibold">Pre T1</th>
                      <th className="px-4 py-3 font-semibold">T1</th>
                      <th className="px-4 py-3 font-semibold">T2</th>
                      <th className="px-4 py-3 font-semibold">T3</th>
                      <th className="px-4 py-3 font-semibold">T4</th>
                      <th className="px-4 py-3 font-semibold">T5</th>
                      <th className="px-4 py-3 font-semibold">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subjectInternalMarks.map((item) => (
                      <tr key={`${item.subject_name}-m2`} className="border-t border-slate-100">
                        <td className="px-4 py-3 font-semibold text-ink">{item.subject_name}</td>
                        <td className="px-4 py-3 text-slate-400">{EMPTY_MARK}</td>
                        <td className="px-4 py-3 text-slate-400">{EMPTY_MARK}</td>
                        <td className="px-4 py-3 text-slate-400">{EMPTY_MARK}</td>
                        <td className="px-4 py-3 text-slate-400">{EMPTY_MARK}</td>
                        <td className="px-4 py-3 text-slate-400">{EMPTY_MARK}</td>
                        <td className="px-4 py-3 text-slate-400">{EMPTY_MARK}</td>
                        <td className="px-4 py-3 font-semibold text-slate-400">{EMPTY_MARK}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {showSubjectAttendance ? (
              <section ref={subjectAttendanceRef} className="mt-6 rounded-[2rem] bg-white p-6 shadow-soft ring-1 ring-slate-100">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-tide">Attendance Breakdown</p>
                    <h2 className="mt-2 font-display text-2xl text-ink">Subject-Wise Attendance</h2>
                  </div>
                  <div className="rounded-full bg-mist px-4 py-2 text-sm font-semibold text-ink">
                    {selectedStudent.subject_attendance.length} subjects
                  </div>
                </div>
                <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {selectedStudent.subject_attendance.map((item) => (
                    <div key={item.subject_name} className="rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-4">
                      <p className="text-sm font-semibold text-ink">{item.subject_name}</p>
                      <p
                        className={`mt-3 text-2xl font-semibold ${
                          item.attendance_percentage < 75 ? "text-red-600" : "text-ink"
                        }`}
                      >
                        {item.attendance_percentage.toFixed(0)}%
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}
          </div>
        </section>
      ) : (
        <>
          <section className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="flex w-full flex-col gap-4 md:max-w-3xl md:flex-row">
                <div className="relative w-full md:max-w-md">
                  <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder="Search by name, registration number, or email"
                    className="w-full rounded-2xl border border-slate-200 py-3 pl-11 pr-4 text-sm text-ink outline-none focus:border-tide"
                  />
                </div>
                {role === "admin" ? (
                  <select
                    value={sectionFilter}
                    onChange={(event) => setSectionFilter(event.target.value)}
                    className="rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide md:min-w-[180px]"
                  >
                    <option value="All">All Sections</option>
                    {sectionOptions.map((section) => (
                      <option key={section} value={section}>
                        {section}
                      </option>
                    ))}
                  </select>
                ) : null}
              </div>
              <div className="text-sm text-slate-500">
                Showing {totalStudents === 0 ? 0 : (currentPage - 1) * pageSize + 1}-
                {Math.min(currentPage * pageSize, totalStudents)} of {totalStudents} students
              </div>
            </div>
          </section>

          <div className="space-y-4">
            <StudentTable
              students={students}
              selectedStudentId={selectedStudentId}
              onSelect={handleSelectStudent}
              latestPrediction={prediction}
            />
            <section className="flex flex-col gap-3 rounded-[2rem] bg-white px-4 py-4 shadow-soft sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:px-6">
              <div className="text-sm text-slate-500">
                Page {totalPages === 0 ? 0 : currentPage} of {totalPages}
              </div>
              <div className="flex w-full items-center gap-3 sm:w-auto">
                <button
                  onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                  disabled={currentPage === 1}
                  className="flex-1 rounded-2xl border border-slate-200 px-4 py-2 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:text-slate-300 sm:flex-none"
                >
                  Previous
                </button>
                <button
                  onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                  disabled={currentPage >= totalPages}
                  className="flex-1 rounded-2xl border border-slate-200 px-4 py-2 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:text-slate-300 sm:flex-none"
                >
                  Next
                </button>
              </div>
            </section>
          </div>
        </>
      )}

      {error ? <div className="rounded-3xl bg-red-50 px-5 py-4 text-red-700 shadow-soft">{error}</div> : null}
    </div>
  );
}

function buildFallbackPrediction(student: StudentDetail, overview: StudentListItem | null): PredictionResult {
  const positiveReasons: string[] = [];
  const riskReasons: string[] = [];
  let riskLevel: PredictionResult["risk_level"] = overview?.latest_risk_level ?? "Low";
  let probability = overview?.latest_risk_score ?? 0.35;

  if (student.gpa >= 7) positiveReasons.push("strong CGPA");
  else if (student.gpa < 6) riskReasons.push("low CGPA");

  if (student.attendance >= 85) positiveReasons.push("high attendance");
  else if (student.attendance < 65) riskReasons.push("very low attendance");
  else if (student.attendance < 75) riskReasons.push("low attendance");
  else if (student.attendance < 85) riskReasons.push("attendance below the safe threshold");

  if (student.lms_activity.assignment_submission_rate >= 80 && student.lms_activity.missed_assignments <= 2) {
    positiveReasons.push("strong LMS activity");
  } else {
    riskReasons.push("weak LMS activity");
  }

  if (student.financial.fee_due <= 0 && student.financial.payment_delay_days <= 0) {
    positiveReasons.push("fees paid on time");
  } else {
    riskReasons.push("pending fee payment");
  }

  if (!overview?.latest_risk_level) {
    const riskPoints =
      (student.attendance < 65 ? 3 : student.attendance < 75 ? 2 : student.attendance < 85 ? 1 : 0) +
      (student.gpa < 5.5 ? 2 : student.gpa < 7 ? 1 : 0) +
      (student.lms_activity.assignment_submission_rate < 65 || student.lms_activity.missed_assignments >= 4 ? 1 : 0) +
      (student.financial.fee_due > 0 || student.financial.payment_delay_days > 0 ? 1 : 0);

    if (riskPoints >= 4) {
      riskLevel = "High";
      probability = 0.85;
    } else if (riskPoints >= 2) {
      riskLevel = "Medium";
      probability = 0.65;
    } else if (riskPoints === 1) {
      riskLevel = "Low";
      probability = 0.35;
    } else {
      riskLevel =
        student.attendance >= 85 &&
        student.gpa >= 8 &&
        student.lms_activity.assignment_submission_rate >= 80 &&
        student.financial.fee_due <= 0 &&
        student.financial.payment_delay_days <= 0
          ? "Safe"
          : "Low";
      probability = riskLevel === "Safe" ? 0.15 : 0.35;
    }
  }

  const explanation =
    riskLevel === "Safe"
      ? `${(positiveReasons.slice(0, 3).join(", ") || "excellent academic and engagement signals").replace(/^./, (c) => c.toUpperCase())} are the main reasons behind the safe retention outlook.`
      : riskLevel === "Low"
      ? `${(positiveReasons.slice(0, 3).join(", ") || "stable academic and engagement signals").replace(/^./, (c) => c.toUpperCase())} are the main reasons behind the low retention risk.`
      : `${(riskReasons.slice(0, 3).join(", ") || "inconsistent academic and engagement signals").replace(/^./, (c) => c.toUpperCase())} are the main reasons behind the ${riskLevel.toLowerCase()} retention risk.`;

  const recommendations =
    riskLevel === "High"
      ? [
          "Urgently improve attendance above 75% with faculty follow-up and weekly monitoring.",
          "Schedule faculty mentoring for weak subjects and revise fundamentals twice a week.",
          "Complete pending LMS assignments immediately and recover missed coursework.",
          "Resolve pending fee payment without delay.",
        ]
      : riskLevel === "Medium"
        ? [
            "Improve attendance to at least 85% through structured class participation goals.",
            "Complete pending LMS assignments and maintain a submission rate above 90%.",
            "Review weak topics weekly with counselor or faculty support.",
            "Keep fee payment status regular to avoid additional risk.",
          ]
        : riskLevel === "Low"
          ? [
              "Maintain steady attendance and continue tracking progress every week.",
              "Stay regular with LMS work and internal assessments.",
              "Review any weak subject before it turns into a larger issue.",
              "Keep fee payment status regular.",
            ]
        : [
            "Maintain the current academic performance with monthly progress reviews.",
            "Continue consistent class attendance above 85%.",
            "Sustain strong LMS participation and on-time submissions.",
            "Keep fee payment status regular.",
          ];

  return {
    risk_level: riskLevel,
    probability,
    comparison_model_probability: probability,
    explanation,
    recommendations,
    feature_importance: [
      { feature: "gpa", importance: 0.041, actual_value: Number(student.gpa.toFixed(2)) },
      { feature: "attendance", importance: 0.041, actual_value: `${student.attendance.toFixed(1)}%` },
      {
        feature: "assignment_submission_rate",
        importance: 0.038,
        actual_value: `${student.lms_activity.assignment_submission_rate.toFixed(1)}%`,
      },
      {
        feature: "fees_paid_status",
        importance: 0.02,
        actual_value:
          student.financial.fee_due <= 0 && student.financial.payment_delay_days <= 0 ? "Paid" : "Not Paid",
      },
    ],
  };
}
