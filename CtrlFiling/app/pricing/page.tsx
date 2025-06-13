"use client"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth-context"
import { useEffect, useRef } from "react"
import { PricingCard } from "@/components/pricing-card"
import { CTASection } from "@/components/cta-section"

const individualFeatures = [
  "1 user",
  "Unlimited calendars",
  "Unlimited event types",
  "Workflows",
  "Integrate with your favorite apps",
  "Accept payments via Stripe",
]

const teamFeatures = [
  "1 team",
  "Schedule meetings as a team",
  "Round-Robin, Fixed Round-Robin",
  "Collective Events",
  "Advanced Routing Forms",
  "Team Workflows",
]

const enterpriseFeatures = [
  "1 parent team and unlimited sub-teams",
  "Organization workflows",
  "Insights - analyze your booking data",
  "Active directory sync",
  "24/7 Email, Chat and Phone support",
  "Sync your HRIS tools",
]

export default function PricingPage() {
  const { user } = useAuth()
  const teamsCardRef = useRef<HTMLDivElement>(null)
  const badgeRef = useRef<HTMLDivElement>(null)

  // Animate the Teams card and badge on load
  useEffect(() => {
    if (teamsCardRef.current) {
      // Add a slight bounce animation to the Teams card
      const card = teamsCardRef.current
      setTimeout(() => {
        card.style.transform = "translateY(-8px)"
        setTimeout(() => {
          card.style.transform = "translateY(0)"
        }, 300)
      }, 500)
    }

    if (badgeRef.current) {
      // Slide in the badge from the top
      const badge = badgeRef.current
      badge.style.opacity = "0"
      badge.style.transform = "translateY(-20px)"
      setTimeout(() => {
        badge.style.opacity = "1"
        badge.style.transform = "translateY(0)"
      }, 800)
    }
  }, [])

  return (
    <>
      {/* Login Prompt for Non-Logged In Users */}
      {!user && (
        <div className="bg-blue-50 border-b border-blue-100">
          <div className="container mx-auto px-4 py-4">
            <div className="flex flex-col sm:flex-row items-center justify-between">
              <p className="text-blue-800 mb-3 sm:mb-0">Already have an account? Log in to manage your subscription.</p>
              <Link href="/login?redirect=pricing">
                <Button variant="outline" className="border-blue-600 text-blue-600 hover:bg-blue-100">
                  Log In
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}

      <div className="container mx-auto px-4 py-16">
        <div className="text-center max-w-3xl mx-auto mb-16 animate-in fade-in-50 slide-in-from-bottom-5 duration-700">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">Simple pricing based on your needs</h1>
          <p className="text-xl text-gray-600">
            Discover a variety of our advanced features. Unlimited and free for individuals.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Individuals Plan */}
          <PricingCard
            title="Individuals"
            price="$0"
            description="Good for individuals who are just starting out and simply want the essentials."
            features={individualFeatures}
            buttonText="Get started"
            buttonVariant="outline"
            className="bg-gradient-to-br from-rose-50 to-rose-100"
            delay={0}
          />

          {/* Teams Plan */}
          <PricingCard
            title="Teams"
            price="$12"
            description="Highly recommended for small teams who seek to upgrade their time & perform."
            features={teamFeatures}
            buttonText="Get started"
            highlighted={true}
            badge="30 days free trial"
            className="bg-gradient-to-br from-blue-50 to-blue-100"
            delay={1}
            cardRef={teamsCardRef}
            badgeRef={badgeRef}
          />

          {/* Enterprise Plan */}
          <PricingCard
            title="Enterprise"
            price="$15k"
            description="Robust scheduling for larger teams looking to have more control, privacy & security."
            features={enterpriseFeatures}
            buttonText="Contact us"
            buttonVariant="outline"
            className="bg-gradient-to-br from-teal-50 to-teal-100"
            delay={2}
          />
        </div>

        <div className="mt-16 text-center animate-in fade-in-50 slide-in-from-bottom-5 duration-700 delay-300">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Need a custom solution?</h2>
          <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
            Contact our sales team to discuss your specific requirements and get a tailored quote.
          </p>
          <Button className="bg-blue-600 hover:bg-blue-700">Contact Sales</Button>
        </div>
      </div>

      {/* CTA Section */}
      <CTASection
        title="Ready to streamline your tax preparation?"
        description="Join thousands of tax professionals who are saving time and reducing errors with our AI-powered platform."
      />
    </>
  )
}
