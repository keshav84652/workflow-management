import { NextRequest, NextResponse } from 'next/server'
import { CLIENTS_DATA } from '@/lib/data'

export async function GET(request: NextRequest) {
  try {
    // In a real app, this would be filtered by firm_id and user permissions
    return NextResponse.json({ 
      success: true, 
      data: CLIENTS_DATA 
    })
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Failed to fetch clients' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const clientData = await request.json()
    
    // In a real app, this would save to database
    const newClient = {
      id: Math.max(...CLIENTS_DATA.map(c => c.id)) + 1,
      ...clientData,
      firm_id: 1,
      is_active: true,
      created_at: new Date().toISOString()
    }

    CLIENTS_DATA.push(newClient)

    return NextResponse.json({ 
      success: true, 
      data: newClient 
    })
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Failed to create client' },
      { status: 500 }
    )
  }
}