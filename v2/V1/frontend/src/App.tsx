import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { AssistantPage } from "./features/assistant/AssistantPage";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { DoctorsPage } from "./features/doctors/DoctorsPage";
import { SourcesPage } from "./features/sources/SourcesPage";
import { TrackerPage } from "./features/tracker/TrackerPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="assistant" element={<AssistantPage />} />
        <Route path="tracker" element={<TrackerPage />} />
        <Route path="doctors" element={<DoctorsPage />} />
        <Route path="sources" element={<SourcesPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
