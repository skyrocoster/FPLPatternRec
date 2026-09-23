import { Route, Routes } from "react-router-dom";

import { AppShell } from "./features/app-shell/AppShell";
import PageNotFoundView from "./features/app-shell/PageNotFoundView";
import { StatusPage } from "./features/status/StatusPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<StatusPage />} />
        <Route path="*" element={<PageNotFoundView />} />
      </Routes>
    </AppShell>
  );
}
