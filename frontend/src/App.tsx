import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { AssistantPage } from "./pages/AssistantPage";

const OverviewPage = lazy(() => import("./pages/OverviewPage").then((module) => ({ default: module.OverviewPage })));
const SalesPage = lazy(() => import("./pages/SalesPage").then((module) => ({ default: module.SalesPage })));
const InventoryPage = lazy(() => import("./pages/InventoryPage").then((module) => ({ default: module.InventoryPage })));
const AutomationHistoryPage = lazy(() => import("./pages/AutomationHistoryPage").then((module) => ({ default: module.AutomationHistoryPage })));
const MethodologyPage = lazy(() => import("./pages/MethodologyPage").then((module) => ({ default: module.MethodologyPage })));

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="/assistant" element={<AssistantPage />} />
        <Route path="/overview" element={<Suspense fallback={<div className="text-sm text-slate-500">Loading dashboard...</div>}><OverviewPage /></Suspense>} />
        <Route path="/sales" element={<Suspense fallback={<div className="text-sm text-slate-500">Loading sales analytics...</div>}><SalesPage /></Suspense>} />
        <Route path="/inventory" element={<Suspense fallback={<div className="text-sm text-slate-500">Loading inventory...</div>}><InventoryPage /></Suspense>} />
        <Route path="/automation-history" element={<Suspense fallback={<div className="text-sm text-slate-500">Loading history...</div>}><AutomationHistoryPage /></Suspense>} />
        <Route path="/methodology" element={<Suspense fallback={<div className="text-sm text-slate-500">Loading methodology...</div>}><MethodologyPage /></Suspense>} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  );
}
