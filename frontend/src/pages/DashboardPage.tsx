import { Activity, AlertTriangle, GraduationCap, Siren, Wallet } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";

import { fetchAnalytics } from "../api/endpoints";
import StatCard from "../components/StatCard";
import { AnalyticsData } from "../types";

const riskColors = ["#2fbf71", "#a3e635", "#f4d35e", "#ff7f51"];

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAnalytics().then(setAnalytics).catch(() => undefined);
  }, []);

  if (!analytics) {
    return <div className="rounded-[2rem] bg-white p-8 shadow-soft">Loading analytics...</div>;
  }

  return (
    <div className="space-y-6">
      <section className="min-w-0 rounded-[2rem] bg-white p-5 shadow-soft sm:p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-tide">Overview</p>
        <h1 className="mt-3 font-display text-3xl text-ink sm:text-4xl">Predictive Student Retention Dashboard</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600 sm:text-base">
          This dashboard combines academic, LMS, and financial indicators to prioritize intervention and explain which factors are driving risk.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-6">
        <StatCard label="Students" value={String(analytics.kpis.total_students)} icon={<GraduationCap />} />
        <button type="button" onClick={() => navigate("/filters?risk=High&attendance=Below%2075%25")} className="text-left">
          <StatCard label="Need Action Today" value={String(analytics.kpis.action_needed_today)} icon={<Siren />} tone="bg-red-100" />
        </button>
        <button type="button" onClick={() => navigate("/filters?risk=Safe")} className="text-left">
          <StatCard label="Safe" value={String(analytics.kpis.safe_risk_students)} icon={<Activity />} tone="bg-emerald-50" />
        </button>
        <button type="button" onClick={() => navigate("/filters?risk=Low")} className="text-left">
          <StatCard label="Low Risk" value={String(analytics.kpis.low_risk_students)} icon={<Activity />} tone="bg-lime-50" />
        </button>
        <button type="button" onClick={() => navigate("/filters?risk=Medium")} className="text-left">
          <StatCard label="Medium Risk" value={String(analytics.kpis.medium_risk_students)} icon={<AlertTriangle />} tone="bg-amber-50" />
        </button>
        <button type="button" onClick={() => navigate("/filters?risk=High")} className="text-left">
          <StatCard label="High Risk" value={String(analytics.kpis.high_risk_students)} icon={<AlertTriangle />} tone="bg-red-50" />
        </button>
        <StatCard label="Avg GPA" value={analytics.kpis.average_gpa.toFixed(2)} icon={<Activity />} tone="bg-sand/20" />
        <StatCard label="Avg Attendance" value={`${analytics.kpis.average_attendance.toFixed(1)}%`} icon={<Wallet />} tone="bg-mint/20" />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="min-w-0 overflow-hidden rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
          <h2 className="font-display text-xl text-ink sm:text-2xl">Risk Distribution</h2>
          <div className="mt-4 h-64 sm:mt-6 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={analytics.risk_distribution} dataKey="value" nameKey="label" outerRadius="72%">
                  {analytics.risk_distribution.map((entry, index) => (
                    <Cell key={entry.label} fill={riskColors[index % riskColors.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="min-w-0 overflow-hidden rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
          <h2 className="font-display text-xl text-ink sm:text-2xl">Department Risk Scores</h2>
          <div className="mt-4 h-64 sm:mt-6 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics.department_risk}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={56} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#1b4965" radius={[12, 12, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="min-w-0 overflow-hidden rounded-[2rem] bg-white p-5 shadow-soft sm:p-6">
        <h2 className="font-display text-xl text-ink sm:text-2xl">Attendance vs GPA</h2>
        <div className="mt-4 h-72 sm:mt-6 sm:h-96">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="attendance" name="Attendance" unit="%" tick={{ fontSize: 11 }} />
              <YAxis type="number" dataKey="gpa" name="GPA" tick={{ fontSize: 11 }} width={34} />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Scatter data={analytics.attendance_vs_gpa} fill="#ff7f51" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
