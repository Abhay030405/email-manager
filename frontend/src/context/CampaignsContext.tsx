import { createContext, useContext, useState, ReactNode, useCallback } from "react";
import { Campaign, CampaignStatus, initialCampaigns } from "@/data/campaignsData";

interface CampaignsContextValue {
  campaigns: Campaign[];
  getCampaign: (id: string) => Campaign | undefined;
  setStatus: (id: string, status: CampaignStatus, note?: string) => void;
}

const CampaignsContext = createContext<CampaignsContextValue | undefined>(undefined);

export const CampaignsProvider = ({ children }: { children: ReactNode }) => {
  const [campaigns, setCampaigns] = useState<Campaign[]>(initialCampaigns);

  const getCampaign = useCallback(
    (id: string) => campaigns.find((c) => c.id === id),
    [campaigns],
  );

  const setStatus = useCallback((id: string, status: CampaignStatus, note?: string) => {
    setCampaigns((prev) =>
      prev.map((c) => (c.id === id ? { ...c, status, revisionNotes: note ?? c.revisionNotes } : c)),
    );
  }, []);

  return (
    <CampaignsContext.Provider value={{ campaigns, getCampaign, setStatus }}>
      {children}
    </CampaignsContext.Provider>
  );
};

export const useCampaigns = () => {
  const ctx = useContext(CampaignsContext);
  if (!ctx) throw new Error("useCampaigns must be used within CampaignsProvider");
  return ctx;
};
