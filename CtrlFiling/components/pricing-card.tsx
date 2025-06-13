import type React from "react"
import { Button } from "@/components/ui/button"
import { CheckIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { cardAnimationClasses } from "@/lib/animation-utils"

type PricingCardProps = {
  title: string
  price: string
  description: string
  features: string[]
  buttonText: string
  buttonVariant?: "default" | "outline"
  highlighted?: boolean
  badge?: string
  className?: string
  delay?: number
  cardRef?: React.RefObject<HTMLDivElement>
  badgeRef?: React.RefObject<HTMLDivElement>
}

export function PricingCard({
  title,
  price,
  description,
  features,
  buttonText,
  buttonVariant = "default",
  highlighted = false,
  badge,
  className,
  delay = 0,
  cardRef,
  badgeRef,
}: PricingCardProps) {
  return (
    <div
      ref={cardRef}
      className={cn(
        "rounded-xl p-8 relative",
        cardAnimationClasses.base,
        cardAnimationClasses.hover,
        `animate-in fade-in-50 slide-in-from-bottom-5 duration-700 delay-${delay * 100}`,
        "transition-transform duration-300 ease-in-out",
        highlighted && "ring-2 ring-blue-500",
        className,
      )}
    >
      {badge && (
        <div
          ref={badgeRef}
          className="absolute -top-3 right-8 bg-blue-600 text-white text-xs font-medium px-3 py-1 rounded-full transition-all duration-300 ease-in-out"
        >
          {badge}
        </div>
      )}
      <h2 className="text-xl font-bold text-gray-900 mb-2">{title}</h2>
      <div className="mb-4">
        <div className="flex items-baseline">
          <span className="text-4xl font-bold">{price}</span>
          <span className="ml-2 text-gray-600">per month/user</span>
        </div>
      </div>
      <p className="text-gray-600 mb-6">{description}</p>
      <Button
        variant={buttonVariant}
        className={cn("w-full mb-8", buttonVariant === "default" && "bg-blue-600 hover:bg-blue-700")}
      >
        {buttonText}
      </Button>
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900">
          {title === "Teams"
            ? "Free plan features, plus:"
            : title === "Enterprise"
              ? "Organization plan features, plus:"
              : "Free, forever"}
        </h3>
        <ul className="space-y-3">
          {features.map((feature, index) => (
            <li key={index} className="flex group">
              <CheckIcon className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 transition-transform duration-300 group-hover:scale-110" />
              <span>{feature}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
