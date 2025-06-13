import { Button } from "@/components/ui/button"

type CTASectionProps = {
  title?: string
  description?: string
  primaryButtonText?: string
  secondaryButtonText?: string
}

export function CTASection({
  title = "Ready to transform your tax preparation?",
  description = "Join thousands of tax professionals who are saving time and reducing errors with Ctrl+Filing.",
  primaryButtonText = "Get Started",
  secondaryButtonText = "Schedule a Demo",
}: CTASectionProps) {
  return (
    <div className="bg-blue-600 text-white py-16">
      <div className="container mx-auto px-4 text-center">
        <h2 className="text-3xl md:text-4xl font-bold mb-4 animate-in fade-in-50 duration-700">{title}</h2>
        <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto animate-in fade-in-50 duration-700 delay-100">
          {description}
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center animate-in fade-in-50 duration-700 delay-200">
          <Button className="bg-white text-blue-600 hover:bg-blue-50">{primaryButtonText}</Button>
          <Button variant="outline" className="text-white border-white hover:bg-blue-700">
            {secondaryButtonText}
          </Button>
        </div>
      </div>
    </div>
  )
}
