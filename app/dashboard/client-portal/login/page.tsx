"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Shield,
  Key,
  Users,
  Mail,
  Clock,
  CheckCircle,
} from "lucide-react"

export default function ClientPortalLoginPage() {
  const mockClientLogins = [
    {
      id: 1,
      clientName: "ABC Corporation",
      email: "admin@abccorp.com",
      lastLogin: "2024-01-15 10:30 AM",
      status: "Active",
      accessLevel: "Full Access",
    },
    {
      id: 2,
      clientName: "XYZ Industries",
      email: "finance@xyzind.com", 
      lastLogin: "2024-01-14 02:15 PM",
      status: "Active",
      accessLevel: "Limited Access",
    },
    {
      id: 3,
      clientName: "Tech Solutions Inc",
      email: "hr@techsol.com",
      lastLogin: "2024-01-10 09:45 AM",
      status: "Inactive",
      accessLevel: "View Only",
    },
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Active":
        return "bg-green-100 text-green-800"
      case "Inactive":
        return "bg-red-100 text-red-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Client Portal Login</h1>
          <p className="text-muted-foreground">Manage client portal access and authentication</p>
        </div>
        <Button>
          <Shield className="h-4 w-4 mr-2" />
          Create Access
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="text-center">
              <Shield className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h3 className="font-semibold mb-2">Secure Access</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Provide clients secure access to their documents and project status
              </p>
              <Button className="w-full">
                Generate Login
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="text-center">
              <Key className="h-12 w-12 text-green-600 mx-auto mb-4" />
              <h3 className="font-semibold mb-2">Access Control</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Set permissions and control what clients can view and access
              </p>
              <Button variant="outline" className="w-full">
                Manage Permissions
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="text-center">
              <Users className="h-12 w-12 text-purple-600 mx-auto mb-4" />
              <h3 className="font-semibold mb-2">User Management</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Add multiple users per client with different access levels
              </p>
              <Button variant="outline" className="w-full">
                Add Users
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Client Access Overview</CardTitle>
          <CardDescription>Current client portal access and login status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockClientLogins.map((client) => (
              <div key={client.id} className="flex items-center gap-4 p-4 border rounded-lg">
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                    <Users className="h-5 w-5 text-blue-600" />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium">{client.clientName}</h3>
                    <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(client.status)}`}>
                      {client.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {client.email}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Last login: {client.lastLogin}
                    </span>
                    <span className="flex items-center gap-1">
                      <Shield className="h-3 w-3" />
                      {client.accessLevel}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline">
                    Edit Access
                  </Button>
                  <Button size="sm" variant="outline">
                    Reset Password
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6 text-center">
            <div className="text-2xl font-bold text-blue-600">
              {mockClientLogins.filter(c => c.status === "Active").length}
            </div>
            <div className="text-sm text-muted-foreground">Active Logins</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 text-center">
            <div className="text-2xl font-bold text-red-600">
              {mockClientLogins.filter(c => c.status === "Inactive").length}
            </div>
            <div className="text-sm text-muted-foreground">Inactive Logins</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 text-center">
            <div className="text-2xl font-bold text-green-600">
              {mockClientLogins.filter(c => c.accessLevel === "Full Access").length}
            </div>
            <div className="text-sm text-muted-foreground">Full Access</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 text-center">
            <div className="text-2xl font-bold text-purple-600">{mockClientLogins.length}</div>
            <div className="text-sm text-muted-foreground">Total Clients</div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}