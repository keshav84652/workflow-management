'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { 
  CheckCircle, 
  Clock, 
  Users, 
  FolderOpen, 
  TrendingUp,
  Plus,
  Loader2,
  Activity
} from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { useDashboardStats, useRecentActivity } from '@/lib/hooks'
import { withAuth } from '@/lib/auth'
import Link from 'next/link'

function DashboardPage() {
  const { user } = useAuth()
  const { data: stats, loading: statsLoading, error: statsError } = useDashboardStats()
  const { data: recentActivity, loading: activityLoading, error: activityError } = useRecentActivity(5)

  if (statsLoading || activityLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (statsError || activityError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-red-600 mb-2">Error loading dashboard data</p>
          <p className="text-gray-500">{statsError || activityError}</p>
        </div>
      </div>
    )
  }

  const statsCards = [
    {
      title: "Active Projects",
      value: stats?.active_projects?.toString() || "0",
      change: `${stats?.total_projects || 0} total`,
      icon: FolderOpen,
      color: "text-blue-600",
      href: "/dashboard/projects"
    },
    {
      title: "Pending Tasks",
      value: stats?.pending_tasks?.toString() || "0",
      change: `${stats?.overdue_tasks || 0} overdue`,
      icon: Clock,
      color: "text-amber-600",
      href: "/dashboard/tasks"
    },
    {
      title: "Completed Tasks",
      value: stats?.completed_tasks?.toString() || "0",
      change: `${stats?.total_tasks || 0} total`,
      icon: CheckCircle,
      color: "text-green-600",
      href: "/dashboard/tasks"
    },
    {
      title: "Total Clients",
      value: stats?.total_clients?.toString() || "0",
      change: "Active clients",
      icon: Users,
      color: "text-purple-600",
      href: "/dashboard/clients"
    }
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back, {user?.name}. Here's your workflow overview.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/tasks/create">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Task
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statsCards.map((stat, index) => (
          <Link key={index} href={stat.href}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <TrendingUp className="h-3 w-3" />
                  {stat.change}
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Activity
            </CardTitle>
            <CardDescription>
              Latest updates and changes
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivity && recentActivity.length > 0 ? (
                recentActivity.map((activity, index) => (
                  <div key={index} className="flex items-start gap-3 pb-3 border-b last:border-0">
                    <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0" />
                    <div className="flex-1 space-y-1">
                      <p className="text-sm font-medium leading-none">{activity.message}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{activity.user}</span>
                        <span>•</span>
                        <span>{new Date(activity.timestamp).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No recent activity</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common tasks and shortcuts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Link href="/dashboard/tasks/create">
                <Button variant="outline" className="w-full justify-start h-12">
                  <Plus className="h-4 w-4 mr-3" />
                  <div className="text-left">
                    <div className="font-medium">Create Task</div>
                    <div className="text-xs text-muted-foreground">Add a new task to your workflow</div>
                  </div>
                </Button>
              </Link>
              <Link href="/dashboard/projects/kanban">
                <Button variant="outline" className="w-full justify-start h-12">
                  <FolderOpen className="h-4 w-4 mr-3" />
                  <div className="text-left">
                    <div className="font-medium">Kanban Board</div>
                    <div className="text-xs text-muted-foreground">Manage projects visually</div>
                  </div>
                </Button>
              </Link>
              <Link href="/dashboard/clients">
                <Button variant="outline" className="w-full justify-start h-12">
                  <Users className="h-4 w-4 mr-3" />
                  <div className="text-left">
                    <div className="font-medium">Client Management</div>
                    <div className="text-xs text-muted-foreground">View and manage clients</div>
                  </div>
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Task Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Task Overview</CardTitle>
          <CardDescription>Current task status and distribution</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-amber-600">{stats?.pending_tasks || 0}</div>
              <div className="text-sm text-muted-foreground">Pending Tasks</div>
              <div className="text-xs text-muted-foreground mt-1">Need attention</div>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-red-600">{stats?.overdue_tasks || 0}</div>
              <div className="text-sm text-muted-foreground">Overdue Tasks</div>
              <div className="text-xs text-muted-foreground mt-1">Past due date</div>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-green-600">{stats?.completed_tasks || 0}</div>
              <div className="text-sm text-muted-foreground">Completed Tasks</div>
              <div className="text-xs text-muted-foreground mt-1">This period</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default withAuth(DashboardPage)