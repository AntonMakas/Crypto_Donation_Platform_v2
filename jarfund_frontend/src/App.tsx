import { Suspense, lazy } from 'react'
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom'

import { ROUTES } from '@/lib/constants'
import { useAuth } from '@/contexts/AuthContext'
import AppLayout   from '@/components/layout/AppLayout'
import { PageSpinner } from '@/components/ui/PageSpinner'



// ── Lazy-loaded pages ─────────────────────────────────────────────
const HomePage       = lazy(() => import('@/pages/HomePage'))
const ExplorePage    = lazy(() => import('@/pages/ExplorePage'))
const JarDetailPage  = lazy(() => import('@/pages/JarDetailPage'))
const CreateJarPage  = lazy(() => import('@/pages/CreateJarPage'))
const ProfilePage    = lazy(() => import('@/pages/ProfilePage'))
const NotFoundPage   = lazy(() => import('@/pages/NotFoundPage'))

// ── Protected route wrapper ───────────────────────────────────────
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to={ROUTES.HOME} replace />
  return <>{children}</>
}

// ── App ───────────────────────────────────────────────────────────
export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageSpinner />}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index                 element={<HomePage />} />
            <Route path={ROUTES.EXPLORE} element={<ExplorePage />} />
            <Route path="/jar/:id"       element={<JarDetailPage />} />
            <Route path={ROUTES.CREATE}  element={<CreateJarPage />} />
            <Route path={ROUTES.PROFILE} element={<ProfilePage />} />
            <Route path="*"              element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

// export default function App() {
//   return (
//     <BrowserRouter>
//       <Suspense fallback={<PageSpinner />}>
//         <Routes>
//           <Route element={<AppLayout />}>
//             {/* Public */}
//             <Route index                   element={<HomePage />} />
//             <Route path={ROUTES.EXPLORE}   element={<ExplorePage />} />
//             <Route path="/jar/:id"         element={<JarDetailPage />} />

//             {/* Protected */}
//             <Route
//               path={ROUTES.CREATE}
//               element={
//                 <RequireAuth>
//                   <CreateJarPage />
//                 </RequireAuth>
//               }
//             />
//             <Route
//               path={ROUTES.PROFILE}
//               element={
//                 <RequireAuth>
//                   <ProfilePage />
//                 </RequireAuth>
//               }
//             />

//             {/* 404 */}
//             <Route path="*" element={<NotFoundPage />} />
//           </Route>
//         </Routes>
//       </Suspense>
//     </BrowserRouter>
//   )
// }
