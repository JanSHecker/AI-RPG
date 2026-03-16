import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { BootScreen } from './routes/boot-screen'
import { PlayScreen } from './routes/play-screen'

const router = createBrowserRouter([
  {
    path: '/',
    element: <BootScreen />,
  },
  {
    path: '/play/:saveId',
    element: <PlayScreen />,
  },
])

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}
