"use client"

import {
  CheckCircle,
  Info,
  Loader2,
  AlertOctagon,
  AlertTriangle,
} from "lucide-react"
import { useTheme } from "next-themes"
import { Toaster as Sonner } from "sonner"

const Toaster = (props) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme}
      className="toaster group"
      icons={{
        success: <CheckCircle className="size-4" />,
        info: <Info className="size-4" />,
        warning: <AlertTriangle className="size-4" />,
        error: <AlertOctagon className="size-4" />,
        loading: <Loader2 className="size-4 animate-spin" />,
      }}
      style={{
        "--normal-bg": "var(--popover)",
        "--normal-text": "var(--popover-foreground)",
        "--normal-border": "var(--border)",
        "--border-radius": "var(--radius)",
      }}
      {...props}
    />
  )
}

export { Toaster }
