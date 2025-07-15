"use client"

import { SidebarProvider as ShadcnSidebarProvider } from "@/components/ui/sidebar"

export function SidebarProvider({
  children,
  ...props
}: React.ComponentProps<typeof ShadcnSidebarProvider>) {
  return (
    <ShadcnSidebarProvider {...props}>
      {children}
    </ShadcnSidebarProvider>
  )
}