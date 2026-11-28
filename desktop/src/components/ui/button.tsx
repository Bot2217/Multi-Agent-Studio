import { Slot } from "@radix-ui/react-slot";
import { motion, useReducedMotion } from "motion/react";
import type { ComponentProps } from "react";
import { motion as motionTokens } from "../../../design/tokens.json";

type ButtonProps = Omit<
  ComponentProps<"button">,
  "onAnimationStart" | "onDrag" | "onDragStart" | "onDragEnd"
> & {
  asChild?: boolean;
  variant?: "primary" | "secondary" | "quiet" | "danger";
};

const pressTransition = {
  duration: Number.parseFloat(motionTokens.duration.$value) / 1000,
  ease: motionTokens.ease.$value as [number, number, number, number],
};

export function Button({
  asChild = false,
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  const reducedMotion = useReducedMotion();
  const appearance = {
    "data-variant": variant,
    className: `ulei-button rounded-control ${className}`,
  };

  if (asChild) return <Slot {...props} {...appearance} />;
  const canAnimate = !reducedMotion && !props.disabled
    && props["aria-disabled"] !== true && props["aria-disabled"] !== "true";

  return (
    <motion.button
      {...props}
      {...appearance}
      type={type}
      whileTap={canAnimate ? { scale: 0.98 } : undefined}
      transition={pressTransition}
    />
  );
}
