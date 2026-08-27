import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import DashboardLayout from "./components/DashboardLayout";
import { ThemeProvider } from "./contexts/ThemeContext";
import Capabilities from "./pages/Capabilities";
import Dashboard from "./pages/Dashboard";
import Assets from "./pages/Assets";
import Integrations from "./pages/Integrations";
import Intelligence from "./pages/Intelligence";
import Runbooks from "@/pages/Runbooks";
import ServerAssets from "@/pages/ServerAssets";

function Router() {
  // make sure to consider if you need authentication for certain routes
  return (
    <DashboardLayout>
      <Switch>
        <Route path={"/"} component={Dashboard} />
        <Route path={"/assets"} component={Assets} />
        <Route path={"/servers"} component={ServerAssets} />
        <Route path={"/runbooks"} component={Runbooks} />
        <Route path={"/integrations"} component={Integrations} />
        <Route path={"/intelligence"} component={Intelligence} />
        <Route path={"/capabilities"} component={Capabilities} />
        <Route path={"/404"} component={NotFound} />
        <Route component={NotFound} />
      </Switch>
    </DashboardLayout>
  );
}

// NOTE: About Theme
// - First choose a default theme according to your design style (dark or light bg), than change color palette in index.css
//   to keep consistent foreground/background color across components
// - If you want to make theme switchable, pass `switchable` ThemeProvider and use `useTheme` hook

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider
        defaultTheme="dark"
        // switchable
      >
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
