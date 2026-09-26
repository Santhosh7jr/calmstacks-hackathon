import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
};

export function Card({ children, className = "" }: CardProps) {
  return (
    <article
      className={`rounded-2xl border border-white/10 bg-white/[0.035] ${className}`.trim()}
    >
      {children}
    </article>
  );
}

export default Card;
