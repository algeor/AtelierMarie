import { cn } from "@/lib/utils";

export type CategoryLineArtKind = "candles" | "christmas-balls" | "custom-boxes" | "notebooks";

interface CategoryLineArtProps {
  kind: CategoryLineArtKind;
  className?: string;
  animated?: boolean;
  title?: string;
}

const drawings: Record<CategoryLineArtKind, string[]> = {
  candles: [
    "M47 92 C47 74 48 52 55 45 C61 39 77 39 84 45 C91 52 92 74 92 92",
    "M46 92 C57 98 82 98 94 92",
    "M55 47 C62 55 78 55 85 47",
    "M70 43 C66 35 70 28 76 23 C78 31 86 37 78 45",
    "M60 56 C62 62 67 64 70 58 C74 66 80 63 82 56",
    "M39 94 C51 105 89 105 101 94",
  ],
  "christmas-balls": [
    "M39 66 C39 54 49 44 61 44 C73 44 83 54 83 66 C83 78 73 88 61 88 C49 88 39 78 39 66Z",
    "M56 39 H66 V45 H56Z",
    "M61 39 C60 31 66 27 71 31",
    "M76 73 C76 63 84 55 94 55 C104 55 112 63 112 73 C112 83 104 91 94 91 C84 91 76 83 76 73Z",
    "M89 50 H99 V56 H89Z",
    "M94 50 C93 43 99 40 103 43",
    "M55 71 C61 67 65 61 67 54",
    "M89 79 C96 74 101 67 103 60",
  ],
  "custom-boxes": [
    "M34 53 L78 35 L122 53 L78 72Z",
    "M34 53 V91 L78 111 V72",
    "M122 53 V91 L78 111",
    "M78 35 V111",
    "M58 44 C53 34 66 28 78 35 C90 28 103 34 98 44",
    "M78 35 C71 29 64 29 58 36",
    "M78 35 C85 29 92 29 98 36",
  ],
  notebooks: [
    "M40 31 H84 C95 31 104 40 104 51 V95 C104 99 101 102 97 102 H52 C45 102 40 97 40 90Z",
    "M50 31 V96 C54 92 60 90 67 90 H104",
    "M62 47 H90",
    "M62 59 H92",
    "M62 71 H86",
    "M104 40 C113 43 120 51 120 62 V101 C114 97 107 95 97 96",
    "M88 31 V58 L94 53 L100 58 V33",
  ],
};

export function CategoryLineArt({
  kind,
  className,
  animated = true,
  title,
}: CategoryLineArtProps) {
  const titleId = title ? `category-line-art-${kind}-title` : undefined;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 160 120"
      width={160}
      height={120}
      role={title ? "img" : undefined}
      aria-labelledby={titleId}
      aria-hidden={title ? undefined : true}
      focusable="false"
      className={cn("category-line-art", animated && "rebrand-line-draw", className)}
    >
      {title ? <title id={titleId}>{title}</title> : null}
      {drawings[kind].map((d, index) => (
        <path
          key={`${kind}-${index}`}
          className="category-line-art__stroke"
          d={d}
          pathLength={1}
          fill="none"
          stroke="currentColor"
          strokeWidth={3}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}
    </svg>
  );
}
