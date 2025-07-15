"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"
import { TaskForm } from "@/components/forms/task-form"

export default function CreateTaskSimplePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (data: any) => {
    setLoading(true)
    try {
      // Mock API call
      console.log("Creating task:", data)
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      router.push("/dashboard/tasks")
    } catch (error) {
      console.error("Error creating task:", error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button 
          variant="outline" 
          size="icon"
          onClick={() => router.back()}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Create Task</h1>
          <p className="text-muted-foreground">Add a new task with proper validation</p>
        </div>
      </div>

      <TaskForm onSubmit={handleSubmit} loading={loading} />
    </div>
  )
}