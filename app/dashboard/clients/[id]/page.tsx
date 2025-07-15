"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  ArrowLeft,
  Edit,
  Mail,
  Phone,
  MapPin,
  Building2,
  FileText,
  Calendar,
  DollarSign,
  Users,
  MoreHorizontal,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface ClientData {
  id: number
  name: string
  email: string
  phone: string
  address: string
  city: string
  state: string
  zip_code: string
  tax_id: string
  industry: string
  contact_person: string
  notes: string
  status: string
  created_at: string
  projects: any[]
  total_revenue: number
  last_activity: string
}

export default function ClientDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [client, setClient] = useState<ClientData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Mock client data
    const mockClient: ClientData = {
      id: parseInt(params.id),
      name: "ABC Corporation",
      email: "finance@abccorp.com",
      phone: "(555) 123-4567",
      address: "123 Business Avenue",
      city: "New York",
      state: "NY",
      zip_code: "10001",
      tax_id: "12-3456789",
      industry: "Technology",
      contact_person: "John Smith",
      notes: "Long-term client with annual tax preparation and quarterly reviews. Very responsive and pays invoices promptly.",
      status: "active",
      created_at: "2023-01-15",
      last_activity: "2024-01-20",
      total_revenue: 45000,
      projects: [
        {
          id: 1,
          name: "Q4 Financial Review",
          status: "in_progress",
          start_date: "2024-01-15",
          due_date: "2024-02-15",
          budget: 15000,
        },
        {
          id: 2,
          name: "Annual Tax Return",
          status: "completed",
          start_date: "2023-03-01",
          due_date: "2023-04-15",
          budget: 12000,
        },
        {
          id: 3,
          name: "Quarterly Review Q3",
          status: "completed",
          start_date: "2023-10-01",
          due_date: "2023-10-31",
          budget: 8000,
        },
      ],
    }

    setClient(mockClient)
    setLoading(false)
  }, [params.id])

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-100 text-green-800"
      case "inactive":
        return "bg-red-100 text-red-800"
      case "prospective":
        return "bg-yellow-100 text-yellow-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getProjectStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800"
      case "in_progress":
        return "bg-blue-100 text-blue-800"
      case "planning":
        return "bg-yellow-100 text-yellow-800"
      case "on_hold":
        return "bg-orange-100 text-orange-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg">Loading client details...</div>
      </div>
    )
  }

  if (!client) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg">Client not found</div>
      </div>
    )
  }

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
            <h1 className="text-3xl font-bold">{client.name}</h1>
            <p className="text-muted-foreground">Client #{client.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            onClick={() => router.push(`/dashboard/clients/${client.id}/edit`)}
          >
            <Edit className="h-4 w-4 mr-2" />
            Edit Client
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
                Generate Report
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Mail className="h-4 w-4 mr-2" />
                Send Email
              </DropdownMenuItem>
              <DropdownMenuItem className="text-red-600">
                Archive Client
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Client Information</CardTitle>
              <CardDescription>Basic client details and contact information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Status</span>
                <Badge className={getStatusColor(client.status)} variant="secondary">
                  {client.status.toUpperCase()}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Contact Person</span>
                <span className="text-sm text-muted-foreground">{client.contact_person}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="font-medium">Industry</span>
                <span className="text-sm text-muted-foreground">{client.industry}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="font-medium">Tax ID</span>
                <span className="text-sm text-muted-foreground">{client.tax_id}</span>
              </div>

              <Separator />

              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{client.email}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{client.phone}</span>
                </div>
                <div className="flex items-start gap-3">
                  <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
                  <div className="text-sm">
                    <div>{client.address}</div>
                    <div>{client.city}, {client.state} {client.zip_code}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-2">
                <span className="font-medium">Notes</span>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {client.notes}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Client Projects</CardTitle>
              <CardDescription>Projects associated with this client</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {client.projects.map((project) => (
                  <div key={project.id} className="flex items-center gap-4 p-4 border rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium">{project.name}</h4>
                        <Badge className={getProjectStatusColor(project.status)} variant="secondary">
                          {project.status.replace('_', ' ')}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(project.start_date).toLocaleDateString()} - {new Date(project.due_date).toLocaleDateString()}
                        </span>
                        <span className="flex items-center gap-1">
                          <DollarSign className="h-3 w-3" />
                          ${project.budget.toLocaleString()}
                        </span>
                      </div>
                    </div>
                    <Button size="sm" variant="outline">
                      View Project
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
              <CardTitle>Client Statistics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Total Revenue</span>
                <span className="text-lg font-bold text-green-600">
                  ${client.total_revenue.toLocaleString()}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Total Projects</span>
                <span className="text-lg font-bold">{client.projects.length}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Active Projects</span>
                <span className="text-lg font-bold text-blue-600">
                  {client.projects.filter(p => p.status === 'in_progress').length}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="font-medium">Completed Projects</span>
                <span className="text-lg font-bold text-green-600">
                  {client.projects.filter(p => p.status === 'completed').length}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5 text-green-600" />
                <div>
                  <div className="font-medium">Client Since</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(client.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5 text-blue-600" />
                <div>
                  <div className="font-medium">Last Activity</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(client.last_activity).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button className="w-full" variant="outline">
                <Mail className="h-4 w-4 mr-2" />
                Send Email
              </Button>
              <Button className="w-full" variant="outline">
                <FileText className="h-4 w-4 mr-2" />
                Create Project
              </Button>
              <Button className="w-full" variant="outline">
                <Building2 className="h-4 w-4 mr-2" />
                Generate Invoice
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}