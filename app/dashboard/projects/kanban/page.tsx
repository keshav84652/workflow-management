"use client"

import { useState, useEffect } from "react"
import { DragDropContext, Droppable, Draggable, DropResult } from "@hello-pangea/dnd"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Calendar,
  Users,
  CheckCircle,
  Circle,
  Clock,
  AlertCircle,
  Loader2,
  Building2,
  User,
} from "lucide-react"
import Link from "next/link"
import { Project, Task, CLIENTS_DATA, USERS_DATA, WORK_TYPES_DATA } from "@/lib/data"

interface KanbanColumn {
  id: string
  title: string
  status: string
  color: string
  icon: React.ReactNode
}

const columns: KanbanColumn[] = [
  {
    id: "planning",
    title: "Planning",
    status: "Planning",
    color: "bg-yellow-100 border-yellow-200",
    icon: <Circle className="h-4 w-4 text-yellow-600" />,
  },
  {
    id: "active",
    title: "Active",
    status: "Active",
    color: "bg-blue-100 border-blue-200",
    icon: <Clock className="h-4 w-4 text-blue-600" />,
  },
  {
    id: "review",
    title: "Review", 
    status: "Review",
    color: "bg-purple-100 border-purple-200",
    icon: <AlertCircle className="h-4 w-4 text-purple-600" />,
  },
  {
    id: "completed",
    title: "Completed",
    status: "Completed",
    color: "bg-green-100 border-green-200",
    icon: <CheckCircle className="h-4 w-4 text-green-600" />,
  },
]

