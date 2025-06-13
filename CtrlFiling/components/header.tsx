"use client"

import { useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth-context"
import { cn } from "@/lib/utils"
import { linkAnimationClasses, headerAnimationClasses } from "@/lib/animation-utils"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Menu, User } from "lucide-react"

type HeaderProps = {
  scrolled?: boolean
}

export default function Header({ scrolled = false }: HeaderProps) {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header
      className={cn(
        "sticky top-0 z-50 w-full bg-white shadow-sm",
        headerAnimationClasses.base,
        scrolled ? headerAnimationClasses.scrolled : headerAnimationClasses.default,
      )}
    >
      <div className="container mx-auto px-4 h-full flex items-center justify-between">
        <Link href="/" className="flex items-center">
          <Image
            src="/logo.png"
            alt="Ctrl+Filing Logo"
            width={scrolled ? 130 : 150}
            height={scrolled ? 35 : 40}
            className="transition-all duration-200 ease-in-out"
            priority
          />
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-6">
          <Link
            href="/pricing"
            className={cn(
              linkAnimationClasses.base,
              linkAnimationClasses.underline,
              "font-medium",
              pathname === "/pricing" ? "text-blue-600" : "text-gray-600 hover:text-blue-600",
            )}
          >
            Pricing
          </Link>
          <Link
            href="/about"
            className={cn(
              linkAnimationClasses.base,
              linkAnimationClasses.underline,
              "font-medium",
              pathname === "/about" ? "text-blue-600" : "text-gray-600 hover:text-blue-600",
            )}
          >
            About
          </Link>

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="rounded-full h-10 w-10 p-0">
                  <User className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="animate-in fade-in-80 zoom-in-95 duration-200">
                <DropdownMenuLabel>My Account</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/about">Plan Details</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/files">My Files</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/settings">Settings</Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout}>Logout</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <>
              <Link
                href="/login"
                className={cn(
                  linkAnimationClasses.base,
                  linkAnimationClasses.underline,
                  "font-medium",
                  pathname === "/login" ? "text-blue-600" : "text-gray-600 hover:text-blue-600",
                )}
              >
                Login
              </Link>
              <Button className="bg-blue-600 hover:bg-blue-700 text-white rounded-full px-6">Request Demo</Button>
            </>
          )}
        </nav>

        {/* Mobile Navigation */}
        <Sheet open={isMenuOpen} onOpenChange={setIsMenuOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="h-6 w-6" />
              <span className="sr-only">Toggle menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="animate-in slide-in-from-right duration-300">
            <div className="flex flex-col space-y-4 mt-8">
              <Link href="/pricing" className="text-lg font-medium py-2" onClick={() => setIsMenuOpen(false)}>
                Pricing
              </Link>
              <Link href="/about" className="text-lg font-medium py-2" onClick={() => setIsMenuOpen(false)}>
                About
              </Link>
              {user ? (
                <>
                  <Link href="/about" className="text-lg font-medium py-2" onClick={() => setIsMenuOpen(false)}>
                    Plan Details
                  </Link>
                  <Link href="/files" className="text-lg font-medium py-2" onClick={() => setIsMenuOpen(false)}>
                    My Files
                  </Link>
                  <Link href="/settings" className="text-lg font-medium py-2" onClick={() => setIsMenuOpen(false)}>
                    Settings
                  </Link>
                  <Button
                    variant="ghost"
                    className="justify-start px-0 hover:bg-transparent hover:text-blue-600"
                    onClick={() => {
                      logout()
                      setIsMenuOpen(false)
                    }}
                  >
                    Logout
                  </Button>
                </>
              ) : (
                <>
                  <Link href="/login" className="text-lg font-medium py-2" onClick={() => setIsMenuOpen(false)}>
                    Login
                  </Link>
                  <Button className="bg-blue-600 hover:bg-blue-700 mt-2" onClick={() => setIsMenuOpen(false)}>
                    Request Demo
                  </Button>
                </>
              )}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  )
}
