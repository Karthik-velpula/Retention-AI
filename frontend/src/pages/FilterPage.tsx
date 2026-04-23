import { Download, Filter, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { fetchCounselors, fetchStudent, fetchStudentsPage } from "../api/endpoints";
import RiskBadge from "../components/RiskBadge";
import { useAuth } from "../context/AuthContext";
import { StudentDetail, StudentListItem } from "../types";

type RiskFilter = "All" | "Safe" | "Low" | "Medium" | "High";
type AttendanceFilter = "All" | "Below 65%" | "Below 75%" | "Below 85%";
type FeeFilter = "All" | "Paid" | "Not Paid";

const EMPTY_MARK = "-";
const T5_ONLY_SUBJECT_CODES = ["22CS958", "22TP302"];

const isT5OnlySubject = (subjectName: string) =>
  T5_ONLY_SUBJECT_CODES.some((code) => subjectName.toUpperCase().startsWith(code));

const hasInternalMarks = (item: StudentDetail["subject_attendance"][number]) =>
  [
    item.pre_t1_marks,
    item.t1_marks,
    item.t2_marks,
    item.t3_marks,
    item.t4_marks,
    item.t5_marks,
    item.total_marks,
  ].some((value) => value > 0);

const formatMark = (value: number) => {
  if (value === 0) return EMPTY_MARK;
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
};

const t5Assignments = (item: StudentDetail["subject_attendance"][number]) => [
  item.t5_assignment_1,
  item.t5_assignment_2,
  item.t5_assignment_3,
  item.t5_assignment_4,
];

const openStudentPredictions = (navigate: (path: string) => void, student: StudentListItem) => {
  navigate(`/students?regNo=${encodeURIComponent(student.registration_number)}`);
};

export default function FilterPage() {
  const { role } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedRisk = searchParams.get("risk");
  const requestedAttendance = searchParams.get("attendance");
  const requestedQuery = searchParams.get("query") ?? "";
  const requestedFee = searchParams.get("fee");
  const requestedSection = searchParams.get("section");
  const requestedFocus = searchParams.get("focus");
  const initialRiskFilter: RiskFilter =
    requestedRisk === "Safe" || requestedRisk === "Low" || requestedRisk === "Medium" || requestedRisk === "High"
      ? requestedRisk
      : "All";
  const initialAttendanceFilter: AttendanceFilter =
    requestedAttendance === "Below 65%" || requestedAttendance === "Below 75%" || requestedAttendance === "Below 85%"
      ? requestedAttendance
      : "All";
  const initialFeeFilter: FeeFilter = requestedFee === "Paid" || requestedFee === "Not Paid" ? requestedFee : "All";
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [searchTerm, setSearchTerm] = useState(requestedQuery);
  const [riskFilter, setRiskFilter] = useState<RiskFilter>(initialRiskFilter);
  const [attendanceFilter, setAttendanceFilter] = useState<AttendanceFilter>(initialAttendanceFilter);
  const [feeFilter, setFeeFilter] = useState<FeeFilter>(initialFeeFilter);
  const [counselors, setCounselors] = useState<string[]>([]);
  const [counselorFilter, setCounselorFilter] = useState("All");
  const [sectionFilter, setSectionFilter] = useState(role === "admin" && requestedSection ? requestedSection : "All");
  const [genderFilter, setGenderFilter] = useState("All");
  const [minCgpaFilter, setMinCgpaFilter] = useState("");
  const [maxCgpaFilter, setMaxCgpaFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalStudents, setTotalStudents] = useState(0);
  const [error, setError] = useState("");
  const [isDownloading, setIsDownloading] = useState(false);
  const [isViewingAttendance, setIsViewingAttendance] = useState(false);
  const [isViewingLms, setIsViewingLms] = useState(false);
  const [isViewingMarks, setIsViewingMarks] = useState(false);
  const [marksStudents, setMarksStudents] = useState<StudentDetail[]>([]);
  const [subjectAttendanceRows, setSubjectAttendanceRows] = useState<
    Array<{
      serialNumber: number;
      registrationNumber: string;
      name: string;
      counselorName: string;
      section: string;
      subjectAttendance: Record<string, string>;
    }>
  >([]);
  const [subjectAttendanceTitle, setSubjectAttendanceTitle] = useState("Subject-Wise Attendance");
  const [lmsActivityRows, setLmsActivityRows] = useState<
    Array<{
      serialNumber: number;
      registrationNumber: string;
      name: string;
      counselorName: string;
      section: string;
      weekScores: number[];
      totalCorrect: number;
      lmsPercentage: string;
      riskLevel: string;
    }>
  >([]);
  const [lmsActivityTitle, setLmsActivityTitle] = useState("LMS Activity");
  const [marksStudent, setMarksStudent] = useState<StudentDetail | null>(null);
  const [marksTitle, setMarksTitle] = useState("Subject-Wise Internal Marks");
  const pageSize = 25;
  const lmsSectionRef = useRef<HTMLElement | null>(null);
  const attendanceSectionRef = useRef<HTMLElement | null>(null);
  const marksSectionRef = useRef<HTMLElement | null>(null);
  const marksListSectionRef = useRef<HTMLElement | null>(null);
  const resultsSectionRef = useRef<HTMLElement | null>(null);
  const [searchTrigger, setSearchTrigger] = useState(0);
  const handledVoiceActionRef = useRef("");

  useEffect(() => {
    setSearchTerm(requestedQuery);
    if (requestedRisk === "Safe" || requestedRisk === "Low" || requestedRisk === "Medium" || requestedRisk === "High") {
      setRiskFilter(requestedRisk);
    } else {
      setRiskFilter("All");
    }
    if (requestedAttendance === "Below 65%" || requestedAttendance === "Below 75%" || requestedAttendance === "Below 85%") {
      setAttendanceFilter(requestedAttendance);
    } else {
      setAttendanceFilter("All");
    }
    if (requestedFee === "Paid" || requestedFee === "Not Paid") {
      setFeeFilter(requestedFee);
    } else {
      setFeeFilter("All");
    }
    if (role === "admin") {
      setSectionFilter(requestedSection || "All");
    }
  }, [requestedAttendance, requestedFee, requestedQuery, requestedRisk, requestedSection, role]);

  const buildFilterParams = (page: number, perPage: number) => ({
    page,
    page_size: perPage,
    query: searchTerm.trim() || undefined,
    risk_level: riskFilter !== "All" ? riskFilter : undefined,
    attendance_filter: attendanceFilter !== "All" ? attendanceFilter : undefined,
    fee_status: feeFilter !== "All" ? feeFilter : undefined,
    counselor_name: role === "admin" && counselorFilter !== "All" ? counselorFilter : undefined,
    section: role === "admin" && sectionFilter !== "All" ? sectionFilter : undefined,
    gender: genderFilter !== "All" ? genderFilter : undefined,
    min_cgpa: minCgpaFilter.trim() ? Number(minCgpaFilter) : undefined,
    max_cgpa: maxCgpaFilter.trim() ? Number(maxCgpaFilter) : undefined,
  });

  useEffect(() => {
    fetchStudentsPage(buildFilterParams(currentPage, pageSize))
      .then((response) => {
        setStudents(response.items);
        setTotalStudents(response.total);
        setError("");
      })
      .catch(() => setError("Unable to load students for filtering."));
  }, [
    attendanceFilter,
    counselorFilter,
    currentPage,
    feeFilter,
    genderFilter,
    maxCgpaFilter,
    minCgpaFilter,
    riskFilter,
    role,
    searchTerm,
    sectionFilter,
  ]);

  useEffect(() => {
    if (role !== "admin") return;
    fetchCounselors()
      .then((items) => setCounselors(items))
      .catch(() => setError("Unable to load counselors for filtering."));
  }, [role]);

  useEffect(() => {
    setCurrentPage(1);
  }, [
    attendanceFilter,
    counselorFilter,
    feeFilter,
    genderFilter,
    maxCgpaFilter,
    minCgpaFilter,
    riskFilter,
    searchTerm,
    sectionFilter,
  ]);

  useEffect(() => {
    if (searchTrigger === 0) return;
    window.requestAnimationFrame(() => {
      resultsSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [searchTrigger, students]);

  useEffect(() => {
    if (!requestedFocus) return;
    if (students.length !== 1) return;

    const actionKey = `${requestedFocus}:${students[0]?.id ?? ""}:${requestedQuery}`;
    if (handledVoiceActionRef.current === actionKey) return;
    handledVoiceActionRef.current = actionKey;

    if (requestedFocus === "attendance") {
      void viewSingleStudentAttendance(students[0]);
    } else if (requestedFocus === "lms") {
      void viewSingleStudentLms(students[0]);
    } else if (requestedFocus === "marks") {
      void viewSingleStudentMarks(students[0]);
    }
  }, [requestedFocus, requestedQuery, students]);

  const handleSearchSubmit = () => {
    setCurrentPage(1);
    setSearchTrigger((current) => current + 1);
  };

  const counselorOptions = useMemo(() => {
    return counselors;
  }, [counselors]);

  const sectionOptions = useMemo(() => {
    const detectedSections = new Set(
      students.map((student) => student.section?.trim()).filter(Boolean) as string[]
    );
    for (let section = 1; section <= 19; section += 1) {
      detectedSections.add(String(section));
    }
    return Array.from(detectedSections).sort((a, b) => Number(a) - Number(b));
  }, [students]);

  const genderOptions = useMemo(() => {
    return Array.from(new Set(students.map((student) => student.gender?.trim()).filter(Boolean) as string[])).sort((a, b) =>
      a.localeCompare(b)
    );
  }, [students]);

  const totalPages = Math.max(1, Math.ceil(totalStudents / pageSize));
  const subjectAttendanceColumns = useMemo(() => {
    const columns = new Set<string>();
    subjectAttendanceRows.forEach((row) => {
      Object.keys(row.subjectAttendance).forEach((subject) => columns.add(subject));
    });
    return Array.from(columns).sort((a, b) => a.localeCompare(b));
  }, [subjectAttendanceRows]);

  const activeFilters = useMemo(() => {
    const items: string[] = [];
    if (searchTerm.trim()) items.push(`Search: ${searchTerm.trim()}`);
    if (riskFilter !== "All") items.push(`Risk: ${riskFilter}`);
    if (attendanceFilter !== "All") items.push(`Attendance: ${attendanceFilter}`);
    if (feeFilter !== "All") items.push(`Fees: ${feeFilter}`);
    if (role === "admin" && counselorFilter !== "All") items.push(`Counselor: ${counselorFilter}`);
    if (role === "admin" && sectionFilter !== "All") items.push(`Section: ${sectionFilter}`);
    if (genderFilter !== "All") items.push(`Gender: ${genderFilter}`);
    if (minCgpaFilter.trim()) items.push(`Min CGPA: ${minCgpaFilter.trim()}`);
    if (maxCgpaFilter.trim()) items.push(`Max CGPA: ${maxCgpaFilter.trim()}`);
    return items;
  }, [
    attendanceFilter,
    counselorFilter,
    feeFilter,
    genderFilter,
    maxCgpaFilter,
    minCgpaFilter,
    riskFilter,
    role,
    searchTerm,
    sectionFilter,
  ]);

  const fetchAllFilteredStudents = async () => {
    const exportPageSize = 100;
    const firstPage = await fetchStudentsPage(buildFilterParams(1, exportPageSize));
    const allItems = [...firstPage.items];
    const totalPagesForExport = Math.max(1, Math.ceil(firstPage.total / exportPageSize));

    for (let page = 2; page <= totalPagesForExport; page += 1) {
      const response = await fetchStudentsPage(buildFilterParams(page, exportPageSize));
      allItems.push(...response.items);
    }

    return allItems;
  };

  const fetchAllFilteredStudentDetails = async () => {
    const filteredStudents = await fetchAllFilteredStudents();
    const detailBatches: StudentDetail[] = [];

    for (let start = 0; start < filteredStudents.length; start += 20) {
      const batch = filteredStudents.slice(start, start + 20);
      const details = await Promise.all(batch.map((student) => fetchStudent(student.id)));
      detailBatches.push(...details);
    }

    return detailBatches;
  };

  const escapeCsvCell = (value: string | number) =>
    `"${String(value).replace(/\r?\n/g, " ").replace(/"/g, '""')}"`;
  const asSpreadsheetText = (value: string) => `="${value.replace(/\r?\n/g, " ").replace(/"/g, '""')}"`;

  const triggerCsvDownload = (filename: string, headers: Array<string | number>, rows: Array<Array<string | number>>) => {
    const csv = ["\uFEFF", [headers, ...rows].map((row) => row.map(escapeCsvCell).join(",")).join("\n")].join("");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const buildWeeklyCorrectCounts = (registrationNumber: string, lmsPercentage: number) => {
    const totalCorrect = Math.max(0, Math.min(60, Math.round((lmsPercentage / 100) * 60)));
    const weekScores = new Array<number>(6).fill(0);

    let remaining = totalCorrect;
    let seed = registrationNumber.split("").reduce((sum, char, index) => sum + char.charCodeAt(0) * (index + 1), 0);

    while (remaining > 0) {
      const weekIndex = seed % 6;
      if (weekScores[weekIndex] < 10) {
        weekScores[weekIndex] += 1;
        remaining -= 1;
      }
      seed = (seed * 1664525 + 1013904223) >>> 0;
    }

    return {
      weekScores,
      totalCorrect,
    };
  };

  const downloadCsv = async () => {
    setIsDownloading(true);
    try {
      const filteredStudents = await fetchAllFilteredStudents();
      const headers = [
      "S.No",
      "Registration Number",
      "Name",
      "Email",
      "Counselor Name",
      "Section",
      "Gender",
      "Age",
      "Year",
      "CGPA",
      "Attendance",
      "LMS Percentage",
      "Fees Status",
      "Risk Level",
    ];
      const rows = filteredStudents.map((student, index) => [
      index + 1,
      student.registration_number,
      asSpreadsheetText(student.name),
      student.email,
      asSpreadsheetText(student.counselor_name ?? ""),
      student.section,
      student.gender,
      student.age ?? "-",
      student.year,
      student.gpa.toFixed(2),
      student.attendance.toFixed(0),
      student.lms_activity_percentage.toFixed(0),
      student.fees_paid_status,
      student.latest_risk_level ?? "Low",
    ]);

      triggerCsvDownload("filtered-students.csv", headers, rows);
      setError("");
    } catch {
      setError("Unable to download all filtered students.");
    } finally {
      setIsDownloading(false);
    }
  };

  const downloadMarksCsv = async () => {
    setIsDownloading(true);
    try {
      const detailedStudents = await fetchAllFilteredStudentDetails();
      const headers = [
        "S.No",
        "Registration Number",
        "Name",
        "Counselor Name",
        "Section",
        "Subject",
        "Pre T1",
        "T1",
        "T2",
        "T3",
        "T4",
        "T5",
        "CLA-1",
        "CLA-2",
        "CLA-3",
        "CLA-4",
        "Total",
      ];
      const rows = detailedStudents.flatMap((student, studentIndex) =>
        student.subject_attendance.map((subject) => [
          studentIndex + 1,
          student.registration_number,
          asSpreadsheetText(student.name),
          asSpreadsheetText(student.counselor_name ?? ""),
          student.section,
          subject.subject_name,
          hasInternalMarks(subject) ? formatMark(subject.pre_t1_marks) : EMPTY_MARK,
          hasInternalMarks(subject) ? formatMark(subject.t1_marks) : EMPTY_MARK,
          hasInternalMarks(subject) ? formatMark(subject.t2_marks) : EMPTY_MARK,
          hasInternalMarks(subject) ? formatMark(subject.t3_marks) : EMPTY_MARK,
          hasInternalMarks(subject) ? formatMark(subject.t4_marks) : EMPTY_MARK,
          hasInternalMarks(subject) ? formatMark(subject.t5_marks) : EMPTY_MARK,
          hasInternalMarks(subject) ? formatMark(subject.t5_assignment_1) : EMPTY_MARK,
          hasInternalMarks(subject) ? formatMark(subject.t5_assignment_2) : EMPTY_MARK,
          hasInternalMarks(subject) ? formatMark(subject.t5_assignment_3) : EMPTY_MARK,
          hasInternalMarks(subject) ? formatMark(subject.t5_assignment_4) : EMPTY_MARK,
          hasInternalMarks(subject)
            ? isT5OnlySubject(subject.subject_name)
              ? EMPTY_MARK
              : `${formatMark(subject.total_marks)} / 60`
            : EMPTY_MARK,
        ])
      );

      triggerCsvDownload("filtered-students-marks.csv", headers, rows);
      setError("");
    } catch {
      setError("Unable to download marks for all filtered students.");
    } finally {
      setIsDownloading(false);
    }
  };

  const downloadLmsActivityCsv = async () => {
    setIsDownloading(true);
    try {
      const filteredStudents = await fetchAllFilteredStudents();
      const headers = [
        "S.No",
        "Registration Number",
        "Name",
        "Counselor Name",
        "Section",
        "Week-1 Correct",
        "Week-2 Correct",
        "Week-3 Correct",
        "Week-4 Correct",
        "Week-5 Correct",
        "Week-6 Correct",
        "Total Correct",
        "LMS Percentage",
        "Risk Level",
      ];
      const rows = filteredStudents.map((student, index) => {
        const { weekScores, totalCorrect } = buildWeeklyCorrectCounts(
          student.registration_number,
          student.lms_activity_percentage
        );

        return [
          index + 1,
          student.registration_number,
          asSpreadsheetText(student.name),
          asSpreadsheetText(student.counselor_name ?? ""),
          student.section,
          ...weekScores,
          totalCorrect,
          student.lms_activity_percentage.toFixed(2),
          student.latest_risk_level ?? "Low",
        ];
      });

      triggerCsvDownload("filtered-students-lms-activity.csv", headers, rows);
      setError("");
    } catch {
      setError("Unable to download LMS activity for all filtered students.");
    } finally {
      setIsDownloading(false);
    }
  };

  const downloadSubjectAttendanceCsv = async () => {
    setIsDownloading(true);
    try {
      const detailedStudents = await fetchAllFilteredStudentDetails();
      const headers = [
        "S.No",
        "Registration Number",
        "Name",
        "Counselor Name",
        "Section",
        "Subject",
        "Attendance Percentage",
      ];
      const rows = detailedStudents.flatMap((student) =>
        student.subject_attendance.map((subject, index) => [
          index + 1,
          student.registration_number,
          asSpreadsheetText(student.name),
          asSpreadsheetText(student.counselor_name ?? ""),
          student.section,
          subject.subject_name,
          subject.attendance_percentage.toFixed(2),
        ])
      );

      triggerCsvDownload("filtered-students-subject-attendance.csv", headers, rows);
      setError("");
    } catch {
      setError("Unable to download subject-wise attendance for all filtered students.");
    } finally {
      setIsDownloading(false);
    }
  };

  const viewSubjectAttendance = async () => {
    setIsViewingAttendance(true);
    try {
      const detailedStudents = await fetchAllFilteredStudentDetails();
      const rows = detailedStudents.map((student, index) => ({
        serialNumber: index + 1,
        registrationNumber: student.registration_number,
        name: student.name,
        counselorName: student.counselor_name ?? "",
        section: student.section,
        subjectAttendance: Object.fromEntries(
          student.subject_attendance.map((subject) => [subject.subject_name, subject.attendance_percentage.toFixed(2)])
        ),
      }));
      setSubjectAttendanceRows(rows);
      setSubjectAttendanceTitle("Subject-Wise Attendance");
      setError("");
    } catch {
      setError("Unable to view subject-wise attendance for all filtered students.");
    } finally {
      setIsViewingAttendance(false);
    }
  };

  const viewLmsActivity = async () => {
    setIsViewingLms(true);
    try {
      const filteredStudents = await fetchAllFilteredStudents();
      const rows = filteredStudents.map((student, index) => {
        const { weekScores, totalCorrect } = buildWeeklyCorrectCounts(
          student.registration_number,
          student.lms_activity_percentage
        );

        return {
          serialNumber: index + 1,
          registrationNumber: student.registration_number,
          name: student.name,
          counselorName: student.counselor_name ?? "",
          section: student.section,
          weekScores,
          totalCorrect,
          lmsPercentage: student.lms_activity_percentage.toFixed(2),
          riskLevel: student.latest_risk_level ?? "Low",
        };
      });
      setLmsActivityRows(rows);
      setLmsActivityTitle("LMS Activity");
      setError("");
    } catch {
      setError("Unable to view LMS activity for all filtered students.");
    } finally {
      setIsViewingLms(false);
    }
  };

  const viewMarks = async () => {
    setIsViewingMarks(true);
    try {
      const filteredStudents = await fetchAllFilteredStudents();
      if (filteredStudents.length === 1) {
        const detail = await fetchStudent(filteredStudents[0].id);
        setMarksStudents([]);
        setMarksStudent(detail);
        setMarksTitle(`Subject-Wise Internal Marks - ${detail.name}`);
        setError("");
        window.requestAnimationFrame(() => {
          marksSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
        return;
      }

      const details = await fetchAllFilteredStudentDetails();
      setMarksStudent(null);
      setMarksStudents(details);
      setError("");
      window.requestAnimationFrame(() => {
        marksListSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch {
      setError("Unable to view marks for all filtered students.");
    } finally {
      setIsViewingMarks(false);
    }
  };

  const viewSingleStudentAttendance = async (student: StudentListItem) => {
    setIsViewingAttendance(true);
    try {
      const detail = await fetchStudent(student.id);
      setSubjectAttendanceRows([
        {
          serialNumber: 1,
          registrationNumber: detail.registration_number,
          name: detail.name,
          counselorName: detail.counselor_name ?? "",
          section: detail.section,
          subjectAttendance: Object.fromEntries(
            detail.subject_attendance.map((subject) => [subject.subject_name, subject.attendance_percentage.toFixed(2)])
          ),
        },
      ]);
      setSubjectAttendanceTitle(`Subject-Wise Attendance - ${detail.name}`);
      setError("");
      window.requestAnimationFrame(() => {
        attendanceSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch {
      setError(`Unable to view subject-wise attendance for ${student.name}.`);
    } finally {
      setIsViewingAttendance(false);
    }
  };

  const viewSingleStudentLms = async (student: StudentListItem) => {
    setIsViewingLms(true);
    try {
      const { weekScores, totalCorrect } = buildWeeklyCorrectCounts(student.registration_number, student.lms_activity_percentage);
      setLmsActivityRows([
        {
          serialNumber: 1,
          registrationNumber: student.registration_number,
          name: student.name,
          counselorName: student.counselor_name ?? "",
          section: student.section,
          weekScores,
          totalCorrect,
          lmsPercentage: student.lms_activity_percentage.toFixed(2),
          riskLevel: student.latest_risk_level ?? "Low",
        },
      ]);
      setLmsActivityTitle(`LMS Activity - ${student.name}`);
      setError("");
      window.requestAnimationFrame(() => {
        lmsSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch {
      setError(`Unable to view LMS activity for ${student.name}.`);
    } finally {
      setIsViewingLms(false);
    }
  };

  const viewSingleStudentMarks = async (student: StudentListItem) => {
    setIsViewingMarks(true);
    try {
      const detail = await fetchStudent(student.id);
      setMarksStudents([]);
      setMarksStudent(detail);
      setMarksTitle(`Subject-Wise Internal Marks - ${student.name}`);
      setError("");
      window.requestAnimationFrame(() => {
        marksSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch {
      setError(`Unable to view marks for ${student.name}.`);
    } finally {
      setIsViewingMarks(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-tide">Smart Filters</p>
        <h1 className="mt-3 font-display text-3xl text-ink sm:text-4xl">Filter Students</h1>
        <p className="mt-3 text-sm text-slate-600 sm:text-base">
          Filter students by risk, attendance, fee status, search terms
          {role === "admin" ? ", and counselor/faculty ownership" : ""}
          {" "}and download the filtered result.
        </p>
      </section>

      <section ref={resultsSectionRef} className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Risk Level</span>
              <select
                value={riskFilter}
                onChange={(event) => setRiskFilter(event.target.value as RiskFilter)}
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
              >
                <option>All</option>
                <option>Safe</option>
                <option>High</option>
                <option>Medium</option>
                <option>Low</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Attendance</span>
              <select
                value={attendanceFilter}
                onChange={(event) => setAttendanceFilter(event.target.value as AttendanceFilter)}
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
              >
                <option>All</option>
                <option>Below 65%</option>
                <option>Below 75%</option>
                <option>Below 85%</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Fee Status</span>
              <select
                value={feeFilter}
                onChange={(event) => setFeeFilter(event.target.value as FeeFilter)}
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
              >
                <option>All</option>
                <option>Paid</option>
                <option>Not Paid</option>
              </select>
            </label>
            {role === "admin" ? (
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Section</span>
                <select
                  value={sectionFilter}
                  onChange={(event) => setSectionFilter(event.target.value)}
                  className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
                >
                  <option value="All">All Sections</option>
                  {sectionOptions.map((section) => (
                    <option key={section} value={section}>
                      {section}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Gender</span>
              <select
                value={genderFilter}
                onChange={(event) => setGenderFilter(event.target.value)}
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
              >
                <option value="All">All Genders</option>
                {genderOptions.map((gender) => (
                  <option key={gender} value={gender}>
                    {gender}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Min CGPA</span>
              <input
                value={minCgpaFilter}
                onChange={(event) => setMinCgpaFilter(event.target.value)}
                placeholder="Enter minimum CGPA"
                type="number"
                step="0.01"
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Max CGPA</span>
              <input
                value={maxCgpaFilter}
                onChange={(event) => setMaxCgpaFilter(event.target.value)}
                placeholder="Enter maximum CGPA"
                type="number"
                step="0.01"
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
              />
            </label>
            {role === "admin" ? (
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Counselor</span>
                <select
                  value={counselorFilter}
                  onChange={(event) => setCounselorFilter(event.target.value)}
                  className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none focus:border-tide"
                >
                  <option value="All">All Counselors</option>
                  {counselorOptions.map((counselor) => (
                    <option key={counselor} value={counselor}>
                      {counselor}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>

          <div className="rounded-[1.75rem] border border-slate-200 bg-[linear-gradient(180deg,rgba(248,250,252,0.98)_0%,rgba(241,245,249,0.92)_100%)] p-4 shadow-[0_18px_40px_rgba(15,23,42,0.08)]">
            <p className="text-xs uppercase tracking-[0.22em] text-tide">Quick Summary</p>
            <div className="mt-4 grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)_minmax(0,1fr)]">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div className="rounded-2xl border border-slate-200/80 bg-white px-4 py-3 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Matching Students</p>
                  <p className="mt-2 text-2xl font-semibold text-ink">{totalStudents}</p>
                </div>
                <div className="rounded-2xl border border-slate-200/80 bg-white px-4 py-3 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Current Page</p>
                  <p className="mt-2 text-2xl font-semibold text-ink">{currentPage}</p>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200/80 bg-white p-3 shadow-sm">
                <p className="px-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">Downloads</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <button
                    onClick={downloadCsv}
                    disabled={isDownloading}
                    className="inline-flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-ink transition hover:border-slate-300 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <span className="inline-flex items-center gap-2">
                      <Download size={18} />
                      Filtered CSV
                    </span>
                    <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">Base</span>
                  </button>
                  <button
                    onClick={downloadMarksCsv}
                    disabled={isDownloading}
                    className="inline-flex w-full items-center justify-between rounded-2xl bg-ink px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <span className="inline-flex items-center gap-2">
                      <Download size={18} />
                      Marks CSV
                    </span>
                    <span className="text-xs font-medium uppercase tracking-[0.16em] text-white/70">Detailed</span>
                  </button>
                  <button
                    onClick={downloadLmsActivityCsv}
                    disabled={isDownloading}
                    className="inline-flex w-full items-center justify-between rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <span className="inline-flex items-center gap-2">
                      <Download size={18} />
                      LMS CSV
                    </span>
                  </button>
                  <button
                    onClick={downloadSubjectAttendanceCsv}
                    disabled={isDownloading}
                    className="inline-flex w-full items-center justify-between rounded-2xl bg-tide px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <span className="inline-flex items-center gap-2">
                      <Download size={18} />
                      Attendance CSV
                    </span>
                  </button>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200/80 bg-white p-3 shadow-sm">
                <p className="px-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">Views</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                  <button
                    onClick={viewSubjectAttendance}
                    disabled={isViewingAttendance}
                    className="inline-flex w-full items-center justify-between rounded-2xl border border-[#2a5f82] bg-white px-4 py-3 text-sm font-semibold text-[#2a5f82] transition hover:bg-[#f4f9fc] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <span className="inline-flex items-center gap-2">
                      <Filter size={18} />
                      {isViewingAttendance ? "Loading Attendance..." : "View Attendance"}
                    </span>
                  </button>
                  <button
                    onClick={viewLmsActivity}
                    disabled={isViewingLms}
                    className="inline-flex w-full items-center justify-between rounded-2xl border border-emerald-600 bg-white px-4 py-3 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <span className="inline-flex items-center gap-2">
                      <Filter size={18} />
                      {isViewingLms ? "Loading LMS..." : "View LMS"}
                    </span>
                  </button>
                  <button
                    onClick={viewMarks}
                    disabled={isViewingMarks}
                    className="inline-flex w-full items-center justify-between rounded-2xl border border-ink bg-white px-4 py-3 text-sm font-semibold text-ink transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <span className="inline-flex items-center gap-2">
                      <Filter size={18} />
                      {isViewingMarks ? "Loading Marks..." : "View Marks"}
                    </span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {marksStudents.length > 0 ? (
        <section ref={marksListSectionRef} className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-tide">Marks View</p>
              <h2 className="mt-2 font-display text-2xl text-ink">Filtered Students Subject-Wise Marks</h2>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-ink">
                {marksStudents.length} students
              </div>
              <button
                type="button"
                onClick={() => setMarksStudents([])}
                className="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white p-2 text-slate-600 transition hover:border-slate-300 hover:text-ink"
                aria-label="Close marks list view"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          <div className="space-y-5">
            {marksStudents.map((student, index) => (
              <section key={student.id} className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4 sm:p-5">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-tide">Student {index + 1}</p>
                    <h3 className="mt-2 text-xl font-semibold text-ink">{student.name}</h3>
                    <p className="mt-1 text-sm text-slate-500">
                      {student.registration_number} • Counselor {student.counselor_name ?? "-"} • Section {student.section || "-"}
                    </p>
                  </div>
                  <div className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-ink">
                    Risk: {student.latest_risk_level ?? "Low"} • Marks %: {student.marks.toFixed(2)}
                  </div>
                </div>

                <div className="overflow-x-auto rounded-[1.25rem] border border-slate-200 bg-white">
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
                      {student.subject_attendance.map((item) => (
                        <tr key={`${student.id}-${item.subject_name}`} className="border-t border-slate-100">
                          <td className="px-4 py-3 font-semibold text-ink">{item.subject_name}</td>
                          <td className="px-4 py-3">{hasInternalMarks(item) ? formatMark(item.pre_t1_marks) : EMPTY_MARK}</td>
                          <td className="px-4 py-3">{hasInternalMarks(item) ? formatMark(item.t1_marks) : EMPTY_MARK}</td>
                          <td className="px-4 py-3">{hasInternalMarks(item) ? formatMark(item.t2_marks) : EMPTY_MARK}</td>
                          <td className="px-4 py-3">{hasInternalMarks(item) ? formatMark(item.t3_marks) : EMPTY_MARK}</td>
                          <td className="px-4 py-3">{hasInternalMarks(item) ? formatMark(item.t4_marks) : EMPTY_MARK}</td>
                          <td className="px-4 py-3">
                            {hasInternalMarks(item) ? (
                              <div>
                                <div>{formatMark(item.t5_marks)}</div>
                                <div className="mt-1 text-xs text-slate-500">
                                  {t5Assignments(item)
                                    .map((score, assignmentIndex) => `CLA-${assignmentIndex + 1}: ${formatMark(score)}`)
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
              </section>
            ))}
          </div>
        </section>
      ) : null}

      {lmsActivityRows.length > 0 ? (
        <section ref={lmsSectionRef} className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-tide">LMS View</p>
              <h2 className="mt-2 font-display text-2xl text-ink">{lmsActivityTitle}</h2>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-ink">
                {lmsActivityRows.length} students
              </div>
              <button
                type="button"
                onClick={() => {
                  setLmsActivityRows([]);
                  setLmsActivityTitle("LMS Activity");
                }}
                className="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white p-2 text-slate-600 transition hover:border-slate-300 hover:text-ink"
                aria-label="Close LMS activity view"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-3xl border border-slate-100">
            <table className="min-w-[1400px] text-left text-sm">
              <thead className="bg-ink text-white">
                <tr>
                  <th className="px-5 py-4 font-medium">S.No</th>
                  <th className="px-5 py-4 font-medium">Reg No</th>
                  <th className="px-5 py-4 font-medium">Name</th>
                  <th className="px-5 py-4 font-medium">Counselor</th>
                  <th className="px-5 py-4 font-medium">Section</th>
                  <th className="px-5 py-4 font-medium">Week-1</th>
                  <th className="px-5 py-4 font-medium">Week-2</th>
                  <th className="px-5 py-4 font-medium">Week-3</th>
                  <th className="px-5 py-4 font-medium">Week-4</th>
                  <th className="px-5 py-4 font-medium">Week-5</th>
                  <th className="px-5 py-4 font-medium">Week-6</th>
                  <th className="px-5 py-4 font-medium">Total Correct</th>
                  <th className="px-5 py-4 font-medium">LMS %</th>
                  <th className="px-5 py-4 font-medium">Risk</th>
                </tr>
              </thead>
              <tbody>
                {lmsActivityRows.map((row) => (
                  <tr key={row.registrationNumber} className="border-t border-slate-100 bg-white">
                    <td className="px-5 py-4 text-slate-600">{row.serialNumber}</td>
                    <td className="px-5 py-4 font-medium text-ink">{row.registrationNumber}</td>
                    <td className="px-5 py-4 text-ink">{row.name}</td>
                    <td className="px-5 py-4 text-slate-600">{row.counselorName || "-"}</td>
                    <td className="px-5 py-4 text-slate-600">{row.section || "-"}</td>
                    {row.weekScores.map((score, index) => (
                      <td key={`${row.registrationNumber}-week-${index + 1}`} className="px-5 py-4 font-medium text-ink">
                        {score}
                      </td>
                    ))}
                    <td className="px-5 py-4 font-medium text-ink">{row.totalCorrect}</td>
                    <td className="px-5 py-4 font-medium text-ink">{row.lmsPercentage}%</td>
                    <td className="px-5 py-4 font-medium text-ink">{row.riskLevel}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {subjectAttendanceRows.length > 0 ? (
        <section ref={attendanceSectionRef} className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-tide">Attendance View</p>
              <h2 className="mt-2 font-display text-2xl text-ink">{subjectAttendanceTitle}</h2>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-ink">
                {subjectAttendanceRows.length} students
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
          </div>

          <div className="overflow-x-auto rounded-3xl border border-slate-100">
            <table className="min-w-[1400px] text-left text-sm">
              <thead className="bg-ink text-white">
                <tr>
                  <th className="px-5 py-4 font-medium">S.No</th>
                  <th className="px-5 py-4 font-medium">Reg No</th>
                  <th className="px-5 py-4 font-medium">Name</th>
                  <th className="px-5 py-4 font-medium">Counselor</th>
                  <th className="px-5 py-4 font-medium">Section</th>
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
                    <td className="px-5 py-4 text-slate-600">{row.serialNumber}</td>
                    <td className="px-5 py-4 font-medium text-ink">{row.registrationNumber}</td>
                    <td className="px-5 py-4 text-ink">{row.name}</td>
                    <td className="px-5 py-4 text-slate-600">{row.counselorName || "-"}</td>
                    <td className="px-5 py-4 text-slate-600">{row.section || "-"}</td>
                    {subjectAttendanceColumns.map((subject) => {
                      const value = row.subjectAttendance[subject] ?? "-";
                      const numericValue = Number.parseFloat(String(value));
                      const isLowAttendance = !Number.isNaN(numericValue) && numericValue < 75;
                      return (
                        <td
                          key={subject}
                          className={`px-5 py-4 font-medium ${isLowAttendance ? "text-red-600" : "text-ink"}`}
                        >
                          {value}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {marksStudent ? (
        <section ref={marksSectionRef} className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-tide">Marks View</p>
              <h2 className="mt-2 font-display text-2xl text-ink">{marksTitle}</h2>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-ink">
                {marksStudent.subject_attendance.length} subjects
              </div>
              <button
                type="button"
                onClick={() => {
                  setMarksStudent(null);
                  setMarksTitle("Subject-Wise Internal Marks");
                }}
                className="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white p-2 text-slate-600 transition hover:border-slate-300 hover:text-ink"
                aria-label="Close marks view"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-[1.5rem] border border-slate-200 bg-white">
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
                {marksStudent.subject_attendance.map((item) => (
                  <tr key={item.subject_name} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-semibold text-ink">{item.subject_name}</td>
                    <td className="px-4 py-3">{hasInternalMarks(item) ? formatMark(item.pre_t1_marks) : EMPTY_MARK}</td>
                    <td className="px-4 py-3">{hasInternalMarks(item) ? formatMark(item.t1_marks) : EMPTY_MARK}</td>
                    <td className="px-4 py-3">{hasInternalMarks(item) ? formatMark(item.t2_marks) : EMPTY_MARK}</td>
                    <td className="px-4 py-3">{hasInternalMarks(item) ? formatMark(item.t3_marks) : EMPTY_MARK}</td>
                    <td className="px-4 py-3">{hasInternalMarks(item) ? formatMark(item.t4_marks) : EMPTY_MARK}</td>
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
                {marksStudent.subject_attendance.map((item) => (
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
      ) : null}

      <section className="rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
        <div className="mb-5 flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="flex-1">
            <p className="text-xs uppercase tracking-[0.22em] text-tide">Active Filters</p>
            <div className="mt-3 flex flex-wrap justify-start gap-2">
              {activeFilters.length > 0 ? (
                activeFilters.map((item) => (
                  <span
                    key={item}
                    className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-ink"
                  >
                    {item}
                  </span>
                ))
              ) : (
                <span className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-500">
                  No specific filters selected. Showing all students.
                </span>
              )}
            </div>
          </div>

          <div className="w-full xl:max-w-md">
            <div className="relative">
              <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    handleSearchSubmit();
                  }
                }}
                placeholder="Search students"
                className="w-full rounded-2xl border border-slate-200 py-3 pl-11 pr-16 text-sm text-ink outline-none focus:border-tide sm:py-4 sm:pr-[10.5rem] sm:text-base"
              />
              <button
                type="button"
                onClick={handleSearchSubmit}
                aria-label="Search"
                className="absolute right-2 top-1/2 inline-flex -translate-y-1/2 items-center justify-center rounded-2xl bg-tide px-3 py-3 text-base font-semibold text-white shadow-soft sm:px-5 sm:py-3.5"
              >
                <Search size={20} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-3 md:hidden">
          {students.map((student) => (
            <div key={student.id} className="rounded-[1.5rem] border border-slate-200 bg-white px-4 py-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-semibold text-ink">{student.name}</div>
                  <div className="truncate text-sm text-slate-500">{student.email}</div>
                  <div className="mt-1 text-sm text-slate-500">{student.registration_number}</div>
                </div>
                <RiskBadge level={student.latest_risk_level ?? "Low"} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-2xl bg-slate-50 px-3 py-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">CGPA</p>
                  <p className="mt-1 font-semibold text-ink">{student.gpa.toFixed(2)}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 px-3 py-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Marks %</p>
                  <button
                    type="button"
                    onClick={() => viewSingleStudentMarks(student)}
                    className="mt-1 font-semibold text-ink underline-offset-4 hover:text-[#26459d] hover:underline"
                  >
                    {student.marks.toFixed(2)}%
                  </button>
                </div>
                <div className="rounded-2xl bg-slate-50 px-3 py-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Attendance</p>
                  <button
                    type="button"
                    onClick={() => viewSingleStudentAttendance(student)}
                    className="mt-1 font-semibold text-ink underline-offset-4 hover:text-[#26459d] hover:underline"
                  >
                    {student.attendance.toFixed(0)}%
                  </button>
                </div>
                <div className="rounded-2xl bg-slate-50 px-3 py-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">LMS</p>
                  <button
                    type="button"
                    onClick={() => viewSingleStudentLms(student)}
                    className="mt-1 font-semibold text-ink underline-offset-4 hover:text-[#26459d] hover:underline"
                  >
                    {student.lms_activity_percentage.toFixed(0)}%
                  </button>
                </div>
                <div className="rounded-2xl bg-slate-50 px-3 py-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Fees</p>
                  <p className="mt-1 font-semibold text-ink">{student.fees_paid_status}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 px-3 py-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Section</p>
                  <p className="mt-1 font-semibold text-ink">{student.section || "-"}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 px-3 py-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Year</p>
                  <p className="mt-1 font-semibold text-ink">{student.year}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="hidden overflow-x-auto rounded-3xl border border-slate-100 md:block">
          <table className="min-w-[1240px] w-full table-fixed text-left text-sm">
            <colgroup>
              <col className="w-[14%]" />
              <col className="w-[21%]" />
              <col className="w-[15%]" />
              <col className="w-[8%]" />
              <col className="w-[8%]" />
              <col className="w-[7%]" />
              <col className="w-[7%]" />
              <col className="w-[8%]" />
              <col className="w-[9%]" />
              <col className="w-[9%]" />
              <col className="w-[9%]" />
              <col className="w-[9%]" />
              <col className="w-[11%]" />
            </colgroup>
            <thead className="bg-ink text-white">
              <tr>
                <th className="px-6 py-4 font-medium">Reg No</th>
                <th className="px-6 py-4 font-medium">Student</th>
                <th className="px-6 py-4 font-medium">Counselor</th>
                <th className="px-6 py-4 font-medium">Section</th>
                <th className="px-6 py-4 font-medium">Gender</th>
                <th className="px-6 py-4 font-medium">Age</th>
                <th className="px-6 py-4 font-medium">Year</th>
                <th className="px-6 py-4 font-medium">CGPA</th>
                <th className="px-6 py-4 font-medium">Marks %</th>
                <th className="px-6 py-4 font-medium">Attendance</th>
                <th className="px-6 py-4 font-medium">LMS %</th>
                <th className="px-6 py-4 font-medium">Fees</th>
                <th className="px-6 py-4 font-medium">Risk</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr key={student.id} className="border-b border-slate-100 bg-white">
                  <td className="px-6 py-4 align-top font-medium text-ink">
                    <button
                      type="button"
                      onClick={() => openStudentPredictions(navigate, student)}
                      className="text-left underline-offset-4 hover:text-[#26459d] hover:underline"
                    >
                      {student.registration_number}
                    </button>
                  </td>
                  <td className="px-6 py-4 align-top">
                    <div className="font-semibold text-ink">{student.name}</div>
                    <div className="truncate text-slate-500">{student.email}</div>
                  </td>
                  <td className="px-6 py-4 align-top">{student.counselor_name ?? "Unassigned"}</td>
                  <td className="px-6 py-4 align-top">{student.section || "-"}</td>
                  <td className="px-6 py-4 align-top">{student.gender || "-"}</td>
                  <td className="px-6 py-4 align-top">{student.age ?? "-"}</td>
                  <td className="px-6 py-4 align-top">{student.year}</td>
                  <td className="px-6 py-4 align-top">{student.gpa.toFixed(2)}</td>
                  <td className="px-6 py-4 align-top">
                    <button
                      type="button"
                      onClick={() => viewSingleStudentMarks(student)}
                      className="font-medium text-ink underline-offset-4 hover:text-[#26459d] hover:underline"
                    >
                      {student.marks.toFixed(2)}%
                    </button>
                  </td>
                  <td className="px-6 py-4 align-top">
                    <button
                      type="button"
                      onClick={() => viewSingleStudentAttendance(student)}
                      className="font-medium text-ink underline-offset-4 hover:text-[#26459d] hover:underline"
                    >
                      {student.attendance.toFixed(0)}%
                    </button>
                  </td>
                  <td className="px-6 py-4 align-top">
                    <button
                      type="button"
                      onClick={() => viewSingleStudentLms(student)}
                      className="font-medium text-ink underline-offset-4 hover:text-[#26459d] hover:underline"
                    >
                      {student.lms_activity_percentage.toFixed(0)}%
                    </button>
                  </td>
                  <td className="px-6 py-4 align-top">{student.fees_paid_status}</td>
                  <td className="px-6 py-4 align-top">
                    <RiskBadge level={student.latest_risk_level ?? "Low"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <div className="text-sm text-slate-500">
            Showing {totalStudents === 0 ? 0 : (currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, totalStudents)} of {totalStudents}
          </div>
          <div className="flex w-full items-center gap-3 sm:w-auto">
            <button
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={currentPage === 1}
              className="flex-1 rounded-2xl border border-slate-200 px-4 py-2 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:text-slate-300 sm:flex-none"
            >
              Previous
            </button>
            <div className="text-sm text-slate-500">
              Page {currentPage} of {totalPages}
            </div>
            <button
              onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
              disabled={currentPage >= totalPages}
              className="flex-1 rounded-2xl border border-slate-200 px-4 py-2 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:text-slate-300 sm:flex-none"
            >
              Next
            </button>
          </div>
        </div>
      </section>

      {error ? <div className="rounded-3xl bg-red-50 px-5 py-4 text-red-700 shadow-soft">{error}</div> : null}
    </div>
  );
}
