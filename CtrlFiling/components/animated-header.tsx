"use client"

import { useState, useEffect } from "react"
import Header from "@/components/header"

export default function AnimatedHeader() {
  const [scrolled, setScrolled] = useState(false)

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

  return <Header scrolled={scrolled} />
}
