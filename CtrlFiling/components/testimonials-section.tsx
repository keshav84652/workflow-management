import Image from "next/image"
import { cn } from "@/lib/utils"

type TestimonialProps = {
  name: string
  username: string
  text: string
  avatar: string
}

const testimonials: TestimonialProps[] = [
  {
    name: "Fatima Khoury",
    username: "dilatory_curtains_98",
    text: "The progress tracker is fantastic. It's motivating to see how much I've improved over time. The app has a great mix of common and challenging words.",
    avatar: "/avatar-fatima.png",
  },
  {
    name: "Hassan Ali",
    username: "turbulent_unicorn_29",
    text: "The progress tracker is fantastic. It's motivating to see how much I've improved over time. The app has a great mix of common and challenging words.",
    avatar: "/avatar-hassan.png",
  },
  {
    name: "Jorge Martinez",
    username: "nefarious_jellybeans_91",
    text: "The progress tracker is fantastic. It's motivating to see how much I've improved over time. The app has a great mix of common and challenging words.",
    avatar: "/avatar-jorge.png",
  },
]

const TestimonialCard = ({ testimonial }: { testimonial: TestimonialProps }) => {
  return (
    <div
      className={cn(
        "bg-white p-6 rounded-xl shadow-sm relative",
        "hover:shadow-md transition-all duration-300 hover:translate-y-[-4px]",
        "animate-in fade-in-50 slide-in-from-bottom-5 duration-700",
      )}
    >
      <div className="text-gray-300 text-5xl font-serif mb-4">"</div>
      <p className="text-gray-700 mb-6">
        {testimonial.text.split("challenging").map((part, i, arr) => (
          <span key={i}>
            {part}
            {i < arr.length - 1 && <span className="text-orange-500 font-medium">challenging</span>}
          </span>
        ))}
      </p>
      <div className="flex items-center">
        <Image
          src={testimonial.avatar || "/placeholder.svg"}
          alt={testimonial.name}
          width={48}
          height={48}
          className="rounded-full mr-4"
        />
        <div>
          <h4 className="font-bold text-gray-900">{testimonial.name}</h4>
          <p className="text-gray-500 text-sm">{testimonial.username}</p>
        </div>
      </div>
    </div>
  )
}

export function TestimonialsSection() {
  return (
    <div className="bg-gray-50 py-16">
      <div className="container mx-auto px-4">
        <div className="text-center mb-12">
          <div className="inline-block border border-orange-500 text-orange-500 px-4 py-1 rounded-full text-sm font-medium mb-4">
            TESTIMONIALS
          </div>
          <h2 className="text-4xl font-bold text-gray-900 mb-8">Our trusted clients</h2>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {testimonials.map((testimonial, index) => (
            <TestimonialCard key={index} testimonial={testimonial} />
          ))}
        </div>
      </div>
    </div>
  )
}
