import "@xyflow/react/dist/style.css";
import "./globals.css";

export const metadata = {
  title: "DRISHTI | Runtime Identity Drift Detection",
  description: "Trust the identity. Verify the behavior. Control the action."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
