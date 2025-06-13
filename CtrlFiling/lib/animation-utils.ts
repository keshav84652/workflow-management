import { cn } from "@/lib/utils"

// Button animation classes
export const buttonAnimationClasses = {
  base: "transition-all duration-200 ease-in-out",
  hover: "hover:translate-y-[-2px] hover:shadow-lg",
  active: "active:scale-[0.97] active:shadow-none",
  disabled: "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:transform-none disabled:hover:shadow-none",
}

// Link animation classes
export const linkAnimationClasses = {
  base: "relative transition-colors duration-300 ease-in-out",
  underline:
    "after:absolute after:bottom-0 after:left-0 after:h-[2px] after:w-0 after:bg-current after:transition-all after:duration-300 after:ease-in-out hover:after:w-full",
}

// Card animation classes
export const cardAnimationClasses = {
  base: "transition-all duration-200 ease-in-out",
  hover: "hover:scale-[1.015] hover:translate-y-[-4px] hover:shadow-2xl",
}

// File upload area animation classes
export const fileUploadAnimationClasses = {
  base: "transition-all duration-250 ease-in-out",
  dragActive: "scale-[1.02] border-blue-500 bg-blue-50",
}

// Header animation classes
export const headerAnimationClasses = {
  base: "transition-all duration-200 ease-in-out",
  scrolled: "h-[60px] shadow-md",
  default: "h-[72px]",
}

// Page transition classes
export const pageTransitionClasses = {
  enter: "transition-opacity duration-300 ease-in-out opacity-0",
  enterActive: "opacity-100",
  exit: "transition-opacity duration-300 ease-in-out opacity-100",
  exitActive: "opacity-0",
}

// Combine animation classes with other classes
export const withAnimations = (baseClasses: string, animationClasses: string) => {
  return cn(baseClasses, animationClasses)
}
