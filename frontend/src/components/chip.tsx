import { TONE_CLASSES, type Tone } from "../format";

interface ChipProps {
  label: string;
  tone: Tone;
}

export function Chip({ label, tone }: ChipProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  );
}
