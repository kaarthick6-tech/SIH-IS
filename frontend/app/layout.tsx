import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IS Recommendation Engine",
  description:
    "Match Indian Standards (IS) to procurement requirements using semantic search and LLM reranking.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900">
        {children}
      </body>
    </html>
  );
}
