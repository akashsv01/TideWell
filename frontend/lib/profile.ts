import type { DeliveryType, FeedingType, Language, Profile } from "@/lib/types";

// Answer options shared by onboarding and the Settings profile editor, so both stay identical.
// TODO (Person 4): confirm the complication list and the consent wording.

export const DELIVERY: { value: DeliveryType; label: string }[] = [
  { value: "vaginal", label: "Vaginal birth" },
  { value: "c-section", label: "C-section" },
];

export const FEEDING: { value: FeedingType; label: string; hint: string }[] = [
  { value: "breastfeeding", label: "Breastfeeding or chestfeeding", hint: "Only breast milk" },
  { value: "formula", label: "Formula", hint: "Only formula" },
  { value: "mixed", label: "A mix of both", hint: "Some of each" },
];

export const COMPLICATIONS: { value: string; label: string }[] = [
  { value: "gestational hypertension", label: "High blood pressure or preeclampsia" },
  { value: "gestational diabetes", label: "Gestational diabetes" },
  { value: "heavy bleeding at birth", label: "Heavy bleeding at birth" },
  { value: "preterm birth", label: "Baby born early (before 37 weeks)" },
  { value: "heart condition", label: "A heart condition" },
];

export const LANGUAGES: { value: Language; label: string }[] = [
  { value: "en", label: "English" },
  { value: "es", label: "Español" },
];

export const CONSENT_TEXT =
  "Tidewell may store my check-ins (what I say, the numbers it notes, and my answers) to track my recovery and remind me when something is worth a call. I can delete everything at any time in Settings.";

export const todayIso = () => new Date().toISOString().slice(0, 10);

export const yearAgoIso = () => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().slice(0, 10);
};

export const digits = (s: string) => s.replace(/\D/g, "");

/** "(202) 555-0123" or "+1 202 555 0123" -> "+12025550123"; null when empty. */
export function toE164(phone: string): string | null {
  const d = digits(phone);
  if (!d) return null;
  return d.length === 10 ? `+1${d}` : `+${d}`;
}

/** Display form of a stored E.164 number for a US/Canada line. */
export function fromE164(phone: string | null): string {
  if (!phone) return "";
  const d = digits(phone);
  return d.length === 11 && d.startsWith("1") ? d.slice(1) : d;
}

/** Problems with a profile, in plain words, or null when it can be saved. */
export function profileProblem(p: Partial<Profile>, phoneText: string): string | null {
  if (!p.consent_granted) return "Tidewell needs your permission to store your check-ins.";
  if (!p.delivery_date) return "Choose the date your baby was born.";
  if (p.delivery_date > todayIso()) return "That date is in the future. Choose the day your baby was born.";
  if (p.delivery_date < yearAgoIso()) return "Tidewell is for the first year after birth. Choose a date in the last 12 months.";
  if (p.gestation_weeks != null && (p.gestation_weeks < 20 || p.gestation_weeks > 45))
    return "Weeks of pregnancy should be between 20 and 45.";
  if (!p.delivery_method) return "Choose how you gave birth.";
  if (!p.feeding_type) return "Choose how you are feeding your baby.";
  if (phoneText.trim() && digits(phoneText).length < 10) return "Enter the full phone number, including area code.";
  if (phoneText.trim() && !p.support_person_name?.trim()) return "Add your support person's first name.";
  return null;
}
