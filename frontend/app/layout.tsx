import type { Metadata } from "next"
import "../globals.css"
import { Header } from "@/components/layout"
import ContentWrapper from "./content-wrapper"

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
      <body className="bg-background text-foreground">
        <Header />
        <ContentWrapper>
          {children}
        </ContentWrapper>
      </body>
    </html>
  )
}
