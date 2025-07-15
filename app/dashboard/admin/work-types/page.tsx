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
  Plus,
  Search,
  MoreHorizontal,
  Edit,
  Trash2,
  Settings2,
  Clock,
  DollarSign,
  Tag,
  FileText,
  Loader2,
  CheckCircle,
} from "lucide-react"
import { useWorkTypes } from "@/lib/hooks"

interface WorkType {
  id: number
  name: string
  description: string
  category: string
  default_rate: number
  estimated_hours: number
  is_active: boolean
  created_at: string
}

export default function WorkTypesPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedCategory, setSelectedCategory] = useState<string>("")
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [editingWorkType, setEditingWorkType] = useState<WorkType | null>(null)

  const { data: workTypes, loading, error, refetch } = useWorkTypes()

  // Mock data for demonstration since useWorkTypes might not return structured data
  const mockWorkTypes: WorkType[] = [
    {
      id: 1,
      name: "Tax Preparation - Individual",
      description: "Individual tax return preparation and filing",
      category: "Tax Services",
      default_rate: 150,
      estimated_hours: 3,
      is_active: true,
      created_at: "2024-01-15",
    },
    {
      id: 2,
      name: "Bookkeeping - Monthly",
      description: "Monthly bookkeeping and reconciliation services",
      category: "Bookkeeping",
      default_rate: 75,
      estimated_hours: 8,
      is_active: true,
      created_at: "2024-01-10",
    },
    {
      id: 3,
      name: "Audit - Small Business",
      description: "Annual audit for small business entities",
      category: "Audit",
      default_rate: 200,
      estimated_hours: 40,
      is_active: true,
      created_at: "2024-01-05",
    },
    {
      id: 4,
      name: "Payroll Processing",
      description: "Bi-weekly payroll processing and compliance",
      category: "Payroll",
      default_rate: 50,
      estimated_hours: 2,
      is_active: true,
      created_at: "2024-01-01",
    },
    {
      id: 5,
      name: "Financial Consulting",
      description: "General financial advisory and consulting",
      category: "Consulting",
      default_rate: 250,
      estimated_hours: 1,
      is_active: false,
      created_at: "2023-12-15",
    },
  ]

  const displayWorkTypes = workTypes && Array.isArray(workTypes) ? workTypes : mockWorkTypes

  const filteredWorkTypes = displayWorkTypes.filter((workType) => {
    const matchesSearch = 
      workType.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      workType.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = !selectedCategory || workType.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  const categories = Array.from(new Set(displayWorkTypes.map(wt => wt.category)))

  const getCategoryColor = (category: string) => {
    const colors = {
      "Tax Services": "bg-blue-100 text-blue-800",
      "Bookkeeping": "bg-green-100 text-green-800",
      "Audit": "bg-red-100 text-red-800",
      "Payroll": "bg-yellow-100 text-yellow-800",
      "Consulting": "bg-purple-100 text-purple-800",
    }
    return colors[category as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  const handleCreateWorkType = async (formData: FormData) => {
    // Mock implementation - in real app, this would call an API
    console.log("Creating work type:", Object.fromEntries(formData))
    setIsCreateDialogOpen(false)
    // refetch()
  }

  const handleEditWorkType = (workType: WorkType) => {
    setEditingWorkType(workType)
  }

  const handleDeleteWorkType = async (workTypeId: number) => {
    if (confirm("Are you sure you want to delete this work type?")) {
      // Mock implementation
      console.log("Deleting work type:", workTypeId)
      // await deleteWorkType(workTypeId)
      // refetch()
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 mb-4">{error}</p>
        <Button onClick={refetch} variant="outline">
          Try Again
        </Button>
      </div>
    )
  }

  const categoryStats = categories.map(category => ({
    category,
    count: displayWorkTypes.filter(wt => wt.category === category).length,
    avgRate: Math.round(
      displayWorkTypes
        .filter(wt => wt.category === category)
        .reduce((sum, wt) => sum + wt.default_rate, 0) / 
      displayWorkTypes.filter(wt => wt.category === category).length
    )
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Work Types Management</h1>
          <p className="text-gray-600 mt-1">Configure work types, rates, and service categories</p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Work Type
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Create New Work Type</DialogTitle>
              <DialogDescription>
                Define a new work type with default rates and estimated hours.
              </DialogDescription>
            </DialogHeader>
            <form action={handleCreateWorkType} className="space-y-4">
              <div>
                <label className="text-sm font-medium">Name</label>
                <Input name="name" placeholder="Enter work type name" required />
              </div>
              <div>
                <label className="text-sm font-medium">Description</label>
                <Textarea name="description" placeholder="Enter description" rows={3} />
              </div>
              <div>
                <label className="text-sm font-medium">Category</label>
                <select name="category" className="w-full p-2 border rounded-md" required>
                  <option value="">Select category</option>
                  {categories.map(category => (
                    <option key={category} value={category}>{category}</option>
                  ))}
                  <option value="new">+ Add New Category</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">Default Rate ($)</label>
                  <Input name="default_rate" type="number" placeholder="0" required />
                </div>
                <div>
                  <label className="text-sm font-medium">Est. Hours</label>
                  <Input name="estimated_hours" type="number" placeholder="0" required />
                </div>
              </div>
              <Button type="submit" className="w-full">
                Create Work Type
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Work Types</p>
                <p className="text-2xl font-bold text-gray-900">{displayWorkTypes.length}</p>
              </div>
              <Settings2 className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Types</p>
                <p className="text-2xl font-bold text-green-900">
                  {displayWorkTypes.filter(wt => wt.is_active).length}
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Rate</p>
                <p className="text-2xl font-bold text-purple-900">
                  ${Math.round(displayWorkTypes.reduce((sum, wt) => sum + wt.default_rate, 0) / displayWorkTypes.length)}
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Categories</p>
                <p className="text-2xl font-bold text-orange-900">{categories.length}</p>
              </div>
              <Tag className="h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Category Stats */}
      <Card>
        <CardHeader>
          <CardTitle>Categories Overview</CardTitle>
          <CardDescription>Work type distribution by category</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {categoryStats.map((stat) => (
              <div key={stat.category} className="text-center p-4 bg-gray-50 rounded-lg">
                <Badge className={getCategoryColor(stat.category)} variant="secondary">
                  {stat.category}
                </Badge>
                <p className="text-lg font-bold text-gray-900 mt-2">{stat.count}</p>
                <p className="text-sm text-gray-600">types</p>
                <p className="text-sm text-blue-600 font-medium">${stat.avgRate} avg</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Search work types..."
                  className="pl-10"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <Tag className="h-4 w-4 mr-2" />
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
        </CardContent>
      </Card>

      {/* Work Types Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredWorkTypes.map((workType) => (
          <Card key={workType.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-lg">{workType.name}</CardTitle>
                  <CardDescription className="mt-1">
                    {workType.description}
                  </CardDescription>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => handleEditWorkType(workType)}>
                      <Edit className="h-4 w-4 mr-2" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem 
                      className="text-red-600"
                      onClick={() => handleDeleteWorkType(workType.id)}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <Badge className={getCategoryColor(workType.category)}>
                  {workType.category}
                </Badge>
                <Badge variant={workType.is_active ? "default" : "secondary"}>
                  {workType.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-green-600" />
                  <div>
                    <p className="text-sm text-gray-600">Default Rate</p>
                    <p className="font-semibold">${workType.default_rate}/hr</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-blue-600" />
                  <div>
                    <p className="text-sm text-gray-600">Est. Hours</p>
                    <p className="font-semibold">{workType.estimated_hours}h</p>
                  </div>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t">
                <p className="text-xs text-gray-500">
                  Created: {new Date(workType.created_at).toLocaleDateString()}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredWorkTypes.length === 0 && (
        <div className="text-center py-12">
          <Settings2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">No work types found</p>
        </div>
      )}
    </div>
  )
}