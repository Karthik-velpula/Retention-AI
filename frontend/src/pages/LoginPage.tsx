import axios from "axios";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlarmClock,
  ArrowRight,
  FlaskConical,
  IdCard,
  Lightbulb,
  Lock,
  MonitorSmartphone,
  Plus,
  X,
} from "lucide-react";
import { Navigate } from "react-router-dom";

import { confirmPasswordReset, login, requestPasswordReset } from "../api/endpoints";
import vignanLogo from "../assets/vignan-logo-deemed.svg";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { token, acceptLogin } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [showRecoveryHelp, setShowRecoveryHelp] = useState(false);
  const [recoveryUsername, setRecoveryUsername] = useState("");
  const [recoveryOtp, setRecoveryOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [recoveryMessage, setRecoveryMessage] = useState("");
  const [recoveryError, setRecoveryError] = useState("");
  const [otpRequested, setOtpRequested] = useState(false);
  const [otpTimeLeft, setOtpTimeLeft] = useState(0);

  if (token) {
    return <Navigate to="/dashboard" replace />;
  }

  useEffect(() => {
    if (!otpRequested || otpTimeLeft <= 0) return;
    const timer = window.setInterval(() => {
      setOtpTimeLeft((current) => {
        if (current <= 1) {
          window.clearInterval(timer);
          return 0;
        }
        return current - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [otpRequested, otpTimeLeft]);

  const passwordRules = useMemo(
    () => [
      { label: "At least 8 characters", valid: newPassword.length >= 8 },
      { label: "One uppercase letter", valid: /[A-Z]/.test(newPassword) },
      { label: "One lowercase letter", valid: /[a-z]/.test(newPassword) },
      { label: "One number", valid: /\d/.test(newPassword) },
      { label: "One special character", valid: /[^A-Za-z0-9]/.test(newPassword) },
    ],
    [newPassword]
  );

  const isPasswordValid = passwordRules.every((rule) => rule.valid);
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmNewPassword;
  const otpExpired = otpRequested && otpTimeLeft === 0;
  const otpTimerLabel = `${String(Math.floor(otpTimeLeft / 60)).padStart(2, "0")}:${String(otpTimeLeft % 60).padStart(2, "0")}`;

  const extractApiError = (fallback: string, caught: unknown) => {
    if (axios.isAxiosError(caught)) {
      const detail = caught.response?.data?.detail;
      if (typeof detail === "string" && detail.trim()) return detail;
    }
    return fallback;
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      setError("");
      const response = await login(username, password);
      acceptLogin(response);
    } catch (caught) {
      setError(extractApiError("Incorrect login ID or password.", caught));
    }
  };

  const handleRequestOtp = async () => {
    try {
      setRecoveryError("");
      setRecoveryMessage("");
      const response = await requestPasswordReset(recoveryUsername);
      setOtpRequested(true);
      setOtpTimeLeft(180);
      setRecoveryOtp("");
      setNewPassword("");
      setConfirmNewPassword("");
      setRecoveryMessage(response.detail);
    } catch (caught) {
      setRecoveryError(extractApiError("Unable to send OTP. Check the login ID/email and backend mail configuration.", caught));
    }
  };

  const handleResetPassword = async () => {
    if (!isPasswordValid) {
      setRecoveryError("New password does not meet the required rules.");
      return;
    }
    if (!passwordsMatch) {
      setRecoveryError("New password and confirm password do not match.");
      return;
    }
    if (otpExpired) {
      setRecoveryError("OTP expired. Please request a new OTP.");
      return;
    }
    try {
      setRecoveryError("");
      const response = await confirmPasswordReset(recoveryUsername, recoveryOtp, newPassword);
      setRecoveryMessage(response.detail);
      setRecoveryOtp("");
      setNewPassword("");
      setConfirmNewPassword("");
      setOtpRequested(false);
      setOtpTimeLeft(0);
    } catch (caught) {
      setRecoveryError(extractApiError("Unable to reset password. Check the OTP and try again.", caught));
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[linear-gradient(180deg,#f7f8fc_0%,#eff2f9_100%)] px-4 py-8">
      <div className="pointer-events-none absolute inset-0 opacity-70">
        <div className="absolute left-[5%] top-[14%] text-[#d6ddef]">
          <Plus size={68} strokeWidth={1.5} />
        </div>
        <div className="absolute right-[11%] top-[10%] text-[#cbd4ea]">
          <Plus size={76} strokeWidth={1.5} />
        </div>
        <div className="absolute left-[1%] top-[30%] text-[#d5dbef]">
          <AlarmClock size={152} strokeWidth={1.1} />
        </div>
        <div className="absolute left-[2%] bottom-[16%] text-[#eadb8f]">
          <Lightbulb size={150} strokeWidth={1.1} />
        </div>
        <div className="absolute right-[3%] top-[25%] text-[#d5dced]">
          <FlaskConical size={185} strokeWidth={1.1} />
        </div>
        <div className="absolute right-[4%] bottom-[16%] text-[#d9dfef]">
          <MonitorSmartphone size={170} strokeWidth={1.1} />
        </div>
      </div>

      <div className="relative w-full max-w-4xl rounded-[2.8rem] bg-white/95 px-5 py-7 shadow-[0_30px_70px_rgba(99,113,156,0.16)] sm:px-10 md:px-14 md:py-10">
        <div className="mx-auto max-w-3xl">
          <div className="text-center">
            <div className="inline-flex flex-col items-center">
              <img
                src={vignanLogo}
                alt="Vignan's Foundation for Science, Technology and Research"
                className="h-28 w-auto object-contain sm:h-36"
              />
            </div>
            <div className="mt-3 text-2xl font-black tracking-tight text-[#27439a] sm:text-[2.1rem]">RETENTION PORTAL</div>
          </div>

          <form onSubmit={handleSubmit} className="mt-9 space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-black uppercase tracking-[0.22em] text-[#505c73]">Login ID</label>
                <div className="mt-2 flex items-center rounded-2xl border border-[#ccd5ea] bg-white px-4 py-3 shadow-[0_4px_12px_rgba(142,155,191,0.08)]">
                  <IdCard size={18} className="mr-3 text-[#8d99b4]" />
                  <input
                    value={username}
                    onChange={(event) => setUsername(event.target.value.toUpperCase())}
                    className="w-full bg-transparent text-sm text-[#31415d] outline-none placeholder:text-[#9aa7bf]"
                    placeholder="Enter Login ID"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-black uppercase tracking-[0.22em] text-[#505c73]">Password</label>
                <div className="mt-2 flex items-center rounded-2xl border border-[#ccd5ea] bg-white px-4 py-3 shadow-[0_4px_12px_rgba(142,155,191,0.08)]">
                  <Lock size={18} className="mr-3 text-[#8d99b4]" />
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="w-full bg-transparent text-sm text-[#31415d] outline-none placeholder:text-[#9aa7bf]"
                    placeholder="Enter Password"
                  />
                </div>
              </div>
            </div>

            {showRecoveryHelp ? (
              <div className="space-y-4 rounded-[1.5rem] border border-sky-200 bg-sky-50 px-4 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <label className="text-sm font-medium text-sky-900">Employee ID</label>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowRecoveryHelp(false)}
                    className="rounded-full border border-sky-200 bg-white p-2 text-sky-700 transition hover:bg-sky-100"
                    aria-label="Close forgot password panel"
                  >
                    <X size={16} />
                  </button>
                </div>
                <div>
                  <input
                    value={recoveryUsername}
                    onChange={(event) => setRecoveryUsername(event.target.value)}
                    className="mt-2 w-full rounded-[1.1rem] border border-sky-200 bg-white px-4 py-3 text-ink outline-none focus:border-tide"
                    placeholder="Enter your employee ID"
                  />
                </div>

                {otpRequested ? (
                  <>
                    <div className="flex flex-col gap-3 rounded-[1.1rem] border border-sky-200 bg-white px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                      <div className="text-sky-900">
                        {otpExpired ? "OTP expired" : `OTP expires in ${otpTimerLabel}`}
                      </div>
                      <button
                        type="button"
                        onClick={handleRequestOtp}
                        disabled={!otpExpired}
                        className="font-semibold text-tide transition hover:text-ink disabled:cursor-not-allowed disabled:text-slate-400"
                      >
                        Resend OTP
                      </button>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-sky-900">OTP</label>
                      <input
                        value={recoveryOtp}
                        onChange={(event) => setRecoveryOtp(event.target.value)}
                        className="mt-2 w-full rounded-[1.1rem] border border-sky-200 bg-white px-4 py-3 text-ink outline-none focus:border-tide"
                        placeholder="Enter the OTP from your email"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-sky-900">New Password</label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(event) => setNewPassword(event.target.value)}
                        className="mt-2 w-full rounded-[1.1rem] border border-sky-200 bg-white px-4 py-3 text-ink outline-none focus:border-tide"
                        placeholder="Enter your new password"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-sky-900">Confirm Password</label>
                      <input
                        type="password"
                        value={confirmNewPassword}
                        onChange={(event) => setConfirmNewPassword(event.target.value)}
                        className="mt-2 w-full rounded-[1.1rem] border border-sky-200 bg-white px-4 py-3 text-ink outline-none focus:border-tide"
                        placeholder="Confirm your new password"
                      />
                      {confirmNewPassword ? (
                        <div className={`mt-2 text-xs ${passwordsMatch ? "text-emerald-700" : "text-red-600"}`}>
                          {passwordsMatch ? "Passwords match." : "Passwords do not match."}
                        </div>
                      ) : null}
                    </div>
                    <div className="rounded-[1.1rem] border border-slate-200 bg-white px-4 py-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Password Rules</p>
                      <div className="mt-3 space-y-2 text-sm">
                        {passwordRules.map((rule) => (
                          <div key={rule.label} className={rule.valid ? "text-emerald-700" : "text-slate-500"}>
                            {rule.valid ? "✓" : "•"} {rule.label}
                          </div>
                        ))}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleResetPassword}
                      disabled={otpExpired}
                      className="w-full rounded-[1.1rem] bg-ink px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
                    >
                      Reset Password
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={handleRequestOtp}
                    className="w-full rounded-[1.1rem] bg-ink px-4 py-3 font-semibold text-white"
                  >
                    Send OTP
                  </button>
                )}

                {recoveryMessage ? (
                  <div className="rounded-[1.1rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                    {recoveryMessage}
                  </div>
                ) : null}
                {recoveryError ? (
                  <div className="rounded-[1.1rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {recoveryError}
                  </div>
                ) : null}

                <div className="text-xs leading-6 text-sky-900/80">
                  Enter your login ID or email. The system will send an OTP to the email linked to that account. The OTP stays valid for 3 minutes.
                </div>
              </div>
            ) : null}

            {error ? (
              <div className="rounded-[1.1rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              className="inline-flex w-full items-center justify-center gap-3 rounded-[0.95rem] bg-[#31489d] px-4 py-3.5 text-sm font-black uppercase tracking-[0.2em] text-white shadow-[0_15px_28px_rgba(49,72,157,0.26)] transition hover:bg-[#273d8c]"
            >
              Sign In To Workspace
              <ArrowRight size={18} />
            </button>

            <div className="flex flex-wrap items-center justify-center gap-3 text-xs font-semibold text-[#677496]">
              <button type="button" onClick={() => setShowRecoveryHelp((current) => !current)} className="transition hover:text-[#31489d]">
                Forgot Password?
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
