import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "AGI Engineer - Code Quality Dashboard",
  description: "GitHub App for automated code quality analysis and fixes",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