export default function KanbanPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState("")

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      
      // Fetch both projects and tasks
      const [projectsResponse, tasksResponse] = await Promise.all([
        fetch('/api/projects'),
        fetch('/api/tasks')
      ])
      
      const projectsResult = await projectsResponse.json()
      const tasksResult = await tasksResponse.json()
      
      if (projectsResult.success && tasksResult.success) {
        setProjects(projectsResult.data)
        setTasks(tasksResult.data)
      } else {
        setError('Failed to fetch data')
      }
    } catch (err) {
      setError('Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  const getClientName = (clientId: number) => {
    const client = CLIENTS_DATA.find(c => c.id === clientId)
    return client?.name || 'Unknown Client'
  }

  const getWorkTypeName = (workTypeId?: number) => {
    if (!workTypeId) return 'No Work Type'
    const workType = WORK_TYPES_DATA.find(w => w.id === workTypeId)
    return workType?.name || 'Unknown Work Type'
  }

  const getWorkTypeColor = (workTypeId?: number) => {
    if (!workTypeId) return '#gray'
    const workType = WORK_TYPES_DATA.find(w => w.id === workTypeId)
    return workType?.color || '#gray'
  }

  const getAssigneeName = (assigneeId?: number) => {
    if (!assigneeId) return 'Unassigned'
    const user = USERS_DATA.find(u => u.id === assigneeId)
    return user?.name || 'Unknown User'
  }

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return 'bg-red-100 text-red-800'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800'
      case 'low':
        return 'bg-green-100 text-green-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getProjectTasks = (projectId: number) => {
    return tasks.filter(task => task.project_id === projectId)
  }

  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    getClientName(project.client_id).toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getProjectsByStatus = (status: string) => {
    return filteredProjects.filter(project => 
      project.status.toLowerCase() === status.toLowerCase()
    )
  }

  const onDragEnd = (result: DropResult) => {
    const { destination, source, draggableId } = result

    if (!destination) return

    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return
    }

    // Find the new status based on the destination column
    const newStatus = columns.find(col => col.id === destination.droppableId)?.status

    if (newStatus) {
      // Update project status
      setProjects(prev => 
        prev.map(project => 
          project.id.toString() === draggableId 
            ? { ...project, status: newStatus }
            : project
        )
      )

      // In a real app, you would make an API call here to update the project
      console.log(`Project ${draggableId} moved to ${newStatus}`)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Error Loading Kanban Board</h3>
          <p className="text-muted-foreground mb-4">{error}</p>
          <Button onClick={fetchData}>Try Again</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Project Kanban</h1>
          <p className="text-muted-foreground">Drag and drop projects to update their status</p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/dashboard/projects">
            <Button variant="outline">
              List View
            </Button>
          </Link>
          <Link href="/dashboard/projects/create">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          </Link>
        </div>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search projects by name or client..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Kanban Board */}
      <DragDropContext onDragEnd={onDragEnd}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {columns.map((column) => {
            const columnProjects = getProjectsByStatus(column.status)
            
            return (
              <div key={column.id} className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {column.icon}
                    <h3 className="font-semibold">{column.title}</h3>
                    <Badge variant="secondary" className="text-xs">
                      {columnProjects.length}
                    </Badge>
                  </div>
                </div>

                <Droppable droppableId={column.id}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      className={`min-h-[500px] p-2 rounded-lg border-2 border-dashed transition-colors ${
                        snapshot.isDraggingOver 
                          ? 'border-blue-300 bg-blue-50' 
                          : 'border-gray-200'
                      }`}
                    >
                      <div className="space-y-3">
                        {columnProjects.map((project, index) => {
                          const projectTasks = getProjectTasks(project.id)
                          const completedTasks = projectTasks.filter(t => t.status === 'Completed').length
                          const totalTasks = projectTasks.length
                          
                          return (
                            <Draggable
                              key={project.id.toString()}
                              draggableId={project.id.toString()}
                              index={index}
                            >
                              {(provided, snapshot) => (
                                <Card
                                  ref={provided.innerRef}
                                  {...provided.draggableProps}
                                  {...provided.dragHandleProps}
                                  className={`cursor-move transition-shadow ${
                                    snapshot.isDragging ? 'shadow-lg rotate-2' : 'hover:shadow-md'
                                  }`}
                                >
                                  <CardHeader className="pb-3">
                                    <div className="flex items-start justify-between">
                                      <div className="space-y-1 flex-1">
                                        <CardTitle className="text-sm font-medium">
                                          {project.name}
                                        </CardTitle>
                                        <CardDescription className="text-xs flex items-center gap-1">
                                          <Building2 className="h-3 w-3" />
                                          {getClientName(project.client_id)}
                                        </CardDescription>
                                      </div>
                                      <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                          <Button 
                                            variant="ghost" 
                                            className="h-6 w-6 p-0"
                                            onClick={(e) => e.stopPropagation()}
                                          >
                                            <MoreHorizontal className="h-3 w-3" />
                                          </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                          <DropdownMenuItem asChild>
                                            <Link href={`/dashboard/projects/${project.id}`}>
                                              View Details
                                            </Link>
                                          </DropdownMenuItem>
                                          <DropdownMenuItem asChild>
                                            <Link href={`/dashboard/projects/${project.id}/edit`}>
                                              Edit Project
                                            </Link>
                                          </DropdownMenuItem>
                                        </DropdownMenuContent>
                                      </DropdownMenu>
                                    </div>
                                    
                                    <div className="flex items-center gap-1">
                                      <Badge className={getPriorityColor(project.priority)} variant="secondary">
                                        {project.priority}
                                      </Badge>
                                      <div 
                                        className="w-2 h-2 rounded-full" 
                                        style={{ backgroundColor: getWorkTypeColor(project.work_type_id) }}
                                      ></div>
                                    </div>
                                  </CardHeader>
                                  
                                  <CardContent className="pt-0">
                                    <div className="space-y-2">
                                      <div className="text-xs text-muted-foreground">
                                        {getWorkTypeName(project.work_type_id)}
                                      </div>
                                      
                                      {project.due_date && (
                                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                          <Calendar className="h-3 w-3" />
                                          Due {new Date(project.due_date).toLocaleDateString()}
                                        </div>
                                      )}

                                      {totalTasks > 0 && (
                                        <div className="space-y-1">
                                          <div className="flex justify-between text-xs">
                                            <span className="text-muted-foreground">Tasks</span>
                                            <span className="text-muted-foreground">
                                              {completedTasks}/{totalTasks}
                                            </span>
                                          </div>
                                          <div className="w-full bg-gray-200 rounded-full h-1.5">
                                            <div 
                                              className="bg-blue-600 h-1.5 rounded-full transition-all"
                                              style={{ 
                                                width: `${totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0}%` 
                                              }}
                                            />
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  </CardContent>
                                </Card>
                              )}
                            </Draggable>
                          )
                        })}
                      </div>
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </div>
            )
          })}
        </div>
      </DragDropContext>

      {filteredProjects.length === 0 && (
        <Card>
          <CardContent className="p-12 text-center">
            <div className="text-muted-foreground mb-4">
              {searchTerm ? (
                <>
                  <Search className="h-12 w-12 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No projects found</h3>
                  <p>Try adjusting your search terms</p>
                </>
              ) : (
                <>
                  <Plus className="h-12 w-12 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No projects yet</h3>
                  <p>Create your first project to get started</p>
                </>
              )}
            </div>
            {!searchTerm && (
              <Link href="/dashboard/projects/create">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Project
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}