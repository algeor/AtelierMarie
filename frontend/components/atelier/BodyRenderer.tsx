export function bodyBlocks(body: string | null): Array<{ type: "p"; text: string } | { type: "ul"; items: string[] }> {
  if (!body) return [];
  const blocks: Array<{ type: "p"; text: string } | { type: "ul"; items: string[] }> = [];
  let bullets: string[] = [];

  for (const rawBlock of body.split(/\n\s*\n/)) {
    const lines = rawBlock.split("\n").map((line) => line.trim()).filter(Boolean);
    for (const line of lines) {
      const bullet = line.match(/^[-*]\s+(.+)/);
      if (bullet) {
        bullets.push(bullet[1] ?? "");
        continue;
      }
      if (bullets.length > 0) {
        blocks.push({ type: "ul", items: bullets });
        bullets = [];
      }
      blocks.push({ type: "p", text: line });
    }
  }
  if (bullets.length > 0) blocks.push({ type: "ul", items: bullets });
  return blocks;
}

export function BodyRenderer({ body, className = "" }: { body: string | null; className?: string }) {
  const blocks = bodyBlocks(body);
  if (blocks.length === 0) return null;
  return (
    <div className={`space-y-4 text-base leading-8 text-soft-brown ${className}`}>
      {blocks.map((block, index) =>
        block.type === "p" ? (
          <p key={`${index}-${block.text}`}>{block.text}</p>
        ) : (
          <ul key={`${index}-list`} className="list-disc space-y-2 pl-5">
            {block.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )
      )}
    </div>
  );
}
