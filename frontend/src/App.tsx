import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "./components/Layout";
import { AuthGate } from "./components/AuthGate";
import { IncidentQueue } from "./pages/IncidentQueue";
import { RunsList } from "./pages/RunsList";
import { RunDetail } from "./pages/RunDetail";
import { IncidentDetail } from "./pages/IncidentDetail";
import { FleetView } from "./pages/FleetView";
import { ApiKeysView } from "./pages/ApiKeysView";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthGate>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<IncidentQueue />} />
              <Route path="fleet" element={<FleetView />} />
              <Route path="runs" element={<RunsList />} />
              <Route path="runs/:id" element={<RunDetail />} />
              <Route path="incidents/:id" element={<IncidentDetail />} />
              <Route path="keys" element={<ApiKeysView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthGate>
    </QueryClientProvider>
  );
}

export default App;
