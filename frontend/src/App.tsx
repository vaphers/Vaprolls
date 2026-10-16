import React, { useEffect } from 'react';
import { useCrawlStore } from './store/useCrawlStore';
import { SpiderHeader } from './components/header/SpiderHeader';
import { CategoryTabs } from './components/tabs/CategoryTabs';
import { MasterTable } from './components/table/MasterTable';
import { UrlInspector } from './components/inspector/UrlInspector';
import { RightPanel } from './components/panels/RightPanel';

export const App: React.FC = () => {
  const { switchTab, setRightPanelTab } = useCrawlStore();

  useEffect(() => {
    // Check URL parameters for audit_id and tab
    const urlParams = new URLSearchParams(window.location.search);
    const urlAuditId = urlParams.get('audit_id');
    const urlTab = urlParams.get('tab') || 'all';

    if (urlAuditId) {
      useCrawlStore.setState({ auditId: urlAuditId });
      switchTab(urlTab);
      setRightPanelTab('site-issues');
    }
  }, [switchTab, setRightPanelTab]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-white text-black font-sans">
      {/* 1. Header Bar */}
      <SpiderHeader />

      {/* 2. Category Tabs & Filters */}
      <CategoryTabs />

      {/* 3. Main Workspace Grid */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Table & Bottom Inspector Column */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Virtualized Master Table */}
          <MasterTable />

          {/* Bottom URL Inspector */}
          <UrlInspector />
        </div>

        {/* Right Side Overview Panel */}
        <RightPanel />
      </div>
    </div>
  );
};

export default App;
