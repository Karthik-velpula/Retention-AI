import RiskBadge from "./RiskBadge";
import { PredictionResult } from "../types";

export default function PredictionPanel({ prediction }: { prediction: PredictionResult | null }) {
  if (!prediction) {
    return (
      <section className="rounded-[2rem] bg-white p-6 shadow-soft">
        <h2 className="font-display text-2xl text-ink">AI Risk Intelligence</h2>
        <p className="mt-3 text-slate-500">Select a student and run a prediction to see risk level, SHAP-based explanations, and targeted actions.</p>
      </section>
    );
  }

  return (
    <section className="rounded-[2rem] bg-white p-6 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl text-ink">AI Risk Intelligence</h2>
          <p className={`mt-2 text-sm font-semibold uppercase tracking-[0.22em] ${riskTone(prediction.risk_level)}`}>
            {riskHeadline(prediction.risk_level)}
          </p>
          <p className="mt-2 text-slate-600">{prediction.explanation}</p>
        </div>
        <RiskBadge level={prediction.risk_level} />
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-3xl bg-mist p-4">
          <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Primary Model Probability</p>
          <p className="mt-2 text-3xl font-semibold text-ink">{(prediction.probability * 100).toFixed(1)}%</p>
          <p className="mt-2 text-sm text-slate-500">{riskGuidance(prediction.risk_level)}</p>
        </div>
        <div className="rounded-3xl bg-mist p-4">
          <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Comparison Model</p>
          <p className="mt-2 text-3xl font-semibold text-ink">{(prediction.comparison_model_probability * 100).toFixed(1)}%</p>
          <p className="mt-2 text-sm text-slate-500">Used to compare confidence against the primary Random Forest model.</p>
        </div>
      </div>
      <div className="mt-6">
        <h3 className="text-lg font-semibold text-ink">Why AI Predicted This</h3>
        <ul className="mt-4 space-y-2 text-slate-600">
          {prediction.feature_importance.map((item) => (
            <li key={item.feature} className="rounded-2xl bg-mist px-4 py-3">
              <div className="font-medium text-ink">
                {featureInfluenceLabel(item.feature, prediction.risk_level, item.actual_value)}
              </div>
              <div className="mt-1 text-sm text-slate-500">
                Current value: {formatFeatureValue(item.actual_value)}
                {" · "}
                Impact: {formatImpactLevel(item.importance)}
              </div>
            </li>
          ))}
        </ul>
      </div>
      <div className="mt-6">
        <h3 className="text-lg font-semibold text-ink">AI Recommendations</h3>
        <ul className="mt-3 space-y-2 text-slate-600">
          {prediction.recommendations.map((item) => (
            <li key={item} className="rounded-2xl bg-mist px-4 py-3">
              {item}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function riskHeadline(level: PredictionResult["risk_level"]) {
  if (level === "High") return "Urgent Intervention Required";
  if (level === "Medium") return "Early Warning: Monitor Closely";
  if (level === "Low") return "Low Risk: Keep Watching Progress";
  return "Safe Retention Outlook";
}

function riskGuidance(level: PredictionResult["risk_level"]) {
  if (level === "High") return "Immediate faculty outreach and corrective action are recommended.";
  if (level === "Medium") return "This student shows moderate risk signals and should be monitored proactively.";
  if (level === "Low") return "Current signals are mostly stable, but periodic monitoring is still recommended.";
  return "Current signals are very healthy; continue reinforcement and periodic review.";
}

function riskTone(level: PredictionResult["risk_level"]) {
  if (level === "High") return "text-red-600";
  if (level === "Medium") return "text-amber-600";
  if (level === "Low") return "text-lime-600";
  return "text-emerald-600";
}

function featureInfluenceLabel(
  feature: string,
  riskLevel: PredictionResult["risk_level"],
  actualValue?: string | number | null
) {
  const cleaned = feature.replace("num__", "").replace("cat__", "").replace(/_/g, " ").toLowerCase();
  const numericValue =
    typeof actualValue === "number"
      ? actualValue
      : typeof actualValue === "string"
        ? Number.parseFloat(actualValue.replace("%", ""))
        : Number.NaN;
  const normalizedValue = typeof actualValue === "string" ? actualValue.toLowerCase() : "";

  if (cleaned.includes("attendance")) {
    if (!Number.isNaN(numericValue) && numericValue >= 85) return "Attendance supported a lower-risk prediction.";
    if (riskLevel === "Safe" || riskLevel === "Low") return "Attendance strongly supported a lower-risk prediction.";
    if (riskLevel === "Medium") return "Attendance below 85% is one of the reasons this student is currently in medium risk.";
    return "Low attendance is a major reason this student is in high risk.";
  }
  if (cleaned.includes("gpa")) {
    if (!Number.isNaN(numericValue) && numericValue >= 8) return "CGPA supported a lower-risk prediction.";
    if (riskLevel === "Safe" || riskLevel === "Low") return "CGPA strongly supported a lower-risk prediction.";
    if (riskLevel === "Medium") return "CGPA is one of the reasons this student is currently in medium risk.";
    return "CGPA is a major reason this student is in high risk.";
  }
  if (cleaned.includes("assignment") || cleaned.includes("lms") || cleaned.includes("login")) {
    if (normalizedValue === "active" || (!Number.isNaN(numericValue) && numericValue >= 80)) {
      return "LMS engagement supported a lower-risk prediction.";
    }
    if (riskLevel === "Safe" || riskLevel === "Low") return "LMS engagement supported a lower-risk prediction.";
    if (riskLevel === "Medium") return "Weak LMS activity is one of the reasons this student is currently in medium risk.";
    return "Weak LMS activity is a major reason this student is in high risk.";
  }
  if (cleaned.includes("fee") || cleaned.includes("payment")) {
    if (normalizedValue === "paid" || (!Number.isNaN(numericValue) && numericValue <= 0)) {
      return "Fee status supported a lower-risk prediction.";
    }
    if (riskLevel === "Safe" || riskLevel === "Low") return "Fee status supported a lower-risk prediction.";
    if (riskLevel === "Medium") return "Fee status is one of the reasons this student is currently in medium risk.";
    return "Fee status is a major reason this student is in high risk.";
  }

  if (riskLevel === "Medium") {
    return `${cleaned.charAt(0).toUpperCase()}${cleaned.slice(1)} is one of the reasons this student is currently in medium risk.`;
  }
  if (riskLevel === "High") {
    return `${cleaned.charAt(0).toUpperCase()}${cleaned.slice(1)} is a major reason this student is in high risk.`;
  }
  return `${cleaned.charAt(0).toUpperCase()}${cleaned.slice(1)} influenced the prediction.`;
}

function formatFeatureValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function formatImpactLevel(importance: number) {
  if (importance >= 0.1) return "Strong";
  if (importance >= 0.03) return "Moderate";
  return "Light";
}
