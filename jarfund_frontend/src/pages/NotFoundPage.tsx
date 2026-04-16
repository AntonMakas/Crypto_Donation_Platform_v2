import { Link }      from 'react-router-dom'
import { motion }    from 'framer-motion'
import { ArrowLeft } from 'lucide-react'
import { ROUTES }    from '@/lib/constants'

export default function NotFoundPage() {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center px-4 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
        className="space-y-6 max-w-md"
      >
        {/* Animated jar */}
        <motion.div
          animate={{ y: [0, -12, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          className="text-8xl"
        >
          🫙
        </motion.div>

        <div className="space-y-3">
          <h1 className="font-display font-black text-7xl text-gradient">404</h1>
          <h2 className="font-display font-bold text-2xl text-text-primary">
            This jar is empty
          </h2>
          <p className="text-text-muted leading-relaxed">
            The page you're looking for doesn't exist, or may have been moved.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Link to={ROUTES.HOME} className="btn-primary px-8 py-3">
            <ArrowLeft size={15} /> Back home
          </Link>
          <Link to={ROUTES.EXPLORE} className="btn-secondary px-8 py-3">
            Explore jars
          </Link>
        </div>
      </motion.div>
    </div>
  )
}
