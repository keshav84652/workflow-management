"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Users,
  Settings,
  FileCheck,
  Calendar,
  Search,
  BarChart3,
  Shield,
  Database,
  Clock,
  Activity,
  TrendingUp,
  UserPlus,
  Settings2,
  Loader2,
} from "lucide-react"
import { useDashboardStats, useUsers, useWorkTypes } from "@/lib/hooks"
import Link from "next/link"

export default function AdminDashboard() {
  const { data: stats, loading: statsLoading } = useDashboardStats()
  const { data: users, loading: usersLoading } = useUsers()
  const { data: workTypes, loading: workTypesLoading } = useWorkTypes()

  const adminCards = [
    {
      title: "User Management",
      description: "Manage user accounts and permissions",
      icon: Users,
      href: "/dashboard/admin/users",
      color: "bg-blue-100 text-blue-600 border-blue-200",
      count: users?.length || 0,
      loading: usersLoading,
    },
    {
      title: "Work Types",
      description: "Configure work types and categories",
      icon: Settings2,
      href: "/dashboard/admin/work-types",
      color: "bg-purple-100 text-purple-600 border-purple-200",
      count: workTypes?.length || 0,
      loading: workTypesLoading,
    },
    {
      title: "Templates",
      description: "Manage project and task templates",
      icon: FileCheck,
      href: "/dashboard/admin/templates",
      color: "bg-green-100 text-green-600 border-green-200",
      count: 0,
      loading: false,
    },
    {
      title: "Calendar Management",
      description: "Configure calendar settings and holidays",
      icon: Calendar,
      href: "/dashboard/admin/calendar",
      color: "bg-orange-100 text-orange-600 border-orange-200",
      count: 0,
      loading: false,
    },
    {
      title: "Global Search",
      description: "Search across all data and content",
      icon: Search,
      href: "/dashboard/admin/search",
      color: "bg-indigo-100 text-indigo-600 border-indigo-200",
      count: 0,
      loading: false,
    },
    {
      title: "Reports & Analytics",
      description: "Generate reports and view analytics",
      icon: BarChart3,
      href: "/dashboard/admin/reports",
      color: "bg-red-100 text-red-600 border-red-200",
      count: 0,
      loading: false,
    },
  ]

  const systemStats = [
    {
      title: "Total Users",
      value: users?.length || 0,
      icon: Users,
      color: "text-blue-600",
      loading: usersLoading,
    },
    {
      title: "Active Sessions",
      value: users?.filter(u => u.role === "Admin").length || 0,
      icon: Activity,
      color: "text-green-600",
      loading: usersLoading,
    },
    {
      title: "System Uptime",
      value: "99.9%",
      icon: TrendingUp,
      color: "text-purple-600",
      loading: false,
    },
    {
      title: "Data Integrity",
      value: "100%",
      icon: Shield,
      color: "text-orange-600",
      loading: false,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="text-gray-600 mt-1">System administration and configuration</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Database className="h-4 w-4 mr-2" />
            Backup Data
          </Button>
          <Button>
            <UserPlus className="h-4 w-4 mr-2" />
            Add User
          </Button>
        </div>
      </div>

      {/* System Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {systemStats.map((stat, index) => (
          <Card key={index}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                  {stat.loading ? (
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400 mt-2" />
                  ) : (
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
                  )}
                </div>
                <stat.icon className={`h-8 w-8 ${stat.color}`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Stats from Dashboard */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>System Overview</CardTitle>
            <CardDescription>Current system statistics and activity</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">{stats.total_projects}</p>
                <p className="text-sm text-gray-600">Total Projects</p>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">{stats.total_tasks}</p>
                <p className="text-sm text-gray-600">Total Tasks</p>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <p className="text-2xl font-bold text-purple-600">{stats.total_clients}</p>
                <p className="text-sm text-gray-600">Total Clients</p>
              </div>
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <p className="text-2xl font-bold text-orange-600">{stats.completed_tasks}</p>
                <p className="text-sm text-gray-600">Completed Tasks</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Admin Functions */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Administration Tools</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {adminCards.map((card) => (
            <Link key={card.href} href={card.href}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className={`p-3 rounded-lg ${card.color}`}>
                      <card.icon className="h-6 w-6" />
                    </div>
                    {card.loading ? (
                      <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                    ) : (
                      <Badge variant="secondary">{card.count}</Badge>
                    )}
                  </div>
                  <CardTitle className="text-lg">{card.title}</CardTitle>
                  <CardDescription>{card.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button variant="outline" className="w-full">
                    Manage
                  </Button>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      {stats?.recent_activities && (
        <Card>
          <CardHeader>
            <CardTitle>Recent System Activity</CardTitle>
            <CardDescription>Latest administrative actions and system events</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats.recent_activities.slice(0, 5).map((activity) => (
                <div key={activity.id} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                  <div className="p-2 bg-white rounded-full">
                    <Clock className="h-4 w-4 text-gray-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{activity.message}</p>
                    <p className="text-xs text-gray-600">by {activity.user}</p>
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(activity.timestamp).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}