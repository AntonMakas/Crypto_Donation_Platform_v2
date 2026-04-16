import { useEffect, useRef, useState } from 'react'

interface AnimatedCounterProps {
  to:       number
  duration?: number   // ms
  prefix?:  string
  suffix?:  string
  decimals?: number
  className?: string
}

function useInView() {
  const ref = useRef<HTMLSpanElement>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    if (!ref.current) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setInView(true) },
      { threshold: 0.1 }
    )
    obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  return { ref, inView }
}

export default function AnimatedCounter({
  to,
  duration = 1800,
  prefix   = '',
  suffix   = '',
  decimals = 0,
  className,
}: AnimatedCounterProps) {
  const { ref, inView } = useInView()
  const [display, setDisplay] = useState(0)
  const frameRef = useRef<number>()

  useEffect(() => {
    if (!inView) return

    const start     = performance.now()
    const from      = 0
    const easeOutExpo = (t: number) => t === 1 ? 1 : 1 - Math.pow(2, -10 * t)

    const step = (now: number) => {
      const elapsed  = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased    = easeOutExpo(progress)
      setDisplay(from + (to - from) * eased)
      if (progress < 1) frameRef.current = requestAnimationFrame(step)
    }

    frameRef.current = requestAnimationFrame(step)
    return () => { if (frameRef.current) cancelAnimationFrame(frameRef.current) }
  }, [inView, to, duration])

  const formatted = display.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })

  return (
    <span ref={ref} className={className}>
      {prefix}{formatted}{suffix}
    </span>
  )
}
