import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import CampaignForm from "@/components/CampaignForm";
import AppHeader from "@/components/AppHeader";

const CreateCampaign = () => {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <AppHeader />
      <main className="max-w-4xl mx-auto w-full px-4 sm:px-6 py-10">
        <nav className="flex items-center gap-1.5 text-sm text-muted-foreground mb-3">
          <Link to="/" className="hover:text-foreground">Home</Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <Link to="/campaigns" className="hover:text-foreground">Campaigns</Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="text-foreground font-medium">Create</span>
        </nav>
        <h1 className="text-3xl font-semibold text-foreground tracking-tight mb-2">Create New Campaign</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Tell us about your product, audience, and goals. Our AI will generate a strategy in seconds.
        </p>
        <CampaignForm />
      </main>
    </div>
  );
};

export default CreateCampaign;
