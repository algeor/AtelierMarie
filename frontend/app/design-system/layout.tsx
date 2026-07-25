import "../globals.css";

// The design-system gallery lives outside the [locale] segment, so it can't rely
// on [locale]/layout.tsx for the <html>/<body> shell. This standalone layout
// supplies them (the root app/layout.tsx is a bare passthrough).
export default function DesignSystemLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans">{children}</body>
    </html>
  );
}
