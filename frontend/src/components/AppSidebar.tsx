import { LayoutDashboard, Megaphone, CheckCircle, BarChart3 } from "lucide-react";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, active: true },
  { label: "Campaigns", icon: Megaphone, active: false },
  { label: "Approvals", icon: CheckCircle, active: false },
  { label: "Metrics", icon: BarChart3, active: false },
];

const AppSidebar = () => {
  return (
    <aside className="w-56 border-r bg-sidebar shrink-0 hidden md:block">
      <nav className="py-4 px-3 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.label}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
              item.active
                ? "bg-primary/10 text-primary"
                : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            }`}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
};

export default AppSidebar;
