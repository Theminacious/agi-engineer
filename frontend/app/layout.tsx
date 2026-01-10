import type { Metadata } from "next"
import "../globals.css"

export const metadata: Metadata = {
  title: "AGI Engineer - AI-Powered Code Analysis",
  description: "Automatically analyze, explain, and fix code issues with AI - Like having a team of expert engineers",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-background text-foreground">{children}</body>
    </html>
  )
}
