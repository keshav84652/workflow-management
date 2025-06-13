"use client"

import Image from "next/image"
import { Button } from "@/components/ui/button"
import { CheckIcon, Shield, XCircle, Sun } from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { TestimonialsSection } from "@/components/testimonials-section"
import { CTASection } from "@/components/cta-section"
import { FeatureCard } from "@/components/feature-card"

export default function AboutPage() {
  const { user } = useAuth()

  return (
    <>
      {/* User Plan Details Section (only shown if logged in) */}
      {user && user.plan && (
        <div className="bg-blue-600 text-white">
          <div className="container mx-auto px-4 py-12">
            <div className="max-w-4xl mx-auto">
              <h1 className="text-3xl font-bold mb-2">Your Plan: {user.plan.name}</h1>
              <p className="text-blue-100 mb-6">{user.plan.price}</p>

              <div className="bg-white text-gray-900 rounded-xl p-6 shadow-lg">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6 pb-6 border-b">
                  <div>
                    <h2 className="text-xl font-bold mb-1">Billing Details</h2>
                    <p className="text-gray-600">
                      Next billing on {user.plan.nextBillingDate} • {user.plan.billingCycle}
                    </p>
                  </div>
                  <div className="mt-4 md:mt-0">
                    <Button variant="outline">Manage Billing</Button>
                  </div>
                </div>

                <h3 className="font-medium text-lg mb-4">Your Plan Includes:</h3>
                <ul className="grid md:grid-cols-2 gap-3 mb-6">
                  {user.plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start">
                      <CheckIcon className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                <div className="flex flex-col sm:flex-row gap-4">
                  <Button className="bg-blue-600 hover:bg-blue-700">Upgrade Plan</Button>
                  <Button variant="outline">Download Invoice</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* How It Started Section */}
      <div className="bg-white py-16">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-2 gap-12 items-center max-w-6xl mx-auto">
            <div className="animate-in fade-in-50 slide-in-from-left-5 duration-700">
              <div className="text-blue-600 font-medium mb-2">How It Started</div>
              <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
                Our Dream is Global Tax Transformation
              </h2>
              <p className="text-gray-600 mb-6">
                Ctrl+Filing was founded by Robert Anderson, a passionate tax professional, and Maria Sanchez, a
                visionary AI engineer. Their shared dream was to create a digital haven of tax preparation accessible to
                all. United by their belief in the transformational power of AI in tax preparation, they embarked on a
                journey to build 'Ctrl+Filing.' With relentless dedication, they gathered a team of experts and launched
                this innovative platform, creating a global community of eager tax professionals, all connected by the
                desire to explore, learn, and grow.
              </p>
            </div>
            <div className="animate-in fade-in-50 slide-in-from-right-5 duration-700">
              <Image
                src="/about-team.png"
                alt="Ctrl+Filing Team"
                width={600}
                height={400}
                className="rounded-xl shadow-lg"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="bg-gray-50 py-12">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
            <div className="text-center animate-in fade-in-50 duration-700">
              <div className="text-4xl md:text-5xl font-bold text-blue-600 mb-2">3.5</div>
              <div className="text-gray-600">Years Experience</div>
            </div>
            <div className="text-center animate-in fade-in-50 duration-700 delay-100">
              <div className="text-4xl md:text-5xl font-bold text-blue-600 mb-2">23</div>
              <div className="text-gray-600">Project Challenge</div>
            </div>
            <div className="text-center animate-in fade-in-50 duration-700 delay-200">
              <div className="text-4xl md:text-5xl font-bold text-blue-600 mb-2">830+</div>
              <div className="text-gray-600">Positive Reviews</div>
            </div>
            <div className="text-center animate-in fade-in-50 duration-700 delay-300">
              <div className="text-4xl md:text-5xl font-bold text-blue-600 mb-2">100K</div>
              <div className="text-gray-600">Trusted Clients</div>
            </div>
          </div>
        </div>
      </div>

      {/* About Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">About Ctrl+Filing</h2>
          <p className="text-lg text-gray-600 mb-8">
            Ctrl+Filing is revolutionizing tax preparation with AI-powered tools designed specifically for tax
            professionals. Our mission is to eliminate the tedious, error-prone aspects of tax preparation, allowing you
            to focus on providing value to your clients.
          </p>

          <div className="grid md:grid-cols-3 gap-6 mb-12">
            <FeatureCard
              icon={<Shield className="text-blue-600" />}
              title="Secure"
              description="Bank-level encryption and compliance with all relevant tax regulations and security standards."
            />
            <FeatureCard
              icon={<XCircle className="text-blue-600" />}
              title="Error-Free"
              description="Our AI validation reduces errors by up to 95% compared to manual data entry and review."
            />
            <FeatureCard
              icon={<Sun className="text-blue-600" />}
              title="Time-Saving"
              description="Reduce tax preparation time by up to 80% with our automated document processing and data extraction."
            />
          </div>
        </div>
      </div>

      {/* Testimonials Section */}
      <TestimonialsSection />

      {/* CTA Section */}
      <CTASection />
    </>
  )
}
