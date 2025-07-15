import { NextRequest, NextResponse } from 'next/server'
import { TASKS_DATA } from '@/lib/data'

export async function GET(request: NextRequest) {
  try {
    // In a real app, this would be filtered by firm_id and user permissions
    return NextResponse.json({ 
      success: true, 
      data: TASKS_DATA 
    })
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Failed to fetch tasks' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const taskData = await request.json()
    
    // In a real app, this would save to database
    const newTask = {
      id: Math.max(...TASKS_DATA.map(t => t.id)) + 1,
      ...taskData,
      firm_id: 1,
      is_recurring: false,
      is_billable: true,
      timer_running: false,
      actual_hours: 0,
      created_at: new Date().toISOString()
    }

    TASKS_DATA.push(newTask)

    return NextResponse.json({ 
      success: true, 
      data: newTask 
    })
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Failed to create task' },
      { status: 500 }
    )
  }
}