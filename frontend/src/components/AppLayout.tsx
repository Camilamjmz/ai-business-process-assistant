import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  ["Overview", "/overview"],
  ["AI Assistant", "/assistant"],
  ["Sales Analytics", "/sales"],
  ["Inventory", "/inventory"],
  ["Automation History", "/automation-history"],
  ["Methodology / Evaluation", "/methodology"],
];

export function AppLayout() {
  return (
    <div className="min-h-screen bg-canvas text-ink lg:flex">
      <aside className="border-b border-slate-200 bg-slate-950 px-5 py-6 text-white lg:min-h-screen lg:w-72 lg:border-b-0 lg:border-r">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Research workspace</p>
          <h1 className="mt-2 text-lg font-semibold leading-snug">AI Business Process Assistant</h1>
        </div>
        <nav aria-label="Primary navigation" className="grid gap-1 sm:grid-cols-3 lg:grid-cols-1">
          {navigation.map(([label, to]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `rounded-md px-3 py-2.5 text-sm transition-colors ${
                  isActive
                    ? "bg-slate-800 font-medium text-white"
                    : "text-slate-300 hover:bg-slate-900 hover:text-white"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-8 border-t border-slate-800 pt-5 text-xs text-slate-400">
          Grounded analytics · Read-only agent
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-x-hidden px-5 py-8 sm:px-8 lg:px-12 lg:py-10">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
