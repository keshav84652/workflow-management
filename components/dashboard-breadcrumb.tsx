"use client"

import { usePathname } from "next/navigation"
import Link from "next/link"
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

interface BreadcrumbSegment {
  title: string
  href?: string
  isLast?: boolean
}

export function DashboardBreadcrumb() {
  const pathname = usePathname()
  
  // Generate breadcrumb segments from pathname
  const generateBreadcrumbs = (): BreadcrumbSegment[] => {
    const segments = pathname.split('/').filter(Boolean)
    const breadcrumbs: BreadcrumbSegment[] = []
    
    // Always start with Dashboard
    breadcrumbs.push({
      title: "Dashboard",
      href: "/dashboard",
    })
    
    if (segments.length <= 1) {
      breadcrumbs[0].isLast = true
      return breadcrumbs
    }
    
    let currentPath = ""
    
    for (let i = 1; i < segments.length; i++) {
      const segment = segments[i]
      currentPath += `/${segment}`
      
      // Skip dynamic route parameters (e.g., [id])
      if (segment.match(/^\[.*\]$/)) {
        continue
      }
      
      // Handle special cases and format titles
      let title = segment
      let href = `/dashboard${currentPath}`
      
      switch (segment) {
        case "tasks":
          title = "Tasks"
          break
        case "projects":
          title = "Projects"
          break
        case "clients":
          title = "Clients"
          break
        case "documents":
          title = "Documents"
          break
        case "contacts":
          title = "Contacts"
          break
        case "client-portal":
          title = "Client Portal"
          break
        case "admin":
          title = "Admin"
          break
        case "kanban":
          title = "Kanban Board"
          break
        case "create":
          title = "Create"
          // Don't make create pages clickable
          break
        case "edit":
          title = "Edit"
          // Don't make edit pages clickable
          break
        case "checklists":
          title = "Checklists"
          break
        case "uploaded":
          title = "Uploaded Files"
          break
        case "share":
          title = "Share Documents"
          break
        case "login":
          title = "Login Management"
          break
        case "dashboard":
          if (segments[i - 1] === "client-portal") {
            title = "Portal Dashboard"
          }
          break
        case "users":
          title = "Users"
          break
        case "work-types":
          title = "Work Types"
          break
        case "templates":
          title = "Templates"
          break
        default:
          // Handle dynamic IDs or other segments
          if (segment.match(/^\d+$/)) {
            // This is likely an ID, get context from previous segment
            const prevSegment = segments[i - 1]
            switch (prevSegment) {
              case "tasks":
                title = `Task #${segment}`
                break
              case "projects":
                title = `Project #${segment}`
                break
              case "clients":
                title = `Client #${segment}`
                break
              default:
                title = `#${segment}`
            }
          } else {
            // Capitalize and format other segments
            title = segment
              .split('-')
              .map(word => word.charAt(0).toUpperCase() + word.slice(1))
              .join(' ')
          }
      }
      
      // Check if this is the last segment or if the href should be undefined
      const isLast = i === segments.length - 1 || 
                    (i === segments.length - 2 && segments[i + 1] === 'edit') ||
                    (i === segments.length - 2 && segments[i + 1] === 'create')
      
      const shouldHaveHref = !isLast && segment !== "create" && segment !== "edit"
      
      breadcrumbs.push({
        title,
        href: shouldHaveHref ? href : undefined,
        isLast,
      })
    }
    
    return breadcrumbs
  }
  
  const breadcrumbs = generateBreadcrumbs()
  
  return (
    <Breadcrumb>
      <BreadcrumbList>
        {breadcrumbs.map((breadcrumb, index) => (
          <BreadcrumbItem key={index}>
            {breadcrumb.isLast || !breadcrumb.href ? (
              <BreadcrumbPage>{breadcrumb.title}</BreadcrumbPage>
            ) : (
              <BreadcrumbLink asChild>
                <Link href={breadcrumb.href}>{breadcrumb.title}</Link>
              </BreadcrumbLink>
            )}
            {index < breadcrumbs.length - 1 && <BreadcrumbSeparator />}
          </BreadcrumbItem>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  )
}