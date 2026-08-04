import { cn } from "@/lib/utils";

type BrandMarkVariant = "signature" | "small";

interface BrandMarkProps {
  className?: string;
  variant?: BrandMarkVariant;
  animated?: boolean;
  title?: string;
}

const signaturePath =
  "M10 54 C17 30 22 18 29 18 C38 18 38 53 44 53 C50 53 55 18 65 18 C76 18 78 42 87 53";
const signatureFlourish = "M8 58 C27 64 65 63 90 55";
const smallPath = "M15 52 C22 26 30 19 36 46 C39 58 44 58 48 46 C58 16 69 25 81 52";

export function BrandMark({
  className,
  variant = "signature",
  animated = false,
  title,
}: BrandMarkProps) {
  const titleId = title ? "atelier-marie-brand-mark-title" : undefined;
  const isSmall = variant === "small";

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 96 72"
      width={isSmall ? 48 : 96}
      height={isSmall ? 36 : 72}
      role={title ? "img" : undefined}
      aria-labelledby={titleId}
      aria-hidden={title ? undefined : true}
      focusable="false"
      className={cn(
        "signature-mark",
        animated && "signature-mark--draw",
        isSmall && "signature-mark--small",
        className
      )}
    >
      {title ? <title id={titleId}>{title}</title> : null}
      <path
        className="signature-mark__stroke"
        d={isSmall ? smallPath : signaturePath}
        pathLength={1}
        fill="none"
        stroke="currentColor"
        strokeWidth={isSmall ? 5.25 : 4.75}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {!isSmall ? (
        <path
          className="signature-mark__flourish"
          d={signatureFlourish}
          pathLength={1}
          fill="none"
          stroke="currentColor"
          strokeWidth={2.75}
          strokeLinecap="round"
        />
      ) : null}
    </svg>
  );
}
