"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Search,
  Filter,
  Clock,
  FileText,
  Users,
  FolderOpen,
  CheckSquare,
  Calendar,
  Building2,
  MoreHorizontal,
  ExternalLink,
} from "lucide-react"

interface SearchResult {
  id: string
  type: "task" | "project" | "client" | "document" | "user"
  title: string
  description: string
  content?: string
  location: string
  date: string
  relevance: number
}

const mockSearchResults: SearchResult[] = [
  {
    id: "1",
    type: "task",
    title: "Complete Q4 Tax Review",
    description: "Review and finalize Q4 tax documentation for ABC Corp",
    content: "Need to review all Q4 transactions and ensure compliance...",
    location: "Tasks > ABC Corp Project",
    date: "2024-01-15",
    relevance: 95,
  },
  {
    id: "2",
    type: "project",
    title: "ABC Corp Annual Audit",
    description: "Complete annual audit for ABC Corporation",
    content: "This project involves comprehensive audit procedures...",
    location: "Projects > Active",
    date: "2024-01-10",
    relevance: 88,
  },
  {
    id: "3",
    type: "client",
    title: "ABC Corporation",
    description: "Large manufacturing client - annual revenue $2M",
    content: "Contact: John Smith, CFO. Primary services: audit, tax...",
    location: "Clients",
    date: "2023-12-01",
    relevance: 85,
  },
  {
    id: "4",
    type: "document",
    title: "Tax Compliance Checklist 2024",
    description: "Updated checklist for 2024 tax compliance procedures",
    content: "1. Gather all financial statements 2. Review deductions...",
    location: "Documents > Checklists",
    date: "2024-01-01",
    relevance: 78,
  },
  {
    id: "5",
    type: "user",
    title: "John Smith",
    description: "Senior Tax Manager - ABC Corp specialist",
    content: "Email: john.smith@firm.com, Phone: (555) 123-4567...",
    location: "Users",
    date: "2023-11-15",
    relevance: 72,
  },
]

