"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
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
  Plus,
  Search,
  MoreHorizontal,
  Edit,
  Trash2,
  Copy,
  FileCheck,
  FolderOpen,
  CheckSquare,
  Clock,
  Star,
  Filter,
  Download,
  Upload,
} from "lucide-react"

interface Template {
  id: number
  name: string
  description: string
  type: "project" | "task" | "checklist"
  category: string
  tasks: number
  estimated_hours: number
  is_favorite: boolean
  usage_count: number
  created_at: string
  created_by: string
}

const mockTemplates: Template[] = [
  {
    id: 1,
    name: "Individual Tax Return Preparation",
    description: "Complete workflow for preparing individual tax returns",
    type: "project",
    category: "Tax Services",
    tasks: 12,
    estimated_hours: 8,
    is_favorite: true,
    usage_count: 45,
    created_at: "2024-01-15",
    created_by: "Admin User",
  },
  {
    id: 2,
    name: "Monthly Bookkeeping Checklist",
    description: "Standard checklist for monthly bookkeeping procedures",
    type: "checklist",
    category: "Bookkeeping",
    tasks: 8,
    estimated_hours: 4,
    is_favorite: false,
    usage_count: 23,
    created_at: "2024-01-10",
    created_by: "Manager User",
  },
  {
    id: 3,
    name: "Client Onboarding Process",
    description: "Complete client onboarding workflow with all necessary steps",
    type: "project",
    category: "Client Management",
    tasks: 15,
    estimated_hours: 6,
    is_favorite: true,
    usage_count: 67,
    created_at: "2024-01-05",
    created_by: "Admin User",
  },
  {
    id: 4,
    name: "Audit Documentation Review",
    description: "Systematic review of audit documentation and compliance",
    type: "task",
    category: "Audit",
    tasks: 1,
    estimated_hours: 3,
    is_favorite: false,
    usage_count: 12,
    created_at: "2024-01-01",
    created_by: "Senior Auditor",
  },
]

