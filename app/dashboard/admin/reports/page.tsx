"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  BarChart3,
  TrendingUp,
  Download,
  Calendar,
  Filter,
  FileText,
  Users,
  DollarSign,
  Clock,
  CheckCircle,
  AlertCircle,
  PieChart,
  Activity,
  Target,
} from "lucide-react"

interface ReportTemplate {
  id: string
  name: string
  description: string
  category: string
  type: "chart" | "table" | "summary"
  lastGenerated: string
  frequency: string
}

const reportTemplates: ReportTemplate[] = [
  {
    id: "1",
    name: "Task Completion Report",
    description: "Track task completion rates by user and project",
    category: "Productivity",
    type: "chart",
    lastGenerated: "2024-01-15",
    frequency: "Weekly",
  },
  {
    id: "2",
    name: "Revenue by Client",
    description: "Revenue breakdown by client and service type",
    category: "Financial",
    type: "chart",
    lastGenerated: "2024-01-14",
    frequency: "Monthly",
  },
  {
    id: "3",
    name: "Project Status Dashboard",
    description: "Overview of all active projects and their status",
    category: "Projects",
    type: "summary",
    lastGenerated: "2024-01-15",
    frequency: "Daily",
  },
  {
    id: "4",
    name: "Time Tracking Summary",
    description: "Time spent analysis by user, project, and work type",
    category: "Time Management",
    type: "table",
    lastGenerated: "2024-01-13",
    frequency: "Weekly",
  },
  {
    id: "5",
    name: "Client Activity Report",
    description: "Client engagement and communication tracking",
    category: "Client Relations",
    type: "chart",
    lastGenerated: "2024-01-12",
    frequency: "Monthly",
  },
]

const mockChartData = {
  taskCompletion: [
    { name: "Jan", completed: 85, pending: 15 },
    { name: "Feb", completed: 92, pending: 8 },
    { name: "Mar", completed: 78, pending: 22 },
    { name: "Apr", completed: 88, pending: 12 },
  ],
  revenueByService: [
    { service: "Tax Prep", revenue: 45000, percentage: 35 },
    { service: "Audit", revenue: 38000, percentage: 30 },
    { service: "Bookkeeping", revenue: 28000, percentage: 22 },
    { service: "Consulting", revenue: 16000, percentage: 13 },
  ]
}

export default function AdminReportsPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>("all")
  const [selectedPeriod, setSelectedPeriod] = useState<string>("month")

  const categories = Array.from(new Set(reportTemplates.map(r => r.category)))

  const filteredReports = reportTemplates.filter(report =>
    selectedCategory === "all" || report.category === selectedCategory
  )

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "chart":
        return <BarChart3 className="h-4 w-4" />
      case "table":
        return <FileText className="h-4 w-4" />
      case "summary":
        return <Activity className="h-4 w-4" />
      default:
        return <BarChart3 className="h-4 w-4" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case "chart":
        return "bg-blue-100 text-blue-800"
      case "table":
        return "bg-green-100 text-green-800"
      case "summary":
        return "bg-purple-100 text-purple-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getCategoryColor = (category: string) => {
    const colors = {
      "Productivity": "bg-green-100 text-green-800",
      "Financial": "bg-yellow-100 text-yellow-800",
      "Projects": "bg-blue-100 text-blue-800",
      "Time Management": "bg-purple-100 text-purple-800",
      "Client Relations": "bg-pink-100 text-pink-800",
    }
    return colors[category as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Reports & Analytics</h1>
          <p className="text-gray-600 mt-1">Generate insights and track firm performance</p>
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <Calendar className="h-4 w-4 mr-2" />
                Period: {selectedPeriod}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setSelectedPeriod("week")}>
                This Week
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setSelectedPeriod("month")}>
                This Month
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setSelectedPeriod("quarter")}>
                This Quarter
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setSelectedPeriod("year")}>
                This Year
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button>
            <Download className="h-4 w-4 mr-2" />
            Export All
          </Button>
        </div>
      </div>

      {/* Key Metrics Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Revenue</p>
                <p className="text-2xl font-bold text-green-600">$127,000</p>
                <p className="text-xs text-green-600 flex items-center gap-1 mt-1">
                  <TrendingUp className="h-3 w-3" />
                  +12% from last month
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Completed Tasks</p>
                <p className="text-2xl font-bold text-blue-600">847</p>
                <p className="text-xs text-blue-600 flex items-center gap-1 mt-1">
                  <TrendingUp className="h-3 w-3" />
                  +8% from last month
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Billable Hours</p>
                <p className="text-2xl font-bold text-purple-600">1,250</p>
                <p className="text-xs text-purple-600 flex items-center gap-1 mt-1">
                  <TrendingUp className="h-3 w-3" />
                  +15% from last month
                </p>
              </div>
              <Clock className="h-8 w-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Clients</p>
                <p className="text-2xl font-bold text-orange-600">42</p>
                <p className="text-xs text-orange-600 flex items-center gap-1 mt-1">
                  <TrendingUp className="h-3 w-3" />
                  +3 new this month
                </p>
              </div>
              <Users className="h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts and Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Task Completion Trends</CardTitle>
            <CardDescription>Monthly task completion rates</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg">
              <div className="text-center">
                <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-500">Task Completion Chart</p>
                <p className="text-sm text-gray-400">Interactive chart would be rendered here</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Revenue by Service Type</CardTitle>
            <CardDescription>Revenue breakdown by service category</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockChartData.revenueByService.map((item, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded bg-blue-500" style={{ 
                      backgroundColor: `hsl(${index * 60}, 70%, 50%)` 
                    }} />
                    <span className="font-medium">{item.service}</span>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">${item.revenue.toLocaleString()}</p>
                    <p className="text-sm text-gray-600">{item.percentage}%</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Report Templates */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Available Reports</CardTitle>
              <CardDescription>Pre-configured report templates</CardDescription>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <Filter className="h-4 w-4 mr-2" />
                  Category: {selectedCategory === "all" ? "All" : selectedCategory}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => setSelectedCategory("all")}>
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
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredReports.map((report) => (
              <Card key={report.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg">{report.name}</CardTitle>
                      <CardDescription className="mt-1">
                        {report.description}
                      </CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge className={getTypeColor(report.type)}>
                      <span className="flex items-center gap-1">
                        {getTypeIcon(report.type)}
                        {report.type}
                      </span>
                    </Badge>
                    <Badge className={getCategoryColor(report.category)} variant="secondary">
                      {report.category}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="text-sm text-gray-600">
                      <p>Last generated: {report.lastGenerated}</p>
                      <p>Frequency: {report.frequency}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button className="flex-1" size="sm">
                        Generate Report
                      </Button>
                      <Button variant="outline" size="sm">
                        <Download className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Reports */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Reports</CardTitle>
          <CardDescription>Recently generated reports and exports</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { name: "Monthly Revenue Report", type: "PDF", size: "2.3 MB", date: "2024-01-15 10:30 AM" },
              { name: "Task Completion Analysis", type: "Excel", size: "1.8 MB", date: "2024-01-14 03:15 PM" },
              { name: "Client Activity Summary", type: "PDF", size: "945 KB", date: "2024-01-13 11:45 AM" },
            ].map((file, index) => (
              <div key={index} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-gray-600" />
                  <div>
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-gray-600">{file.type} • {file.size}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">{file.date}</span>
                  <Button size="sm" variant="outline">
                    <Download className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}