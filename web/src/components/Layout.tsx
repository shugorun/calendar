import { Link, Outlet } from 'react-router-dom'

// 全ページ共通のランドマーク: header(banner) / main / footer(contentinfo)。
export function Layout() {
  return (
    <>
      <header className="topbar">
        <Link className="brand" to="/">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="16" height="16">
              <g stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
                <line x1="12" y1="3" x2="12" y2="21" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="5.5" y1="5.5" x2="18.5" y2="18.5" />
                <line x1="18.5" y1="5.5" x2="5.5" y2="18.5" />
              </g>
            </svg>
          </span>
          Floaty
        </Link>
      </header>
      <main>
        <Outlet />
      </main>
      <footer className="site-footer">
        <p className="footer-note">
          スクショ・テキストから、まだ確定していない予定を拾って忘れないために。ローカルで動く個人用カレンダー。
        </p>
      </footer>
    </>
  )
}
