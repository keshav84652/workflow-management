import { NextRequest, NextResponse } from 'next/server'
import { USERS_DATA } from '@/lib/data'

export async function GET(request: NextRequest) {
  try {
    // In a real app, this would be filtered by firm_id and user permissions
    return NextResponse.json({ 
      success: true, 
      data: USERS_DATA 
    })
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Failed to fetch users' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const userData = await request.json()
    
    // In a real app, this would save to database
    const newUser = {
      id: Math.max(...USERS_DATA.map(u => u.id)) + 1,
      ...userData,
      firm_id: 1,
      created_at: new Date().toISOString()
    }

    USERS_DATA.push(newUser)

    return NextResponse.json({ 
      success: true, 
      data: newUser 
    })
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Failed to create user' },
      { status: 500 }
    )
  }
}