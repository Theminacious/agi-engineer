import type { Metadata } from "next"
import "../globals.css"

export const metadata: Metadata = {
  title: "AGI Engineer - AI-Powered Code Analysis",
  description: "Automatically analyze, explain, and fix code issues with AI",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  )
}
