import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Index from "./pages/Index.tsx";
import CreateCampaign from "./pages/CreateCampaign.tsx";
import CampaignStrategy from "./pages/CampaignStrategy.tsx";
import CampaignApproval from "./pages/CampaignApproval.tsx";
import CampaignMetrics from "./pages/CampaignMetrics.tsx";
import Campaigns from "./pages/Campaigns.tsx";
import CampaignDetail from "./pages/CampaignDetail.tsx";
import EmailVariantPage from "./pages/EmailVariantPage.tsx";
import NotFound from "./pages/NotFound.tsx";
import { CampaignsProvider } from "./context/CampaignsContext.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <CampaignsProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/campaigns" element={<Campaigns />} />
            <Route path="/campaigns/create" element={<CreateCampaign />} />
            <Route path="/campaigns/:id/strategy" element={<CampaignStrategy />} />
            <Route path="/campaigns/approval" element={<CampaignApproval />} />
            <Route path="/campaigns/metrics" element={<CampaignMetrics />} />
            <Route path="/campaigns/:id" element={<CampaignDetail />} />
            <Route path="/campaigns/:id/:variantId" element={<EmailVariantPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </CampaignsProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