export default function TemplatesPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedType, setSelectedType] = useState<string>("")
  const [selectedCategory, setSelectedCategory] = useState<string>("")
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)

  const filteredTemplates = mockTemplates.filter((template) => {
    const matchesSearch = 
      template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      template.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesType = !selectedType || template.type === selectedType
    const matchesCategory = !selectedCategory || template.category === selectedCategory
    return matchesSearch && matchesType && matchesCategory
  })

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "project":
        return <FolderOpen className="h-4 w-4" />
      case "task":
        return <CheckSquare className="h-4 w-4" />
      case "checklist":
        return <FileCheck className="h-4 w-4" />
      default:
        return <FileCheck className="h-4 w-4" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case "project":
        return "bg-blue-100 text-blue-800"
      case "task":
        return "bg-green-100 text-green-800"
      case "checklist":
        return "bg-purple-100 text-purple-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getCategoryColor = (category: string) => {
    const colors = {
      "Tax Services": "bg-red-100 text-red-800",
      "Bookkeeping": "bg-green-100 text-green-800",
      "Audit": "bg-yellow-100 text-yellow-800",
      "Client Management": "bg-blue-100 text-blue-800",
    }
    return colors[category as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  const handleCreateTemplate = async (formData: FormData) => {
    console.log("Creating template:", Object.fromEntries(formData))
    setIsCreateDialogOpen(false)
  }

  const handleUseTemplate = (templateId: number) => {
    console.log("Using template:", templateId)
  }

  const handleDuplicateTemplate = (templateId: number) => {
    console.log("Duplicating template:", templateId)
  }

  const categories = Array.from(new Set(mockTemplates.map(t => t.category)))
  const typeStats = [
    { type: "project", count: mockTemplates.filter(t => t.type === "project").length },
    { type: "task", count: mockTemplates.filter(t => t.type === "task").length },
    { type: "checklist", count: mockTemplates.filter(t => t.type === "checklist").length },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Template Management</h1>
          <p className="text-gray-600 mt-1">Create and manage project, task, and checklist templates</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Template
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Create New Template</DialogTitle>
                <DialogDescription>
                  Create a reusable template for projects, tasks, or checklists.
                </DialogDescription>
              </DialogHeader>
              <form action={handleCreateTemplate} className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Template Name</label>
                  <Input name="name" placeholder="Enter template name" required />
                </div>
                <div>
                  <label className="text-sm font-medium">Description</label>
                  <Textarea name="description" placeholder="Enter description" rows={3} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium">Type</label>
                    <select name="type" className="w-full p-2 border rounded-md" required>
                      <option value="">Select type</option>
                      <option value="project">Project Template</option>
                      <option value="task">Task Template</option>
                      <option value="checklist">Checklist Template</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Category</label>
                    <select name="category" className="w-full p-2 border rounded-md" required>
                      <option value="">Select category</option>
                      {categories.map(category => (
                        <option key={category} value={category}>{category}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium">Estimated Hours</label>
                  <Input name="estimated_hours" type="number" placeholder="0" />
                </div>
                <Button type="submit" className="w-full">
                  Create Template
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Templates</p>
                <p className="text-2xl font-bold text-gray-900">{mockTemplates.length}</p>
              </div>
              <FileCheck className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
        {typeStats.map((stat) => (
          <Card key={stat.type}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 capitalize">{stat.type}s</p>
                  <p className="text-2xl font-bold text-gray-900">{stat.count}</p>
                </div>
                {getTypeIcon(stat.type)}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Search templates..."
                  className="pl-10"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline">
                    <Filter className="h-4 w-4 mr-2" />
                    Type: {selectedType || "All"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setSelectedType("")}>
                    All Types
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedType("project")}>
                    Project
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedType("task")}>
                    Task
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedType("checklist")}>
                    Checklist
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline">
                    Category: {selectedCategory || "All"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setSelectedCategory("")}>
                    All Categories
                  </DropdownMenuItem>
                  {categories.map((category) => (
                    <DropdownMenuItem
                      key={category}
                      onClick={() => setSelectedCategory(category)}
                    >
                      {category}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Templates */}
      <Tabs defaultValue="grid" className="space-y-6">
        <div className="flex justify-between items-center">
          <TabsList>
            <TabsTrigger value="grid">Grid View</TabsTrigger>
            <TabsTrigger value="list">List View</TabsTrigger>
          </TabsList>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>

        <TabsContent value="grid">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredTemplates.map((template) => (
              <Card key={template.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-lg">{template.name}</CardTitle>
                        {template.is_favorite && (
                          <Star className="h-4 w-4 text-yellow-500 fill-current" />
                        )}
                      </div>
                      <CardDescription className="mt-1">
                        {template.description}
                      </CardDescription>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent>
                        <DropdownMenuItem onClick={() => handleUseTemplate(template.id)}>
                          <FolderOpen className="h-4 w-4 mr-2" />
                          Use Template
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDuplicateTemplate(template.id)}>
                          <Copy className="h-4 w-4 mr-2" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Edit className="h-4 w-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-red-600">
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge className={getTypeColor(template.type)}>
                      <span className="flex items-center gap-1">
                        {getTypeIcon(template.type)}
                        {template.type}
                      </span>
                    </Badge>
                    <Badge className={getCategoryColor(template.category)} variant="secondary">
                      {template.category}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <CheckSquare className="h-4 w-4 text-blue-600" />
                        <div>
                          <p className="text-gray-600">Tasks</p>
                          <p className="font-semibold">{template.tasks}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-green-600" />
                        <div>
                          <p className="text-gray-600">Est. Hours</p>
                          <p className="font-semibold">{template.estimated_hours}h</p>
                        </div>
                      </div>
                    </div>
                    <div className="pt-3 border-t">
                      <div className="flex justify-between items-center text-xs text-gray-600">
                        <span>Used {template.usage_count} times</span>
                        <span>by {template.created_by}</span>
                      </div>
                    </div>
                    <Button className="w-full" onClick={() => handleUseTemplate(template.id)}>
                      Use Template
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="list">
          <Card>
            <CardContent className="p-0">
              <div className="divide-y">
                {filteredTemplates.map((template) => (
                  <div key={template.id} className="p-6 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-2">
                            {getTypeIcon(template.type)}
                            <h3 className="font-semibold">{template.name}</h3>
                            {template.is_favorite && (
                              <Star className="h-4 w-4 text-yellow-500 fill-current" />
                            )}
                          </div>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                        <div className="flex items-center gap-4 mt-2">
                          <Badge className={getTypeColor(template.type)}>
                            {template.type}
                          </Badge>
                          <Badge className={getCategoryColor(template.category)} variant="secondary">
                            {template.category}
                          </Badge>
                          <span className="text-xs text-gray-500">
                            {template.tasks} tasks • {template.estimated_hours}h • Used {template.usage_count} times
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button size="sm" onClick={() => handleUseTemplate(template.id)}>
                          Use Template
                        </Button>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent>
                            <DropdownMenuItem onClick={() => handleDuplicateTemplate(template.id)}>
                              <Copy className="h-4 w-4 mr-2" />
                              Duplicate
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Edit className="h-4 w-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem className="text-red-600">
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {filteredTemplates.length === 0 && (
        <div className="text-center py-12">
          <FileCheck className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">No templates found</p>
        </div>
      )}
    </div>
  )
}