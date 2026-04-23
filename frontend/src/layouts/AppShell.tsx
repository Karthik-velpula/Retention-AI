import { ReactNode, useMemo, useState } from "react";
import {
  BarChart3,
  BellRing,
  BookOpenCheck,
  BrainCircuit,
  CalendarClock,
  ChevronDown,
  ClipboardCheck,
  Funnel,
  LogOut,
  Menu,
  ShieldCheck,
  X,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import vignanLogo from "../assets/vignan-logo-deemed.svg";
import VoiceAssistant from "../components/VoiceAssistant";

export default function AppShell({ children }: { children: ReactNode }) {
  const { logout, role, name, lastLoginAt } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [desktopMenuOpen, setDesktopMenuOpen] = useState(true);
  const navItems = useMemo(
    () => [
      { to: "/", label: "Dashboard", icon: <BarChart3 size={18} />, show: true },
      { to: "/students", label: "AI Predictions", icon: <BrainCircuit size={18} />, show: true },
      { to: "/filters", label: "Filters", icon: <Funnel size={18} />, show: true },
      { to: "/interventions", label: "Interventions", icon: <ClipboardCheck size={18} />, show: role === "faculty" },
      { to: "/follow-ups", label: "Next Follow-Ups", icon: <CalendarClock size={18} />, show: role === "faculty" },
      { to: "/alerts", label: "Alerts", icon: <BellRing size={18} />, show: true },
      { to: "/admin", label: "Admin Console", icon: <ShieldCheck size={18} />, show: role === "admin" },
      { to: "/advising", label: "Advising", icon: <BookOpenCheck size={18} />, show: true },
    ].filter((item) => item.show),
    [role]
  );
  const lastLoginLabel = useMemo(() => {
    if (!lastLoginAt) return null;
    const normalizedLastLoginAt =
      /[zZ]|[+\-]\d{2}:\d{2}$/.test(lastLoginAt) ? lastLoginAt : `${lastLoginAt}Z`;
    const parsed = new Date(normalizedLastLoginAt);
    if (Number.isNaN(parsed.getTime())) return null;
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
      timeZone: "Asia/Kolkata",
    }).format(parsed);
  }, [lastLoginAt]);

  return (
    <div className="min-h-screen">
      <header className="border-b border-[#d7deef] bg-white shadow-[0_8px_24px_rgba(15,23,42,0.05)]">
        <div className="h-2 w-full bg-[linear-gradient(90deg,#111827_0%,#111827_28%,#ef5350_28%,#ef5350_94%,#1e88e5_94%,#1e88e5_100%)]" />
        <div className="px-3 py-4 sm:px-4 md:px-8">
          <div className="flex items-center justify-between gap-3 xl:hidden">
            <button
              type="button"
              onClick={() => setMenuOpen((current) => !current)}
              className="rounded-2xl border border-slate-200 bg-white p-3 text-ink shadow-sm"
              aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
            >
              {menuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <div className="min-w-0 flex-1">
              <h1 className="text-lg font-black tracking-tight text-ink sm:text-xl">Vignan's Retention Portal</h1>
              {name ? <p className="mt-1 text-xs font-semibold text-[#26459d]">Logged in as {name}</p> : null}
              {lastLoginLabel ? <p className="mt-1 text-xs font-medium text-slate-500">Last login: {lastLoginLabel}</p> : null}
            </div>
          </div>

          <div className="hidden items-center justify-between gap-8 xl:flex">
            <div className="flex min-w-fit items-center gap-4">
              <button
                type="button"
                onClick={() => setDesktopMenuOpen((current) => !current)}
                className="rounded-2xl border border-slate-200 bg-white p-3 text-ink shadow-sm"
                aria-label={desktopMenuOpen ? "Hide navigation menu" : "Show navigation menu"}
              >
                {desktopMenuOpen ? <X size={20} /> : <Menu size={20} />}
              </button>
              <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-2xl border border-[#cbd6f1] bg-white shadow-sm">
                <img src={vignanLogo} alt="Vignan's logo" className="h-full w-full object-contain p-1" />
              </div>
              <div>
                <div className="text-[2rem] font-black leading-none tracking-tight text-[#ea4335]">VIGNAN'S</div>
                <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-slate-500">
                  Foundation for Science, Technology & Research
                </div>
                <div className="text-[11px] font-semibold text-slate-400">(Deemed to be University)</div>
              </div>
            </div>

            <div className="min-w-fit">
              {name ? <p className="mb-1 text-right text-sm font-semibold text-[#26459d]">Logged in as {name}</p> : null}
              {lastLoginLabel ? <p className="mb-1 text-right text-[11px] font-medium text-slate-500">Last login: {lastLoginLabel}</p> : null}
              <button
                onClick={logout}
                className="flex min-w-fit items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
              >
                <LogOut size={18} /> Sign out
              </button>
            </div>
          </div>

          {desktopMenuOpen ? (
            <div className="hidden xl:block">
              <nav className="mt-4 flex items-center gap-1 overflow-x-auto border-t border-slate-200 pt-4">
                {navItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `flex min-w-fit items-center gap-1 rounded-xl px-3 py-2 text-sm font-black uppercase tracking-[0.08em] transition ${
                        isActive ? "bg-[#f3f6ff] text-[#26459d]" : "text-[#2b2f36] hover:bg-slate-50"
                      }`
                    }
                  >
                    <span>{item.label}</span>
                    <ChevronDown size={14} strokeWidth={2.2} />
                  </NavLink>
                ))}
              </nav>
            </div>
          ) : null}

          {menuOpen ? (
            <div className="mt-4 space-y-2 border-t border-slate-200 pt-4 xl:hidden">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3 rounded-2xl px-4 py-3 text-ink hover:bg-slate-50"
                >
                  {item.icon} {item.label}
                </NavLink>
              ))}
              <button
                onClick={logout}
                className="flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 px-4 py-3 text-slate-700 hover:bg-slate-50"
              >
                <LogOut size={18} /> Sign out
              </button>
            </div>
          ) : null}
        </div>
      </header>

      <main className="px-3 py-4 sm:px-4 sm:py-6 md:px-8">
        {children}
      </main>

      <VoiceAssistant />
    </div>
  );
}
