"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import {
  ArrowLeft,
  Edit,
  Calendar,
  DollarSign,
  Users,
  CheckSquare,
  Clock,
  FileText,
  MoreHorizontal,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface ProjectData {
  id: number
  name: string
  description: string
  client: {
    id: number
    name: string
    email: string
  }
  status: string
  start_date: string
  due_date: string
  budget: number
  spent: number
  work_type: {
    id: number
    name: string
  }
  tasks: any[]
  progress: number
}

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [project, setProject] = useState<ProjectData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Mock project data
    const mockProject: ProjectData = {
      id: parseInt(params.id),
      name: "Q4 Financial Review",
      description: "Comprehensive financial analysis and reporting for Q4 2024. This includes reviewing all financial statements, conducting variance analysis, and preparing executive summary reports.",
      client: {
        id: 1,
        name: "ABC Corporation",
        email: "finance@abccorp.com",
      },
      status: "in_progress",
      start_date: "2024-01-15",
      due_date: "2024-02-15",
      budget: 15000,
      spent: 8500,
      work_type: {
        id: 2,
        name: "Financial Statement Audit",
      },
      progress: 65,
      tasks: [
        {
          id: 1,
          title: "Review General Ledger",
          status: "completed",
          assigned_to: "John Doe",
          due_date: "2024-01-20",
        },
        {
          id: 2,
          title: "Analyze Revenue Recognition",
          status: "in_progress",
          assigned_to: "Jane Smith",
          due_date: "2024-01-25",
        },
        {
          id: 3,
          title: "Prepare Executive Summary",
          status: "pending",
          assigned_to: "Mike Johnson",
          due_date: "2024-02-10",
        },
      ],
    }

    setProject(mockProject)
    setLoading(false)
  }, [params.id])

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800"
      case "in_progress":
        return "bg-blue-100 text-blue-800"
      case "planning":
        return "bg-yellow-100 text-yellow-800"
      case "on_hold":
        return "bg-orange-100 text-orange-800"
      case "review":
        return "bg-purple-100 text-purple-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getTaskStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800"
      case "in_progress":
        return "bg-blue-100 text-blue-800"
      case "pending":
        return "bg-gray-100 text-gray-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg">Loading project details...</div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg">Project not found</div>
      </div>
    )
  }

  const budgetUsed = (project.spent / project.budget) * 100

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button 
            variant="outline" 
            size="icon"
            onClick={() => router.back()}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{project.name}</h1>
            <p className="text-muted-foreground">Project #{project.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            onClick={() => router.push(`/dashboard/projects/${project.id}/edit`)}
          >
            <Edit className="h-4 w-4 mr-2" />
            Edit Project
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem>
                <FileText className="h-4 w-4 mr-2" />
                Export Report
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Users className="h-4 w-4 mr-2" />
                Manage Team
              </DropdownMenuItem>
              <DropdownMenuItem className="text-red-600">
                Archive Project
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Project Overview</CardTitle>
              <CardDescription>Key project information and status</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Status</span>
                <Badge className={getStatusColor(project.status)} variant="secondary">
                  {project.status.replace('_', ' ').toUpperCase()}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Work Type</span>
                <span className="text-sm text-muted-foreground">{project.work_type.name}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="font-medium">Client</span>
                <span className="text-sm text-muted-foreground">{project.client.name}</span>
              </div>

              <Separator />

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Progress</span>
                  <span className="text-sm text-muted-foreground">{project.progress}%</span>
                </div>
                <Progress value={project.progress} className="w-full" />
              </div>

              <Separator />

              <div className="space-y-2">
                <span className="font-medium">Description</span>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {project.description}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Project Tasks</CardTitle>
              <CardDescription>Tasks associated with this project</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {project.tasks.map((task) => (
                  <div key={task.id} className="flex items-center gap-4 p-4 border rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium">{task.title}</h4>
                        <Badge className={getTaskStatusColor(task.status)} variant="secondary">
                          {task.status.replace('_', ' ')}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Users className="h-3 w-3" />
                          {task.assigned_to}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          Due {new Date(task.due_date).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <Button size="sm" variant="outline">
                      View Task
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Project Timeline</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5 text-green-600" />
                <div>
                  <div className="font-medium">Start Date</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(project.start_date).toLocaleDateString()}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <Clock className="h-5 w-5 text-orange-600" />
                <div>
                  <div className="font-medium">Due Date</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(project.due_date).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Budget Overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Total Budget</span>
                <span className="text-lg font-bold">${project.budget.toLocaleString()}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Amount Spent</span>
                <span className="text-lg font-bold text-red-600">${project.spent.toLocaleString()}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Remaining</span>
                <span className="text-lg font-bold text-green-600">
                  ${(project.budget - project.spent).toLocaleString()}
                </span>
              </div>

              <Separator />

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Budget Used</span>
                  <span className="text-sm text-muted-foreground">{budgetUsed.toFixed(1)}%</span>
                </div>
                <Progress value={budgetUsed} className="w-full" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick Stats</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 border rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {project.tasks.length}
                  </div>
                  <div className="text-xs text-muted-foreground">Total Tasks</div>
                </div>
                <div className="text-center p-3 border rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {project.tasks.filter(t => t.status === 'completed').length}
                  </div>
                  <div className="text-xs text-muted-foreground">Completed</div>
                </div>
                <div className="text-center p-3 border rounded-lg">
                  <div className="text-2xl font-bold text-orange-600">
                    {project.tasks.filter(t => t.status === 'in_progress').length}
                  </div>
                  <div className="text-xs text-muted-foreground">In Progress</div>
                </div>
                <div className="text-center p-3 border rounded-lg">
                  <div className="text-2xl font-bold text-gray-600">
                    {project.tasks.filter(t => t.status === 'pending').length}
                  </div>
                  <div className="text-xs text-muted-foreground">Pending</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}