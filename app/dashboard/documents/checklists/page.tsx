"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  ClipboardCheck,
  Plus,
  Search,
  FileText,
  CheckCircle,
  Circle,
} from "lucide-react"

export default function ChecklistsPage() {
  const mockChecklists = [
    {
      id: 1,
      name: "Tax Return Preparation Checklist",
      description: "Standard checklist for individual tax returns",
      items: 12,
      completed: 8,
      category: "Tax Services",
    },
    {
      id: 2,
      name: "Client Onboarding Checklist",
      description: "New client onboarding process steps",
      items: 15,
      completed: 15,
      category: "Client Management",
    },
    {
      id: 3,
      name: "Audit Documentation Review",
      description: "Checklist for audit documentation compliance",
      items: 20,
      completed: 5,
      category: "Audit",
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Document Checklists</h1>
          <p className="text-muted-foreground">Manage and track checklist completion</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          New Checklist
        </Button>
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search checklists..."
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {mockChecklists.map((checklist) => (
          <Card key={checklist.id} className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader>
              <div className="flex items-start justify-between">
                <ClipboardCheck className="h-8 w-8 text-blue-600" />
                <div className="text-right">
                  <div className="text-sm text-muted-foreground">
                    {checklist.completed}/{checklist.items} items
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {Math.round((checklist.completed / checklist.items) * 100)}% complete
                  </div>
                </div>
              </div>
              <CardTitle className="text-lg">{checklist.name}</CardTitle>
              <CardDescription>{checklist.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ 
                      width: `${(checklist.completed / checklist.items) * 100}%` 
                    }}
                  />
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-muted-foreground">{checklist.category}</span>
                  <div className="flex items-center gap-1">
                    {checklist.completed === checklist.items ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <Circle className="h-4 w-4 text-gray-400" />
                    )}
                    <span>
                      {checklist.completed === checklist.items ? "Complete" : "In Progress"}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}