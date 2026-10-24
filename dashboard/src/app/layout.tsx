import "@xyflow/react/dist/style.css";
import "./globals.css";

export const metadata = {
  title: "AgentWarden | Autonomous Agent Security",
  description: "Next-gen runtime guardrails and identity security for autonomous agent fleets."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" style={{ backgroundColor: "#040408", color: "#ffffff" }}>
      <body
        className="bg-[#040408] text-white antialiased min-h-screen selection:bg-purple-600 selection:text-white"
        style={{ backgroundColor: "#040408", color: "#ffffff", margin: 0, padding: 0 }}
      >
        {children}
      </body>
    </html>
  );
}