export default function AdminSearchPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedType, setSelectedType] = useState<string>("all")
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    
    setIsSearching(true)
    // Simulate search delay
    setTimeout(() => {
      const filtered = mockSearchResults.filter(result =>
        result.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        result.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        result.content?.toLowerCase().includes(searchQuery.toLowerCase())
      )
      
      if (selectedType !== "all") {
        setSearchResults(filtered.filter(r => r.type === selectedType))
      } else {
        setSearchResults(filtered)
      }
      setIsSearching(false)
    }, 1000)
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "task":
        return <CheckSquare className="h-4 w-4" />
      case "project":
        return <FolderOpen className="h-4 w-4" />
      case "client":
        return <Building2 className="h-4 w-4" />
      case "document":
        return <FileText className="h-4 w-4" />
      case "user":
        return <Users className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case "task":
        return "bg-blue-100 text-blue-800"
      case "project":
        return "bg-green-100 text-green-800"
      case "client":
        return "bg-purple-100 text-purple-800"
      case "document":
        return "bg-orange-100 text-orange-800"
      case "user":
        return "bg-pink-100 text-pink-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getRelevanceColor = (relevance: number) => {
    if (relevance >= 90) return "text-green-600"
    if (relevance >= 70) return "text-yellow-600"
    return "text-red-600"
  }

  const searchStats = {
    total: searchResults.length,
    tasks: searchResults.filter(r => r.type === "task").length,
    projects: searchResults.filter(r => r.type === "project").length,
    clients: searchResults.filter(r => r.type === "client").length,
    documents: searchResults.filter(r => r.type === "document").length,
    users: searchResults.filter(r => r.type === "user").length,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Global Search</h1>
          <p className="text-gray-600 mt-1">Search across all firm data and content</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Filter className="h-4 w-4 mr-2" />
            Advanced Search
          </Button>
        </div>
      </div>

      {/* Search Interface */}
      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                  <Input
                    placeholder="Search tasks, projects, clients, documents, users..."
                    className="pl-10 text-lg h-12"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                  />
                </div>
              </div>
              <Button size="lg" onClick={handleSearch} disabled={isSearching}>
                {isSearching ? "Searching..." : "Search"}
              </Button>
            </div>
            
            <div className="flex gap-2">
              <Button
                variant={selectedType === "all" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedType("all")}
              >
                All
              </Button>
              <Button
                variant={selectedType === "task" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedType("task")}
              >
                <CheckSquare className="h-3 w-3 mr-1" />
                Tasks
              </Button>
              <Button
                variant={selectedType === "project" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedType("project")}
              >
                <FolderOpen className="h-3 w-3 mr-1" />
                Projects
              </Button>
              <Button
                variant={selectedType === "client" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedType("client")}
              >
                <Building2 className="h-3 w-3 mr-1" />
                Clients
              </Button>
              <Button
                variant={selectedType === "document" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedType("document")}
              >
                <FileText className="h-3 w-3 mr-1" />
                Documents
              </Button>
              <Button
                variant={selectedType === "user" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedType("user")}
              >
                <Users className="h-3 w-3 mr-1" />
                Users
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <>
          {/* Results Stats */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-blue-600">{searchStats.total}</p>
                <p className="text-sm text-gray-600">Total Results</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-green-600">{searchStats.tasks}</p>
                <p className="text-sm text-gray-600">Tasks</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-purple-600">{searchStats.projects}</p>
                <p className="text-sm text-gray-600">Projects</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-orange-600">{searchStats.clients}</p>
                <p className="text-sm text-gray-600">Clients</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-red-600">{searchStats.documents}</p>
                <p className="text-sm text-gray-600">Documents</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-pink-600">{searchStats.users}</p>
                <p className="text-sm text-gray-600">Users</p>
              </CardContent>
            </Card>
          </div>

          {/* Results List */}
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle>Search Results</CardTitle>
                  <CardDescription>
                    Found {searchResults.length} results for "{searchQuery}"
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm">
                  Sort by Relevance
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {searchResults.map((result) => (
                  <div key={result.id} className="border rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <Badge className={getTypeColor(result.type)}>
                            <span className="flex items-center gap-1">
                              {getTypeIcon(result.type)}
                              {result.type}
                            </span>
                          </Badge>
                          <span className={`text-sm font-medium ${getRelevanceColor(result.relevance)}`}>
                            {result.relevance}% match
                          </span>
                        </div>
                        <h3 className="font-semibold text-lg text-blue-600 hover:underline cursor-pointer">
                          {result.title}
                        </h3>
                        <p className="text-gray-600 mt-1">{result.description}</p>
                        {result.content && (
                          <p className="text-sm text-gray-500 mt-2 line-clamp-2">
                            {result.content}
                          </p>
                        )}
                        <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                          <span className="flex items-center gap-1">
                            <FolderOpen className="h-3 w-3" />
                            {result.location}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {result.date}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button size="sm" variant="outline">
                          <ExternalLink className="h-3 w-3 mr-1" />
                          Open
                        </Button>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Search Tips */}
      {searchResults.length === 0 && searchQuery && !isSearching && (
        <Card>
          <CardHeader>
            <CardTitle>No Results Found</CardTitle>
            <CardDescription>Try adjusting your search terms or filters</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm text-gray-600">
              <p>• Try different keywords or phrases</p>
              <p>• Check for typos in your search</p>
              <p>• Use broader search terms</p>
              <p>• Remove filters to see more results</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Search Suggestions */}
      {!searchQuery && (
        <Card>
          <CardHeader>
            <CardTitle>Popular Searches</CardTitle>
            <CardDescription>Common search queries</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {["tax returns", "ABC Corp", "quarterly reports", "audit checklist", "client contacts"].map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearchQuery(suggestion)
                    handleSearch()
                  }}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}