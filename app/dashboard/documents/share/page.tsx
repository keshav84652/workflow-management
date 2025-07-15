"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Share2,
  Plus,
  Search,
  Link,
  Mail,
  Copy,
  Eye,
  Calendar,
  Users,
} from "lucide-react"

export default function ShareDocumentsPage() {
  const mockSharedLinks = [
    {
      id: 1,
      name: "Q4 Financial Report",
      recipient: "client@abccorp.com",
      sharedAt: "2024-01-15",
      expiresAt: "2024-02-15", 
      status: "Active",
      views: 3,
    },
    {
      id: 2,
      name: "Tax Documents Package",
      recipient: "john.doe@example.com",
      sharedAt: "2024-01-14",
      expiresAt: "2024-01-21",
      status: "Active",
      views: 7,
    },
    {
      id: 3,
      name: "Audit Report Draft",
      recipient: "manager@firm.com",
      sharedAt: "2024-01-13",
      expiresAt: "2024-01-20",
      status: "Expired",
      views: 12,
    },
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Active":
        return "bg-green-100 text-green-800"
      case "Expired":
        return "bg-red-100 text-red-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Share Documents</h1>
          <p className="text-muted-foreground">Create secure sharing links for documents</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Share Link
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="text-center">
              <Link className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h3 className="font-semibold mb-2">Secure Sharing</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Create password-protected links with expiration dates
              </p>
              <Button className="w-full">
                Create Link
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="text-center">
              <Mail className="h-12 w-12 text-green-600 mx-auto mb-4" />
              <h3 className="font-semibold mb-2">Email Sharing</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Send documents directly via email with tracking
              </p>
              <Button variant="outline" className="w-full">
                Send Email
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="text-center">
              <Users className="h-12 w-12 text-purple-600 mx-auto mb-4" />
              <h3 className="font-semibold mb-2">Team Sharing</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Share with internal team members and collaborators
              </p>
              <Button variant="outline" className="w-full">
                Share Internal
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search shared documents..."
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Shared Links</CardTitle>
          <CardDescription>Manage active and expired sharing links</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockSharedLinks.map((link) => (
              <div key={link.id} className="flex items-center gap-4 p-4 border rounded-lg">
                <div className="flex-shrink-0">
                  <Share2 className="h-8 w-8 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium">{link.name}</h3>
                    <Badge className={getStatusColor(link.status)} variant="secondary">
                      {link.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {link.recipient}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      Expires {new Date(link.expiresAt).toLocaleDateString()}
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye className="h-3 w-3" />
                      {link.views} views
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline">
                    <Copy className="h-3 w-3 mr-1" />
                    Copy Link
                  </Button>
                  <Button size="sm" variant="outline">
                    View Details
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Quick Stats</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {mockSharedLinks.filter(l => l.status === "Active").length}
              </div>
              <div className="text-sm text-muted-foreground">Active Links</div>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-red-600">
                {mockSharedLinks.filter(l => l.status === "Expired").length}
              </div>
              <div className="text-sm text-muted-foreground">Expired Links</div>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                {mockSharedLinks.reduce((sum, l) => sum + l.views, 0)}
              </div>
              <div className="text-sm text-muted-foreground">Total Views</div>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {mockSharedLinks.length}
              </div>
              <div className="text-sm text-muted-foreground">Total Shares</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}