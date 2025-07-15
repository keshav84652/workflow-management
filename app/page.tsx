import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { CheckCircle, Users, Calendar, FileText, BarChart3, Shield } from 'lucide-react'

export default function LandingPage() {
  const features = [
    {
      icon: <CheckCircle className="h-6 w-6" />,
      title: "Template-Driven Workflows",
      description: "Sophisticated workflow automation with conditional logic"
    },
    {
      icon: <Users className="h-6 w-6" />,
      title: "Role-Based Permissions",
      description: "Admin and Member roles with granular access control"
    },
    {
      icon: <Calendar className="h-6 w-6" />,
      title: "Advanced Project Management",
      description: "Sequential task dependencies and project health tracking"
    },
    {
      icon: <FileText className="h-6 w-6" />,
      title: "Document Management",
      description: "File uploads with checklist-based organization"
    },
    {
      icon: <BarChart3 className="h-6 w-6" />,
      title: "Real-Time Analytics",
      description: "Advanced dashboard with live statistics and progress tracking"
    },
    {
      icon: <Shield className="h-6 w-6" />,
      title: "Client Portal Integration",
      description: "Document checklists with public access and sharing"
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-black/20 backdrop-blur-md border-b border-white/10">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-green-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">CW</span>
            </div>
            <span className="text-white text-xl font-bold">CPA WorkflowPilot</span>
          </div>
          <nav className="hidden md:flex space-x-8">
            <Link href="#features" className="text-white/70 hover:text-white transition-colors">
              Features
            </Link>
            <Link href="#about" className="text-white/70 hover:text-white transition-colors">
              About
            </Link>
          </nav>
          <div className="flex space-x-4">
            <Button variant="ghost" className="text-white hover:bg-white/10">
              <Link href="/login">Login</Link>
            </Button>
            <Button className="bg-blue-600 hover:bg-blue-700">
              <Link href="/dashboard">Get Started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="container mx-auto text-center">
          <h1 className="text-5xl md:text-7xl font-bold text-white mb-6">
            Professional
            <span className="bg-gradient-to-r from-blue-400 to-green-400 bg-clip-text text-transparent">
              {" "}Workflow Management
            </span>
          </h1>
          <p className="text-xl text-white/80 mb-8 max-w-3xl mx-auto">
            A comprehensive workflow management application designed specifically for CPA firms, 
            built with enterprise-grade architecture patterns.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-lg px-8 py-3">
              <Link href="/dashboard">Start Your Workflow</Link>
            </Button>
            <Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/10 text-lg px-8 py-3">
              <Link href="#features">Learn More</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4">
        <div className="container mx-auto">
          <h2 className="text-4xl font-bold text-white text-center mb-16">
            Complete Feature Set
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <Card key={index} className="bg-white/10 backdrop-blur-md border-white/20 text-white">
                <CardHeader>
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-blue-600/20 rounded-lg">
                      {feature.icon}
                    </div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-white/70">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto text-center">
          <Card className="bg-white/10 backdrop-blur-md border-white/20 max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle className="text-3xl text-white mb-4">
                Ready to Transform Your Workflow?
              </CardTitle>
              <CardDescription className="text-white/70 text-lg">
                Join CPA firms already using WorkflowPilot to streamline their operations
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <Button size="lg" className="bg-green-600 hover:bg-green-700 text-lg px-8 py-3">
                <Link href="/dashboard">Get Started Today</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t border-white/10">
        <div className="container mx-auto text-center text-white/60">
          <p>&copy; 2024 CPA WorkflowPilot. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}