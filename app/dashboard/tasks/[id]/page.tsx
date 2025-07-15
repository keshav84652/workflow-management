"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Calendar,
  User,
  FolderOpen,
  Clock,
  Edit,
  Save,
  X,
  MoreHorizontal,
  MessageSquare,
  Paperclip,
  Eye,
  Trash2,
  CheckCircle,
  AlertCircle,
  Loader2,
  ArrowLeft,
} from "lucide-react"
import { useTask, useTaskMutations, useProjects, useUsers } from "@/lib/hooks"

export default function TaskDetailPage() {
  const params = useParams()
  const router = useRouter()
  const taskId = parseInt(params.id as string)
  
  const { data: task, loading, error, refetch } = useTask(taskId)
  const { updateTask, updateTaskStatus, deleteTask, loading: mutationLoading } = useTaskMutations()
  const { data: projects } = useProjects()
  const { data: users } = useUsers()

  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState({
    title: "",
    description: "",
    status: "",
    priority: "",
    project_id: "",
    assigned_to: "",
    due_date: "",
  })

  useEffect(() => {
    if (task) {
      setEditData({
        title: task.title || "",
        description: task.description || "",
        status: task.status || "",
        priority: task.priority || "",
        project_id: task.project_id?.toString() || "",
        assigned_to: task.assigned_to?.toString() || "",
        due_date: task.due_date ? task.due_date.split('T')[0] : "",
      })
    }
  }, [task])

  const handleSave = async () => {
    const updateData = {
      ...editData,
      project_id: editData.project_id && editData.project_id !== "none" ? parseInt(editData.project_id) : undefined,
      assigned_to: editData.assigned_to && editData.assigned_to !== "unassigned" ? parseInt(editData.assigned_to) : undefined,
    }
    const result = await updateTask(taskId, updateData)
    if (result.success) {
      setIsEditing(false)
      refetch()
    }
  }

  const handleStatusChange = async (newStatus: string) => {
    const result = await updateTaskStatus(taskId, newStatus)
    if (result.success) {
      refetch()
    }
  }

  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this task?")) {
      const result = await deleteTask(taskId)
      if (result.success) {
        router.push("/dashboard/tasks")
      }
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "High":
        return "bg-red-100 text-red-800"
      case "Medium":
        return "bg-yellow-100 text-yellow-800"
      case "Low":
        return "bg-green-100 text-green-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Todo":
        return "bg-gray-100 text-gray-800"
      case "In Progress":
        return "bg-blue-100 text-blue-800"
      case "Review":
        return "bg-yellow-100 text-yellow-800"
      case "Completed":
        return "bg-green-100 text-green-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "Completed":
        return <CheckCircle className="h-4 w-4" />
      case "In Progress":
        return <Clock className="h-4 w-4" />
      default:
        return <AlertCircle className="h-4 w-4" />
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 mb-4">{error || "Task not found"}</p>
        <Button onClick={() => router.back()} variant="outline">
          Go Back
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => router.back()}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            {isEditing ? (
              <Input
                value={editData.title}
                onChange={(e) => setEditData(prev => ({ ...prev, title: e.target.value }))}
                className="text-2xl font-bold border-none p-0 h-auto"
              />
            ) : (
              <h1 className="text-3xl font-bold text-gray-900">{task.title}</h1>
            )}
            <div className="flex items-center gap-3 mt-2">
              <Badge className={getStatusColor(task.status)}>
                <span className="flex items-center gap-1">
                  {getStatusIcon(task.status)}
                  {task.status}
                </span>
              </Badge>
              <Badge className={getPriorityColor(task.priority)}>
                {task.priority}
              </Badge>
              {task.project_name && (
                <Badge variant="secondary">
                  <FolderOpen className="h-3 w-3 mr-1" />
                  {task.project_name}
                </Badge>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {isEditing ? (
            <>
              <Button variant="outline" onClick={() => setIsEditing(false)}>
                <X className="h-4 w-4 mr-2" />
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={mutationLoading}>
                <Save className="h-4 w-4 mr-2" />
                Save
              </Button>
            </>
          ) : (
            <>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline">
                    Status: {task.status}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleStatusChange("Todo")}>
                    Todo
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleStatusChange("In Progress")}>
                    In Progress
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleStatusChange("Review")}>
                    Review
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleStatusChange("Completed")}>
                    Completed
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Button onClick={() => setIsEditing(true)}>
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem>
                    <Eye className="h-4 w-4 mr-2" />
                    View History
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Paperclip className="h-4 w-4 mr-2" />
                    Add Attachment
                  </DropdownMenuItem>
                  <DropdownMenuItem className="text-red-600" onClick={handleDelete}>
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete Task
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          )}
        </div>
      </div>

      <Tabs defaultValue="details" className="space-y-6">
        <TabsList>
          <TabsTrigger value="details">Details</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="attachments">Attachments</TabsTrigger>
        </TabsList>

        <TabsContent value="details" className="space-y-6">
          {/* Task Information */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              {/* Description */}
              <Card>
                <CardHeader>
                  <CardTitle>Description</CardTitle>
                </CardHeader>
                <CardContent>
                  {isEditing ? (
                    <Textarea
                      value={editData.description}
                      onChange={(e) => setEditData(prev => ({ ...prev, description: e.target.value }))}
                      rows={6}
                      placeholder="Enter task description"
                    />
                  ) : (
                    <p className="text-gray-700 whitespace-pre-wrap">
                      {task.description || "No description provided."}
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Comments Section */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5" />
                    Comments
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="text-center py-8 text-gray-500">
                      No comments yet. Be the first to add a comment.
                    </div>
                    <div className="flex gap-2">
                      <Input placeholder="Add a comment..." />
                      <Button size="sm">Post</Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-6">
              {/* Task Details */}
              <Card>
                <CardHeader>
                  <CardTitle>Task Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Assignee */}
                  <div>
                    <label className="text-sm font-medium text-gray-600">Assigned To</label>
                    {isEditing ? (
                      <Select
                        value={editData.assigned_to}
                        onValueChange={(value) => setEditData(prev => ({ ...prev, assigned_to: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select assignee" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="unassigned">Unassigned</SelectItem>
                          {users?.map((user) => (
                            <SelectItem key={user.id} value={user.id.toString()}>
                              {user.username}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <div className="flex items-center gap-2 mt-1">
                        <User className="h-4 w-4 text-gray-400" />
                        <span>{task.assigned_to_name || "Unassigned"}</span>
                      </div>
                    )}
                  </div>

                  {/* Project */}
                  <div>
                    <label className="text-sm font-medium text-gray-600">Project</label>
                    {isEditing ? (
                      <Select
                        value={editData.project_id}
                        onValueChange={(value) => setEditData(prev => ({ ...prev, project_id: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select project" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">No project</SelectItem>
                          {projects?.map((project) => (
                            <SelectItem key={project.id} value={project.id.toString()}>
                              {project.title}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <div className="flex items-center gap-2 mt-1">
                        <FolderOpen className="h-4 w-4 text-gray-400" />
                        <span>{task.project_name || "No project"}</span>
                      </div>
                    )}
                  </div>

                  {/* Due Date */}
                  <div>
                    <label className="text-sm font-medium text-gray-600">Due Date</label>
                    {isEditing ? (
                      <Input
                        type="date"
                        value={editData.due_date}
                        onChange={(e) => setEditData(prev => ({ ...prev, due_date: e.target.value }))}
                      />
                    ) : (
                      <div className="flex items-center gap-2 mt-1">
                        <Calendar className="h-4 w-4 text-gray-400" />
                        <span>
                          {task.due_date ? new Date(task.due_date).toLocaleDateString() : "No due date"}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Priority */}
                  <div>
                    <label className="text-sm font-medium text-gray-600">Priority</label>
                    {isEditing ? (
                      <Select
                        value={editData.priority}
                        onValueChange={(value) => setEditData(prev => ({ ...prev, priority: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Low">Low</SelectItem>
                          <SelectItem value="Medium">Medium</SelectItem>
                          <SelectItem value="High">High</SelectItem>
                        </SelectContent>
                      </Select>
                    ) : (
                      <Badge className={getPriorityColor(task.priority)} variant="secondary">
                        {task.priority}
                      </Badge>
                    )}
                  </div>

                  {/* Timestamps */}
                  <div className="pt-4 border-t">
                    <div className="text-xs text-gray-500 space-y-1">
                      <p>Created: {new Date(task.created_at).toLocaleString()}</p>
                      <p>Updated: {new Date(task.updated_at).toLocaleString()}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="activity">
          <Card>
            <CardHeader>
              <CardTitle>Activity Timeline</CardTitle>
              <CardDescription>Task history and updates</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                No activity recorded yet.
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="attachments">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Paperclip className="h-5 w-5" />
                Attachments
              </CardTitle>
              <CardDescription>Files and documents related to this task</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                No attachments yet. Drag and drop files or click to upload.
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}