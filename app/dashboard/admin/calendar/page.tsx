"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Calendar as CalendarComponent } from "@/components/ui/calendar"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Calendar,
  Clock,
  Plus,
  Settings,
  Bell,
  Users,
  MapPin,
  Edit,
  Trash2,
  MoreHorizontal,
} from "lucide-react"

export default function AdminCalendarPage() {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date())
  const [isEventDialogOpen, setIsEventDialogOpen] = useState(false)

  const events = [
    {
      id: 1,
      title: "Tax Season Kickoff Meeting",
      date: "2024-01-15",
      time: "09:00 AM",
      type: "meeting",
      attendees: 12,
      location: "Conference Room A",
    },
    {
      id: 2,
      title: "Client Review Deadline",
      date: "2024-01-20",
      time: "All Day",
      type: "deadline",
      attendees: 0,
      location: "",
    },
    {
      id: 3,
      title: "Quarterly Planning Session",
      date: "2024-01-25",
      time: "02:00 PM",
      type: "planning",
      attendees: 8,
      location: "Virtual",
    },
  ]

  const holidays = [
    { name: "New Year's Day", date: "2024-01-01" },
    { name: "Martin Luther King Jr. Day", date: "2024-01-15" },
    { name: "Presidents Day", date: "2024-02-19" },
    { name: "Memorial Day", date: "2024-05-27" },
  ]

  const getEventTypeColor = (type: string) => {
    switch (type) {
      case "meeting":
        return "bg-blue-100 text-blue-800"
      case "deadline":
        return "bg-red-100 text-red-800"
      case "planning":
        return "bg-purple-100 text-purple-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Calendar Management</h1>
          <p className="text-gray-600 mt-1">Manage firm calendar, events, and holidays</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
          <Dialog open={isEventDialogOpen} onOpenChange={setIsEventDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Event
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Event</DialogTitle>
                <DialogDescription>
                  Add a new event to the firm calendar.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Event Title</label>
                  <input className="w-full p-2 border rounded-md" placeholder="Enter event title" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium">Date</label>
                    <input type="date" className="w-full p-2 border rounded-md" />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Time</label>
                    <input type="time" className="w-full p-2 border rounded-md" />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium">Type</label>
                  <select className="w-full p-2 border rounded-md">
                    <option value="meeting">Meeting</option>
                    <option value="deadline">Deadline</option>
                    <option value="planning">Planning</option>
                    <option value="holiday">Holiday</option>
                  </select>
                </div>
                <Button className="w-full">Create Event</Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Calendar and Events Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Firm Calendar</CardTitle>
            <CardDescription>View and manage firm-wide events and deadlines</CardDescription>
          </CardHeader>
          <CardContent>
            <CalendarComponent
              mode="single"
              selected={selectedDate}
              onSelect={setSelectedDate}
              className="rounded-md border w-full"
            />
          </CardContent>
        </Card>

        {/* Upcoming Events */}
        <Card>
          <CardHeader>
            <CardTitle>Upcoming Events</CardTitle>
            <CardDescription>Next scheduled events and deadlines</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {events.map((event) => (
              <div key={event.id} className="p-3 border rounded-lg hover:bg-gray-50">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h4 className="font-medium">{event.title}</h4>
                    <div className="text-sm text-gray-600 mt-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <Calendar className="h-3 w-3" />
                        {event.date}
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="h-3 w-3" />
                        {event.time}
                      </div>
                      {event.location && (
                        <div className="flex items-center gap-2">
                          <MapPin className="h-3 w-3" />
                          {event.location}
                        </div>
                      )}
                      {event.attendees > 0 && (
                        <div className="flex items-center gap-2">
                          <Users className="h-3 w-3" />
                          {event.attendees} attendees
                        </div>
                      )}
                    </div>
                    <Badge className={getEventTypeColor(event.type)} variant="secondary">
                      {event.type}
                    </Badge>
                  </div>
                  <Button variant="ghost" size="icon">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Calendar Management Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Holidays */}
        <Card>
          <CardHeader>
            <CardTitle>Federal Holidays</CardTitle>
            <CardDescription>Manage firm holiday calendar</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {holidays.map((holiday, index) => (
                <div key={index} className="flex justify-between items-center p-3 border rounded-lg">
                  <div>
                    <p className="font-medium">{holiday.name}</p>
                    <p className="text-sm text-gray-600">{holiday.date}</p>
                  </div>
                  <Button variant="ghost" size="icon">
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
            <Button variant="outline" className="w-full mt-4">
              <Plus className="h-4 w-4 mr-2" />
              Add Holiday
            </Button>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <CardTitle>Event Notifications</CardTitle>
            <CardDescription>Configure calendar notifications</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-medium">Email Reminders</p>
                  <p className="text-sm text-gray-600">Send email notifications for events</p>
                </div>
                <input type="checkbox" className="rounded" defaultChecked />
              </div>
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-medium">Holiday Notifications</p>
                  <p className="text-sm text-gray-600">Notify about upcoming holidays</p>
                </div>
                <input type="checkbox" className="rounded" defaultChecked />
              </div>
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-medium">Deadline Alerts</p>
                  <p className="text-sm text-gray-600">Alert for approaching deadlines</p>
                </div>
                <input type="checkbox" className="rounded" defaultChecked />
              </div>
              <Button className="w-full">
                <Bell className="h-4 w-4 mr-2" />
                Update Notifications
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}