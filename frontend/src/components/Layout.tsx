import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: 'Übersicht', end: true },
  { to: '/jobs/new', label: 'Neuer Druckauftrag' },
  { to: '/presets', label: 'Standarddruckobjekte' },
  { to: '/queue', label: 'Warteschlange' },
  { to: '/failed', label: 'Fehlgeschlagen' },
  { to: '/printer', label: 'Drucker-Status' },
  { to: '/settings', label: 'Konfiguration' },
]

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="app-shell">
      <header className="mobile-header">
        <button
          className="burger-btn"
          onClick={() => setSidebarOpen((o) => !o)}
          aria-label="Navigation öffnen"
          aria-expanded={sidebarOpen}
        >
          <span className="burger-icon" />
        </button>
        <img src="/logo.png" alt="Bondrucker" className="mobile-logo" />
      </header>

      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      <aside className={`sidebar${sidebarOpen ? ' sidebar-open' : ''}`}>
        <h1>
          <img src="/logo.png" alt="Bondrucker" className="sidebar-logo" />
        </h1>
        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? 'active' : '')}
              onClick={() => setSidebarOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
