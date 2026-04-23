import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Bot, Mic, MicOff, Send, Square, Volume2, VolumeX, X } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { askAssistant } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";

type AssistantMessage = {
  id: number;
  role: "assistant" | "user";
  content: string;
};

type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionEventLike = {
  results: ArrayLike<{
    0: {
      transcript: string;
    };
  }>;
};

declare global {
  interface Window {
    webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
    SpeechRecognition?: new () => SpeechRecognitionInstance;
  }
}

const initialMessage = "Voice assistant is ready.";

function extractTargetPhrase(query: string) {
  const trimmed = query.trim();
  const forMatch = trimmed.match(/\b(?:for|of)\s+(.+)$/i);
  if (forMatch?.[1]) return forMatch[1].trim();
  const whoMatch = trimmed.match(/\b(?:student|reg(?:istration)?(?: number)?)\s+(.+)$/i);
  if (whoMatch?.[1]) return whoMatch[1].trim();
  return trimmed;
}

export default function VoiceAssistant() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, role } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("Tap the mic and speak.");
  const [messages, setMessages] = useState<AssistantMessage[]>([
    { id: 1, role: "assistant", content: initialMessage },
  ]);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const messageIdRef = useRef(2);
  const conversationEndRef = useRef<HTMLDivElement | null>(null);

  const speechSupported = useMemo(
    () => typeof window !== "undefined" && ("speechSynthesis" in window) && (!!window.SpeechRecognition || !!window.webkitSpeechRecognition),
    []
  );

  useEffect(() => {
    if (!speechSupported || recognitionRef.current) return;
    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Recognition) return;

    const recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-IN";
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join(" ")
        .trim();
      if (transcript) {
        void submitQuery(transcript);
      }
    };
    recognition.onerror = (event) => {
      setStatus(event.error === "not-allowed" ? "Microphone permission was denied." : "Voice capture failed. Try again.");
      setIsListening(false);
    };
    recognition.onend = () => {
      setIsListening(false);
    };
    recognitionRef.current = recognition;
  }, [speechSupported]);

  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const pushMessage = (roleType: "assistant" | "user", content: string) => {
    setMessages((current) => [...current, { id: messageIdRef.current++, role: roleType, content }]);
  };

  const speak = (text: string) => {
    if (isMuted || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-IN";
    utterance.rate = 1;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  };

  const handleCommand = async (query: string) => {
    const normalized = query.trim().toLowerCase();

    if (normalized.includes("help") || normalized.includes("what can you do")) {
      return "You can ask me to open pages, filter safe low medium or high risk students, show unpaid students, or open attendance, LMS, or marks for a student.";
    }

    if (normalized.includes("open dashboard")) {
      navigate("/dashboard");
      return "Opening dashboard.";
    }
    if (normalized.includes("open students") || normalized.includes("open predictions")) {
      navigate("/students");
      return "Opening students and AI predictions.";
    }
    if (normalized.includes("open filters") || normalized.includes("open filter")) {
      navigate("/filters");
      return "Opening filters page.";
    }
    if (normalized.includes("clear filters") || normalized.includes("clear all filters")) {
      navigate("/filters");
      return "Clearing filters and opening the full filter page.";
    }
    if (normalized.includes("open alerts")) {
      navigate("/alerts");
      return "Opening alerts page.";
    }
    if (normalized.includes("open advising")) {
      navigate("/advising");
      return "Opening advising page.";
    }
    if (normalized.includes("open interventions") && role === "faculty") {
      navigate("/interventions");
      return "Opening interventions page.";
    }
    if ((normalized.includes("open follow up") || normalized.includes("open follow-up")) && role === "faculty") {
      navigate("/follow-ups");
      return "Opening follow ups page.";
    }
    if (normalized.includes("open admin") && role === "admin") {
      navigate("/admin");
      return "Opening admin console.";
    }
    if (normalized.includes("sign out") || normalized.includes("logout") || normalized.includes("log out")) {
      logout();
      return "Signing out.";
    }
    if (normalized.includes("where am i") || normalized.includes("which page")) {
      return `You are currently on ${location.pathname === "/" || location.pathname === "/dashboard" ? "dashboard" : location.pathname.replace("/", "")}.`;
    }

    if (
      normalized.includes("subject wise attendance") ||
      normalized.includes("subject-wise attendance") ||
      normalized.includes("show attendance for") ||
      normalized.includes("open attendance for")
    ) {
      const target = extractTargetPhrase(query);
      navigate(`/filters?query=${encodeURIComponent(target)}&focus=attendance`);
      return `Opening subject-wise attendance for ${target}.`;
    }

    if (
      normalized.includes("open marks for") ||
      normalized.includes("show marks for") ||
      normalized.includes("subject wise marks") ||
      normalized.includes("subject-wise marks")
    ) {
      const target = extractTargetPhrase(query);
      navigate(`/filters?query=${encodeURIComponent(target)}&focus=marks`);
      return `Opening marks for ${target}.`;
    }

    if (
      normalized.includes("open lms for") ||
      normalized.includes("show lms for") ||
      normalized.includes("show lms activity for") ||
      normalized.includes("open lms activity for")
    ) {
      const target = extractTargetPhrase(query);
      navigate(`/filters?query=${encodeURIComponent(target)}&focus=lms`);
      return `Opening LMS activity for ${target}.`;
    }

    if (
      normalized.includes("show student ") ||
      normalized.includes("find student ") ||
      /^[0-9a-z ]{8,}$/i.test(query.trim())
    ) {
      const target = extractTargetPhrase(query);
      navigate(`/filters?query=${encodeURIComponent(target)}`);
      return `Opening filtered student results for ${target}.`;
    }

    if (
      normalized.includes("safe students") ||
      normalized.includes("low risk students") ||
      normalized.includes("medium risk students") ||
      normalized.includes("high risk students") ||
      normalized.includes("unpaid students") ||
      normalized.includes("paid students") ||
      normalized.includes("attendance below")
    ) {
      const params = new URLSearchParams();
      if (normalized.includes("safe")) params.set("risk", "Safe");
      else if (normalized.includes("low risk")) params.set("risk", "Low");
      else if (normalized.includes("medium risk")) params.set("risk", "Medium");
      else if (normalized.includes("high risk")) params.set("risk", "High");

      if (normalized.includes("unpaid")) params.set("fee", "Not Paid");
      else if (normalized.includes("paid")) params.set("fee", "Paid");

      const attendanceMatch = normalized.match(/attendance below\s*(65|75|85)/);
      if (attendanceMatch) {
        params.set("attendance", `Below ${attendanceMatch[1]}%`);
      }

      const sectionMatch = normalized.match(/section\s+(\d{1,2})/);
      if (sectionMatch) {
        params.set("section", sectionMatch[1]);
      }

      navigate(`/filters?${params.toString()}`);
      return "Opening filtered student data.";
    }

    const response = await askAssistant(query);
    return response.answer;
  };

  const submitQuery = async (query: string) => {
    const cleaned = query.trim();
    if (!cleaned) return;
    pushMessage("user", cleaned);
    setInput("");
    setStatus("Thinking...");
    try {
      const response = await handleCommand(cleaned);
      pushMessage("assistant", response);
      setStatus("Ready for the next question.");
      speak(response);
    } catch {
      const fallback = "I could not complete that request right now. Please try again.";
      pushMessage("assistant", fallback);
      setStatus("Something went wrong.");
      speak(fallback);
    }
  };

  const toggleListening = () => {
    const recognition = recognitionRef.current;
    if (!recognition) {
      setStatus("Voice recognition is not available in this browser.");
      return;
    }
    if (isListening) {
      recognition.stop();
      setIsListening(false);
      setStatus("Stopped listening.");
      return;
    }
    setStatus("Listening...");
    setIsListening(true);
    recognition.start();
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await submitQuery(input);
  };

  return (
    <>
      {isOpen ? (
        <section className="fixed bottom-24 right-5 z-50 flex h-[min(42rem,calc(100vh-7rem))] w-[min(22rem,calc(100vw-1.5rem))] flex-col overflow-hidden rounded-[1.7rem] border border-[#d8e1f1] bg-[linear-gradient(180deg,#fdfefe_0%,#f4f7fd_100%)] shadow-[0_22px_60px_rgba(20,39,84,0.18)] sm:bottom-24 sm:right-6">
          <div className="relative overflow-hidden border-b border-[#dbe3f2] bg-[linear-gradient(135deg,#0f2747_0%,#1c4d8c_55%,#3b82c4_100%)] px-4 py-3.5 text-white">
            <div className="absolute -right-8 -top-10 h-24 w-24 rounded-full bg-white/10 blur-sm" />
            <div className="absolute bottom-0 right-10 h-16 w-16 rounded-full bg-[#ffd36c]/15 blur-sm" />
            <div className="relative">
              <div className="min-w-0">
                <p className="text-[11px] uppercase tracking-[0.28em] text-white/70">Voice AI</p>
                <h3 className="mt-1 font-display text-[1.15rem] text-white">Counselor Copilot</h3>
                <p className="mt-1 max-w-xs text-xs leading-5 text-white/78">
                  Ask about students, attendance, fees, marks, LMS, or navigate the portal by voice.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="text-[11px] uppercase tracking-[0.22em] text-[#6a7fa4]">Session Status</p>
              <p className="mt-1 text-[13px] font-semibold text-ink">{status}</p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 rounded-full bg-[#eff4ff] px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#31558f]">
                <span className={`h-2.5 w-2.5 rounded-full ${isListening ? "bg-[#ff6f6f] shadow-[0_0_0_4px_rgba(255,111,111,0.14)]" : "bg-emerald-500"}`} />
                {isListening ? "Listening" : "Ready"}
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
              className="inline-flex items-center gap-2 rounded-full border border-[#d7dfed] bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:text-ink"
                aria-label="Close voice assistant"
              >
                <X size={18} />
                <span>Close</span>
              </button>
            </div>
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-3 px-4 pb-4">
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={toggleListening}
                className={`group relative overflow-hidden rounded-[1.2rem] px-3.5 py-3.5 text-left transition ${
                  isListening
                    ? "bg-[linear-gradient(135deg,#d84242_0%,#f06d6d_100%)] text-white shadow-[0_14px_32px_rgba(216,66,66,0.26)]"
                    : "bg-[linear-gradient(135deg,#143f76_0%,#2f66b1_100%)] text-white shadow-[0_14px_32px_rgba(20,63,118,0.22)]"
                }`}
                aria-label={isListening ? "Stop voice input" : "Start voice input"}
              >
                <div className="absolute -right-6 -top-6 h-16 w-16 rounded-full bg-white/10" />
                <div className="relative flex items-center justify-between">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.2em] text-white/70">Mic</p>
                    <p className="mt-1 text-[13px] font-semibold">{isListening ? "Stop Listening" : "Start Listening"}</p>
                  </div>
                  <div className="rounded-2xl bg-white/15 p-2.5">
                    {isListening ? <MicOff size={17} /> : <Mic size={17} />}
                  </div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setIsMuted((current) => !current)}
                className="rounded-[1.2rem] border border-[#d8e0ee] bg-white px-3.5 py-3.5 text-left shadow-[0_10px_24px_rgba(24,42,84,0.06)] transition hover:border-[#bfd0e9] hover:shadow-[0_14px_30px_rgba(24,42,84,0.08)]"
                aria-label={isMuted ? "Unmute speech reply" : "Mute speech reply"}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.2em] text-[#6a7fa4]">Speech Reply</p>
                    <p className="mt-1 text-[13px] font-semibold text-ink">{isMuted ? "Muted" : isSpeaking ? "Reading" : "Ready"}</p>
                  </div>
                  <div className="rounded-2xl bg-[#eef4ff] p-2.5 text-[#214d90]">
                    {isMuted ? <VolumeX size={17} /> : <Volume2 size={17} />}
                  </div>
                </div>
              </button>
            </div>

            {isSpeaking ? (
              <button
                type="button"
                onClick={stopSpeaking}
                className="inline-flex items-center justify-center gap-2 rounded-[1.1rem] border border-[#f1c9c9] bg-[#fff5f5] px-3.5 py-2.5 text-sm font-semibold text-[#b33d3d] transition hover:bg-[#ffecec]"
              >
                <Square size={15} />
                Stop Voice
              </button>
            ) : null}

            <div className="flex min-h-0 flex-1 flex-col rounded-[1.3rem] border border-[#d9e2f0] bg-white p-3 shadow-[0_14px_30px_rgba(24,42,84,0.06)]">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.22em] text-[#6a7fa4]">Conversation</p>
                  <p className="mt-1 text-xs text-slate-600">Your questions and AI replies appear here.</p>
                </div>
              </div>
              <div className="min-h-0 flex-1 space-y-2.5 overflow-y-auto pr-1">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`rounded-[1.1rem] px-3.5 py-3 text-sm leading-6 ${
                      message.role === "assistant"
                        ? "mr-5 border border-[#e0e7f3] bg-[#f7faff] text-slate-700"
                        : "ml-5 bg-[linear-gradient(135deg,#173f75_0%,#295fa7_100%)] text-white"
                    }`}
                  >
                    <p className={`mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${message.role === "assistant" ? "text-[#6a7fa4]" : "text-white/70"}`}>
                      {message.role === "assistant" ? "AI Reply" : "You"}
                    </p>
                    {message.content}
                  </div>
                ))}
                <div ref={conversationEndRef} />
              </div>
            </div>

            <form onSubmit={handleSubmit} className="rounded-[1.3rem] border border-[#d9e2f0] bg-white p-3 shadow-[0_14px_30px_rgba(24,42,84,0.06)]">
              <div className="flex items-center gap-2">
                <input
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="Ask anything about student data"
                  className="min-w-0 flex-1 rounded-[1rem] bg-[#f7faff] px-3.5 py-2.5 text-sm text-ink outline-none ring-1 ring-transparent placeholder:text-slate-400 focus:bg-white focus:ring-[#c7d8f2]"
                />
                <button
                  type="submit"
                  className="inline-flex items-center justify-center rounded-[1rem] bg-ink px-3.5 py-2.5 text-white transition hover:bg-slate-800"
                  aria-label="Send assistant message"
                >
                  <Send size={18} />
                </button>
              </div>
            </form>

            {!speechSupported ? (
              <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-700">
                Voice input is not supported in this browser. You can still use the assistant by typing.
              </p>
            ) : null}
          </div>
        </section>
      ) : null}

      {!isOpen ? (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="fixed bottom-24 right-5 z-50 inline-flex h-14 w-14 items-center justify-center rounded-full bg-[linear-gradient(135deg,#123b70_0%,#2a67b4_100%)] text-white shadow-[0_18px_36px_rgba(18,59,112,0.28)] transition hover:translate-y-[-1px] hover:shadow-[0_22px_42px_rgba(18,59,112,0.34)] sm:bottom-24 sm:right-6"
          aria-label="Show AI voice assistant"
        >
          <span className="rounded-full bg-white/14 p-2.5">
            <Bot size={20} />
          </span>
        </button>
      ) : null}
    </>
  );
}
