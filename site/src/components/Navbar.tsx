import { Link, NavLink } from "react-router-dom";
import { Activity, ArrowRight, Code2 } from "lucide-react";

export function Navbar() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="p-1.5 bg-blue-600 rounded-md text-white group-hover:bg-blue-700 transition-colors">
              <Activity className="w-5 h-5" />
            </div>
            <span className="text-xl font-extrabold text-slate-900 tracking-tight">
              Cortex<span className="text-blue-600">Heal</span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
            <NavLink
              to="/docs"
              className={({ isActive }) =>
                `transition-colors hover:text-slate-900 ${
                  isActive ? "text-blue-600 font-semibold" : ""
                }`
              }
            >
              Documentation
            </NavLink>
            <NavLink
              to="/blog"
              className={({ isActive }) =>
                `transition-colors hover:text-slate-900 ${
                  isActive ? "text-blue-600 font-semibold" : ""
                }`
              }
            >
              Engineering Blog
            </NavLink>
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="text-slate-600 hover:text-slate-900 transition-colors"
            >
              API Reference
            </a>
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <a
            href="https://github.com/Ashitpatel001/CortexHeal"
            target="_blank"
            rel="noreferrer"
            className="p-2 text-slate-500 hover:text-slate-900 transition-colors hidden sm:flex items-center gap-1 text-xs font-mono font-medium"
            title="GitHub Repository"
          >
            <Code2 className="w-4 h-4" />
            <span>Source</span>
          </a>

          <a
            href="http://localhost:5173"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-sm transition-all"
          >
            <span>Live Ops Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </div>
    </header>
  );
}
