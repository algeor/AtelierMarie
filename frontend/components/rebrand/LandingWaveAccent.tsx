import { cn } from "@/lib/utils";

interface LandingWaveAccentProps {
  className?: string;
  span?: "medium" | "long";
  flip?: boolean;
}

const wavePaths = [
  {
    className: "landing-wave-accent__path--dark",
    d: "M36 136C232 50 420 48 628 118C826 184 1026 148 1272 48",
    strokeWidth: 8,
  },
  {
    className: "landing-wave-accent__path--soft",
    d: "M72 164C256 88 412 106 590 152C798 204 986 128 1214 88",
    strokeWidth: 5.25,
  },
  {
    className: "landing-wave-accent__path--light",
    d: "M138 94C308 132 448 82 608 72C794 58 936 138 1156 116",
    strokeWidth: 4,
  },
  {
    className: "landing-wave-accent__path--thread",
    d: "M196 178C352 142 478 158 644 98C816 36 974 84 1116 148",
    strokeWidth: 3.25,
  },
];

export function LandingWaveAccent({
  className,
  span = "long",
  flip = false,
}: LandingWaveAccentProps) {
  return (
    <div
      className={cn(
        "landing-wave-accent",
        `landing-wave-accent--${span}`,
        flip && "landing-wave-accent--flip",
        className
      )}
      aria-hidden="true"
    >
      <svg viewBox="0 0 1320 220" fill="none" preserveAspectRatio="none">
        {wavePaths.map((path) => (
          <path
            key={path.className}
            className={cn("landing-wave-accent__path", path.className)}
            pathLength={1}
            d={path.d}
            stroke="currentColor"
            strokeWidth={path.strokeWidth}
            strokeLinecap="round"
          />
        ))}
      </svg>
    </div>
  );
}
