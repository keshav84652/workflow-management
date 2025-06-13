"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { usePathname } from "next/navigation"
import Header from "@/components/header"
import Footer from "@/components/footer"
import { cn } from "@/lib/utils"

export default function AnimatedLayout({ children }: { children: React.ReactNode }) {
  const [scrolled, setScrolled] = useState(false)
  const pathname = usePathname()

  // Handle scroll events for header animation
  useEffect(() => {
    const handleScroll = () => {
      const isScrolled = window.scrollY > 10
      if (isScrolled !== scrolled) {
        setScrolled(isScrolled)
      }
    }

    // Throttle scroll events for better performance
    let timeoutId: NodeJS.Timeout
    const throttledHandleScroll = () => {
      if (!timeoutId) {
        timeoutId = setTimeout(() => {
          handleScroll()
          timeoutId = null as unknown as NodeJS.Timeout
        }, 100)
      }
    }

    window.addEventListener("scroll", throttledHandleScroll)
    return () => window.removeEventListener("scroll", throttledHandleScroll)
  }, [scrolled])

  // Page transition effect
  const [isPageTransitioning, setIsPageTransitioning] = useState(false)
  const [currentPathname, setCurrentPathname] = useState(pathname)

  useEffect(() => {
    if (currentPathname !== pathname) {
      setIsPageTransitioning(true)
      const timer = setTimeout(() => {
        setCurrentPathname(pathname)
        setIsPageTransitioning(false)
      }, 300)
      return () => clearTimeout(timer)
    }
  }, [pathname, currentPathname])

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Header scrolled={scrolled} />
      <main
        className={cn(
          "flex-grow transition-opacity duration-300 ease-in-out",
          isPageTransitioning ? "opacity-0 translate-x-5" : "opacity-100 translate-x-0",
        )}
      >
        {children}
      </main>
      <Footer />
    </div>
  )
}
