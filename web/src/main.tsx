import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { CalendarPage } from './pages/CalendarPage'
import { EventPage } from './pages/EventPage'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<CalendarPage />} />
          <Route path="/events/:id" element={<EventPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
