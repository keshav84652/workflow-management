"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"

type User = {
  id: string
  name: string
  email: string
  plan?: {
    name: string
    price: string
    features: string[]
    billingCycle: string
    nextBillingDate?: string
  }
}

type AuthContextType = {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  loginWithGoogle: () => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if user is logged in from localStorage
    const storedUser = localStorage.getItem("user")
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser))
      } catch (error) {
        console.error("Failed to parse user from localStorage", error)
      }
    }
    setLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    setLoading(true)
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000))

      // Mock user data
      const userData: User = {
        id: "user_123",
        name: "John Doe",
        email: email,
        plan: {
          name: "Teams",
          price: "$12/month per user",
          features: [
            "1 team",
            "Schedule meetings as a team",
            "Round-Robin, Fixed Round-Robin",
            "Collective Events",
            "Advanced Routing Forms",
            "Team Workflows",
          ],
          billingCycle: "Monthly",
          nextBillingDate: "June 20, 2025",
        },
      }

      setUser(userData)
      localStorage.setItem("user", JSON.stringify(userData))
    } catch (error) {
      console.error("Login failed", error)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const loginWithGoogle = async () => {
    setLoading(true)
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1500))

      // Mock user data
      const userData: User = {
        id: "user_456",
        name: "Jane Smith",
        email: "jane.smith@example.com",
        plan: {
          name: "Teams",
          price: "$12/month per user",
          features: [
            "1 team",
            "Schedule meetings as a team",
            "Round-Robin, Fixed Round-Robin",
            "Collective Events",
            "Advanced Routing Forms",
            "Team Workflows",
          ],
          billingCycle: "Monthly",
          nextBillingDate: "June 15, 2025",
        },
      }

      setUser(userData)
      localStorage.setItem("user", JSON.stringify(userData))
    } catch (error) {
      console.error("Google login failed", error)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem("user")
  }

  return (
    <AuthContext.Provider value={{ user, login, loginWithGoogle, logout, loading }}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
