"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  LayoutDashboard,
  FileText,
  Download,
  Eye,
  Clock,
  CheckCircle,
  AlertCircle,
  Users,
} from "lucide-react"

export default function ClientPortalDashboardPage() {
  const mockClientDashboards = [
    {
      id: 1,
      clientName: "ABC Corporation",
      activeProjects: 3,
      pendingTasks: 8,
      completedTasks: 15,
      documentsShared: 12,
      lastActivity: "2024-01-15",
    },
    {
      id: 2,
      clientName: "XYZ Industries", 
      activeProjects: 2,
      pendingTasks: 5,
      completedTasks: 22,
      documentsShared: 8,
      lastActivity: "2024-01-14",
    },
    {
      id: 3,
      clientName: "Tech Solutions Inc",
      activeProjects: 1,
      pendingTasks: 3,
      completedTasks: 7,
      documentsShared: 5,
      lastActivity: "2024-01-10",
    },
  ]

  const mockRecentDocuments = [
    {
      id: 1,
      name: "Q4 Financial Report",
      client: "ABC Corporation",
      sharedAt: "2024-01-15",
      downloads: 3,
      status: "Viewed",
    },
    {
      id: 2,
      name: "Tax Return Package",
      client: "XYZ Industries",
      sharedAt: "2024-01-14", 
      downloads: 1,
      status: "Downloaded",
    },
    {
      id: 3,
      name: "Audit Summary",
      client: "Tech Solutions Inc",
      sharedAt: "2024-01-13",
      downloads: 0,
      status: "Pending",
    },
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Viewed":
        return "bg-blue-100 text-blue-800"
      case "Downloaded":
        return "bg-green-100 text-green-800"
      case "Pending":
        return "bg-yellow-100 text-yellow-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Client Portal Dashboard</h1>
          <p className="text-muted-foreground">Monitor client portal activity and engagement</p>
        </div>
        <Button>
          <LayoutDashboard className="h-4 w-4 mr-2" />
          Customize Portal
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Active Clients</p>
                <p className="text-2xl font-bold">{mockClientDashboards.length}</p>
              </div>
              <Users className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Projects</p>
                <p className="text-2xl font-bold">
                  {mockClientDashboards.reduce((sum, c) => sum + c.activeProjects, 0)}
                </p>
              </div>
              <LayoutDashboard className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Documents Shared</p>
                <p className="text-2xl font-bold">
                  {mockClientDashboards.reduce((sum, c) => sum + c.documentsShared, 0)}
                </p>
              </div>
              <FileText className="h-8 w-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Pending Tasks</p>
                <p className="text-2xl font-bold">
                  {mockClientDashboards.reduce((sum, c) => sum + c.pendingTasks, 0)}
                </p>
              </div>
              <Clock className="h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Client Activity</CardTitle>
            <CardDescription>Overview of client portal engagement</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockClientDashboards.map((client) => (
                <div key={client.id} className="flex items-center gap-4 p-4 border rounded-lg">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                      <Users className="h-5 w-5 text-blue-600" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium mb-1">{client.clientName}</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm text-muted-foreground">
                      <span>{client.activeProjects} projects</span>
                      <span>{client.pendingTasks} pending tasks</span>
                      <span>{client.documentsShared} documents</span>
                      <span>Last: {new Date(client.lastActivity).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1">
                    <Badge variant="secondary">
                      {client.completedTasks} completed
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Document Activity</CardTitle>
            <CardDescription>Latest document sharing and downloads</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockRecentDocuments.map((doc) => (
                <div key={doc.id} className="flex items-center gap-4 p-4 border rounded-lg">
                  <div className="flex-shrink-0">
                    <FileText className="h-8 w-8 text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium truncate">{doc.name}</h3>
                      <Badge className={getStatusColor(doc.status)} variant="secondary">
                        {doc.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{doc.client}</span>
                      <span>•</span>
                      <span>{new Date(doc.sharedAt).toLocaleDateString()}</span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Download className="h-3 w-3" />
                        {doc.downloads} downloads
                      </span>
                    </div>
                  </div>
                  <Button size="sm" variant="outline">
                    <Eye className="h-3 w-3 mr-1" />
                    View
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Portal Features</CardTitle>
          <CardDescription>Available features for client portal customization</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center p-6 border rounded-lg">
              <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
              <h3 className="font-semibold mb-2">Project Tracking</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Allow clients to view project progress and milestones
              </p>
              <Button variant="outline" className="w-full">
                Configure
              </Button>
            </div>
            <div className="text-center p-6 border rounded-lg">
              <FileText className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h3 className="font-semibold mb-2">Document Access</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Secure document sharing and download tracking
              </p>
              <Button variant="outline" className="w-full">
                Manage
              </Button>
            </div>
            <div className="text-center p-6 border rounded-lg">
              <AlertCircle className="h-12 w-12 text-orange-600 mx-auto mb-4" />
              <h3 className="font-semibold mb-2">Notifications</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Automated email notifications for updates and deadlines
              </p>
              <Button variant="outline" className="w-full">
                Setup
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}