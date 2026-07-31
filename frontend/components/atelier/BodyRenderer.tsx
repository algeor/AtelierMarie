type BodyBlock = { type: "p"; text: string } | { type: "quote"; text: string } | { type: "ul"; items: string[] };

export function bodyBlocks(body: string | null): BodyBlock[] {
  if (!body) return [];
  const blocks: BodyBlock[] = [];
  let bullets: string[] = [];

  for (const rawBlock of body.split(/\n\s*\n/)) {
    const lines = rawBlock.split("\n").map((line) => line.trim()).filter(Boolean);
    for (const line of lines) {
      const bullet = line.match(/^[-*]\s+(.+)/);
      if (bullet) {
        bullets.push(bullet[1] ?? "");
        continue;
      }
      const quote = line.match(/^>\s+(.+)/);
      if (bullets.length > 0) {
        blocks.push({ type: "ul", items: bullets });
        bullets = [];
      }
      if (quote) {
        blocks.push({ type: "quote", text: quote[1] ?? "" });
        continue;
      }
      const inlineQuote = line.match(/^(.*?:)\s+\*["“](.+?)["”]\*$/);
      if (inlineQuote) {
        blocks.push({ type: "p", text: inlineQuote[1] ?? "" });
        blocks.push({ type: "quote", text: inlineQuote[2] ?? "" });
        continue;
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
        ) : block.type === "quote" ? (
          <blockquote
            key={`${index}-${block.text}`}
            className="border-l-2 border-muted-gold pl-5 font-heading text-2xl leading-9 text-charcoal sm:text-3xl sm:leading-10"
          >
            &ldquo;{block.text}&rdquo;
          </blockquote>
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
