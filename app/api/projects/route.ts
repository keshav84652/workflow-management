import { NextRequest, NextResponse } from 'next/server'
import { PROJECTS_DATA } from '@/lib/data'

export async function GET(request: NextRequest) {
  try {
    // In a real app, this would be filtered by firm_id and user permissions
    return NextResponse.json({ 
      success: true, 
      data: PROJECTS_DATA 
    })
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Failed to fetch projects' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const projectData = await request.json()
    
    // In a real app, this would save to database
    const newProject = {
      id: Math.max(...PROJECTS_DATA.map(p => p.id)) + 1,
      ...projectData,
      firm_id: 1,
      task_dependency_mode: false,
      created_at: new Date().toISOString()
    }

    PROJECTS_DATA.push(newProject)

    return NextResponse.json({ 
      success: true, 
      data: newProject 
    })
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Failed to create project' },
      { status: 500 }
    )
  }
}