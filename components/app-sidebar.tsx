"use client"

import * as React from "react"
import {
  Archive,
  BarChart3,
  Building2,
  Calendar,
  ChevronUp,
  ClipboardList,
  FileText,
  FolderOpen,
  Home,
  Kanban,
  LayoutDashboard,
  LogOut,
  Search,
  Settings,
  User2,
  Users,
  UserCircle,
  Shield,
  Clock,
  CheckSquare,
  Upload,
  Share2,
  Eye,
  Settings2,
  Users2,
  FileCheck,
  ClipboardCheck,
  Plus,
  Edit,
  Trash2,
} from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ModeToggle } from "@/components/mode-toggle"
import Link from "next/link"

const data = {
  user: {
    name: "User",
    email: "user@example.com",
    avatar: "/avatars/shadcn.jpg",
  },
  mainNavigation: [
    {
      title: "Dashboard",
      url: "/dashboard",
      icon: LayoutDashboard,
    },
    {
      title: "Tasks",
      url: "/dashboard/tasks",
      icon: CheckSquare,
      items: [
        {
          title: "All Tasks",
          url: "/dashboard/tasks",
          icon: ClipboardList,
        },
        {
          title: "Create Task",
          url: "/dashboard/tasks/create",
          icon: Plus,
        },
        {
          title: "My Tasks",
          url: "/dashboard/tasks/my",
          icon: User2,
        },
      ],
    },
    {
      title: "Projects",
      url: "/dashboard/projects",
      icon: FolderOpen,
      items: [
        {
          title: "All Projects",
          url: "/dashboard/projects",
          icon: FolderOpen,
        },
        {
          title: "Kanban Board",
          url: "/dashboard/projects/kanban",
          icon: Kanban,
        },
        {
          title: "Create Project",
          url: "/dashboard/projects/create",
          icon: Plus,
        },
      ],
    },
    {
      title: "Clients",
      url: "/dashboard/clients",
      icon: Building2,
      items: [
        {
          title: "All Clients",
          url: "/dashboard/clients",
          icon: Building2,
        },
        {
          title: "Create Client",
          url: "/dashboard/clients/create",
          icon: Plus,
        },
        {
          title: "Contacts",
          url: "/dashboard/contacts",
          icon: Users,
        },
      ],
    },
  ],
  sections: [
    {
      title: "Documents",
      items: [
        {
          title: "Checklists",
          url: "/dashboard/documents/checklists",
          icon: ClipboardCheck,
        },
        {
          title: "Uploaded Files",
          url: "/dashboard/documents/uploaded",
          icon: Upload,
        },
        {
          title: "Share Documents",
          url: "/dashboard/documents/share",
          icon: Share2,
        },
      ],
    },
    {
      title: "Admin",
      items: [
        {
          title: "Admin Dashboard",
          url: "/dashboard/admin",
          icon: LayoutDashboard,
        },
        {
          title: "Users",
          url: "/dashboard/admin/users",
          icon: Users2,
        },
        {
          title: "Work Types",
          url: "/dashboard/admin/work-types",
          icon: Settings2,
        },
        {
          title: "Templates",
          url: "/dashboard/admin/templates",
          icon: FileCheck,
        },
        {
          title: "Calendar",
          url: "/dashboard/admin/calendar",
          icon: Calendar,
        },
        {
          title: "Search",
          url: "/dashboard/admin/search",
          icon: Search,
        },
        {
          title: "Reports",
          url: "/dashboard/admin/reports",
          icon: BarChart3,
        },
      ],
    },
    {
      title: "Client Portal",
      items: [
        {
          title: "Client Login",
          url: "/dashboard/client-portal/login",
          icon: Shield,
        },
        {
          title: "Client Dashboard",
          url: "/dashboard/client-portal/dashboard",
          icon: LayoutDashboard,
        },
        {
          title: "Access Setup",
          url: "/dashboard/client-portal/access-setup",
          icon: Settings,
        },
      ],
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/dashboard">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                  <Home className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">CPA WorkflowPilot</span>
                  <span className="truncate text-xs">Professional Edition</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Main Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {data.mainNavigation.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <Link href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                  {item.items?.length ? (
                    <SidebarMenuSub>
                      {item.items.map((subItem) => (
                        <SidebarMenuSubItem key={subItem.title}>
                          <SidebarMenuSubButton asChild>
                            <Link href={subItem.url}>
                              <subItem.icon />
                              <span>{subItem.title}</span>
                            </Link>
                          </SidebarMenuSubButton>
                        </SidebarMenuSubItem>
                      ))}
                    </SidebarMenuSub>
                  ) : null}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        {data.sections.map((section) => (
          <SidebarGroup key={section.title}>
            <SidebarGroupLabel>{section.title}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {section.items.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild>
                      <Link href={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                  <UserCircle className="size-8" />
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">{data.user.name}</span>
                    <span className="truncate text-xs">{data.user.email}</span>
                  </div>
                  <ChevronUp className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                side="bottom"
                align="end"
                sideOffset={4}
              >
                <DropdownMenuItem>
                  <UserCircle />
                  Account
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Settings />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <LogOut />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <div className="flex items-center justify-center p-2">
              <ModeToggle />
            </div>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}