import React, { useState, useMemo } from 'react';
import { useCrawlStore } from '../../store/useCrawlStore';
import {
  ChevronRight,
  ChevronLeft,
  AlertTriangle,
  FolderTree,
  PieChart,
  Clock,
  Layers,
  Search,
  ChevronDown,
  ChevronUp,
  Check,
  Copy,
  ExternalLink,
  Wrench,
  BookOpen,
  Eye,
  X,
  Folder,
  FileCode
} from 'lucide-react';

export const RightPanel: React.FC = () => {
  const {
    isRightPanelOpen,
    toggleRightPanel,
    rightPanelTab,
    setRightPanelTab,
    rightPanelData,
    auditId,
  } = useCrawlStore();

  if (!isRightPanelOpen) {
    return (
      <div className="w-8 border-l border-[#C8B670] bg-[#FFF7D6] flex flex-col items-center py-3 select-none">
        <button
          onClick={toggleRightPanel}
          title="Open Side Panel"
          className="p-1 hover:bg-[#FFE08A] rounded border border-[#C8B670] bg-white mb-4 shadow-xs"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="text-[11px] font-bold text-gray-700 [writing-mode:vertical-rl] rotate-180 tracking-wider">
          SITE SUMMARY
        </span>
      </div>
    );
  }

  const navTabs = [
    { key: 'site-issues', label: 'Issues', icon: AlertTriangle },
    { key: 'structure', label: 'Structure', icon: FolderTree },
    { key: 'segments', label: 'Segments', icon: PieChart },
    { key: 'response-times', label: 'Response', icon: Clock },
    { key: 'depth', label: 'Depth', icon: Layers },
  ];

  const currentData = rightPanelData[rightPanelTab as keyof typeof rightPanelData];

  return (
    <aside className="w-96 md:w-[440px] border-l border-[#C8B670] bg-white flex flex-col select-none text-black overflow-hidden shrink-0 shadow-sm">
      {/* Panel Header */}
      <div className="bg-[#FFE08A] border-b border-[#C8B670] px-3 py-1.5 flex items-center justify-between text-xs shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="font-bold uppercase tracking-wider text-[11px] text-black">
            Site Summary & Issues
          </span>
        </div>
        <button
          onClick={toggleRightPanel}
          className="p-0.5 text-gray-700 hover:text-black hover:bg-[#FFF7D6] rounded border border-transparent hover:border-[#C8B670]"
          title="Collapse Panel"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Panel Icon Tabs */}
      <div className="flex border-b border-[#E2D5A0] bg-[#FFF7D6] text-xs shrink-0">
        {navTabs.map((t) => {
          const Icon = t.icon;
          const isActive = rightPanelTab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setRightPanelTab(t.key)}
              title={t.label}
              className={`flex-1 py-1.5 flex flex-col items-center justify-center gap-0.5 border-b-2 transition-colors ${
                isActive
                  ? 'border-b-black bg-white font-bold text-black shadow-xs'
                  : 'border-b-transparent text-gray-600 hover:bg-white/50'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="text-[10px]">{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* Panel Scrollable Body */}
      <div className="flex-1 overflow-auto p-2.5 text-xs bg-white">
        {!auditId ? (
          <div className="text-center py-12 text-gray-400">
            <AlertTriangle className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="font-medium text-xs">No active audit selected</p>
            <p className="text-[11px] text-gray-400 mt-1">Run or load a crawl to view site metrics & SEO fixes.</p>
          </div>
        ) : (
          renderPanelContent(rightPanelTab, currentData)
        )}
      </div>
    </aside>
  );
};

function renderPanelContent(tab: string, data: any) {
  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-400">
        <div className="w-5 h-5 border-2 border-black border-t-transparent rounded-full animate-spin mb-2" />
        <span>Loading {tab} analysis...</span>
      </div>
    );
  }

  switch (tab) {
    case 'site-issues':
      return <SiteIssuesView data={data} />;

    case 'structure':
      return <SiteStructureView data={data} />;

    case 'segments': {
      const segments = Array.isArray(data) ? data : (data.segments || []);
      return segments.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No URL path segments found.</div>
      ) : (
        <div className="space-y-2.5">
          <div className="text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-2">
            URL Path Segments ({segments.length})
          </div>
          {segments.map((seg: any, idx: number) => (
            <div key={idx} className="space-y-1 p-1.5 border border-[#E2D5A0] bg-[#FFF7D6]/20 rounded-xs">
              <div className="flex justify-between font-medium text-xs">
                <span className="font-mono truncate font-semibold">{seg.segment}</span>
                <span className="font-bold text-black">{seg.count} ({seg.pct}%)</span>
              </div>
              <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-[#FFE08A] border-r border-[#C8B670] h-full transition-all duration-300"
                  style={{ width: `${seg.pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      );
    }

    case 'response-times': {
      const buckets = Array.isArray(data) ? data : (data.buckets || []);
      return buckets.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No response time data recorded.</div>
      ) : (
        <div className="space-y-2.5">
          <div className="text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-2">
            TTFB / Response Time Distribution
          </div>
          {buckets.map((b: any, idx: number) => (
            <div key={idx} className="space-y-1 p-1.5 border border-[#E2D5A0] bg-[#FFF7D6]/20 rounded-xs">
              <div className="flex justify-between font-medium text-xs">
                <span className="font-semibold">{b.range}</span>
                <span className="font-bold text-black">{b.count} ({b.pct}%)</span>
              </div>
              <div className="w-full bg-gray-200 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-black h-full transition-all duration-300"
                  style={{ width: `${b.pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      );
    }

    case 'depth': {
      const levels = Array.isArray(data) ? data : (data.depths || []);
      return levels.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No crawl depth distribution.</div>
      ) : (
        <div className="space-y-2.5">
          <div className="text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-2">
            Crawl Depth / Click Distance
          </div>
          {levels.map((lvl: any, idx: number) => (
            <div key={idx} className="space-y-1 p-1.5 border border-[#E2D5A0] bg-[#FFF7D6]/20 rounded-xs">
              <div className="flex justify-between font-medium text-xs">
                <span className="font-semibold">Level {lvl.depth}</span>
                <span className="font-bold text-black">{lvl.count} ({lvl.pct}%)</span>
              </div>
              <div className="w-full bg-gray-200 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-[#FFE08A] border-r border-[#C8B670] h-full transition-all duration-300"
                  style={{ width: `${lvl.pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      );
    }

    default:
      return <pre className="text-[10px] font-mono p-2 bg-gray-50">{JSON.stringify(data, null, 2)}</pre>;
  }
}

/**
 * Site Issues component with severity filtering, search, step-by-step actionable fixes,
 * copyable code snippets, and affected URLs inspector.
 */
function SiteIssuesView({ data }: { data: any }) {
  const { rows, selectPage, isInspectorOpen, toggleInspector } = useCrawlStore();
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning' | 'notice'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedIssues, setExpandedIssues] = useState<Record<string, boolean>>({});
  const [showUrlsMap, setShowUrlsMap] = useState<Record<string, boolean>>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const rawIssuesList = useMemo(() => {
    return Array.isArray(data) ? data : (data.issues || []);
  }, [data]);

  // Counts by priority
  const counts = useMemo(() => {
    let crit = 0;
    let warn = 0;
    let notc = 0;
    rawIssuesList.forEach((iss: any) => {
      const p = (iss.issue_priority || iss.severity || 'info').toLowerCase();
      if (p === 'critical') crit++;
      else if (p === 'warning' || p === 'high') warn++;
      else notc++;
    });
    return { all: rawIssuesList.length, critical: crit, warning: warn, notice: notc };
  }, [rawIssuesList]);

  // Filtered issues
  const filteredIssues = useMemo(() => {
    return rawIssuesList.filter((iss: any) => {
      const p = (iss.issue_priority || iss.severity || 'info').toLowerCase();
      if (filter === 'critical' && p !== 'critical') return false;
      if (filter === 'warning' && p !== 'warning' && p !== 'high') return false;
      if (filter === 'notice' && p !== 'notice' && p !== 'medium' && p !== 'low' && p !== 'info') return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const name = (iss.issue_name || iss.title || iss.name || '').toLowerCase();
        const desc = (iss.description || '').toLowerCase();
        const fix = (iss.how_to_fix || iss.recommendation || '').toLowerCase();
        const type = (iss.issue_type || iss.category || '').toLowerCase();
        return name.includes(q) || desc.includes(q) || fix.includes(q) || type.includes(q);
      }
      return true;
    });
  }, [rawIssuesList, filter, searchQuery]);

  const toggleExpand = (key: string) => {
    setExpandedIssues((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleShowUrls = (key: string) => {
    setShowUrlsMap((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleInspectUrl = (url: string) => {
    const targetRow = rows.find((r) => r.url === url);
    if (targetRow) {
      selectPage(targetRow.id);
      if (!isInspectorOpen) {
        toggleInspector();
      }
    }
  };

  if (rawIssuesList.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <Check className="w-8 h-8 text-[#15803d] mx-auto mb-2" />
        <p className="font-bold text-xs text-gray-800">No Technical Issues Found</p>
        <p className="text-[11px] text-gray-400 mt-1">All scanned pages passed standard technical SEO checks.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {/* Priority Filter Bar */}
      <div className="flex items-center gap-1 bg-[#FFF7D6] p-1 border border-[#E2D5A0] rounded-xs text-[11px]">
        <button
          onClick={() => setFilter('all')}
          className={`flex-1 py-1 px-1.5 font-bold rounded-xs text-center transition-colors ${
            filter === 'all'
              ? 'bg-black text-white shadow-xs'
              : 'text-gray-700 hover:bg-white/60'
          }`}
        >
          All ({counts.all})
        </button>
        <button
          onClick={() => setFilter('critical')}
          className={`flex-1 py-1 px-1.5 font-bold rounded-xs text-center transition-colors ${
            filter === 'critical'
              ? 'bg-[#b91c1c] text-white shadow-xs'
              : 'text-[#b91c1c] hover:bg-red-50'
          }`}
        >
          Critical ({counts.critical})
        </button>
        <button
          onClick={() => setFilter('warning')}
          className={`flex-1 py-1 px-1.5 font-bold rounded-xs text-center transition-colors ${
            filter === 'warning'
              ? 'bg-[#b45309] text-white shadow-xs'
              : 'text-[#b45309] hover:bg-amber-50'
          }`}
        >
          Warning ({counts.warning})
        </button>
        <button
          onClick={() => setFilter('notice')}
          className={`flex-1 py-1 px-1.5 font-bold rounded-xs text-center transition-colors ${
            filter === 'notice'
              ? 'bg-[#1d4ed8] text-white shadow-xs'
              : 'text-[#1d4ed8] hover:bg-blue-50'
          }`}
        >
          Notice ({counts.notice})
        </button>
      </div>

      {/* Search Input Box */}
      <div className="relative">
        <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2 top-2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search issues, URLs or fixes..."
          className="w-full pl-7 pr-7 py-1.5 text-xs border border-[#C8B670] bg-white rounded-xs focus:outline-hidden focus:border-black font-medium"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-2 top-2 text-gray-400 hover:text-black"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Issues List */}
      <div className="space-y-2">
        {filteredIssues.length === 0 ? (
          <div className="text-center py-6 text-gray-400 text-xs">
            No issues match the selected filter.
          </div>
        ) : (
          filteredIssues.map((group: any, idx: number) => {
            const title = group.issue_name || group.title || group.name || 'SEO Issue';
            const priority = (group.issue_priority || group.severity || 'warning').toLowerCase();
            const category = group.issue_type || group.category || 'Technical SEO';
            const urlCount = group.urls !== undefined ? group.urls : (group.urls_list ? group.urls_list.length : 0);
            const pct = group.pct_of_total !== undefined ? group.pct_of_total : 0;
            const isExpanded = expandedIssues[title] ?? (idx === 0);
            const isUrlsOpen = showUrlsMap[title] ?? false;
            const urlsList = group.urls_list || [];

            const isCritical = priority === 'critical';
            const isWarning = priority === 'warning' || priority === 'high';

            return (
              <div
                key={idx}
                className={`border rounded-xs transition-shadow duration-150 overflow-hidden ${
                  isCritical
                    ? 'border-[#fca5a5] bg-[#fff5f5]'
                    : isWarning
                    ? 'border-[#fde68a] bg-[#fffdf0]'
                    : 'border-[#bfdbfe] bg-[#f8faff]'
                }`}
              >
                {/* Issue Header Bar */}
                <div
                  onClick={() => toggleExpand(title)}
                  className="p-2 cursor-pointer flex items-start justify-between gap-2 hover:bg-black/5 select-none"
                >
                  <div className="flex items-start gap-2 min-w-0">
                    <span
                      className={`px-1.5 py-0.5 rounded-xs font-black text-[9px] uppercase tracking-wider shrink-0 mt-0.5 ${
                        isCritical
                          ? 'bg-[#b91c1c] text-white'
                          : isWarning
                          ? 'bg-[#b45309] text-white'
                          : 'bg-[#1d4ed8] text-white'
                      }`}
                    >
                      {isCritical ? 'CRITICAL' : isWarning ? 'WARNING' : 'NOTICE'}
                    </span>
                    <div className="min-w-0">
                      <div className="font-bold text-xs text-black leading-tight truncate" title={title}>
                        {title}
                      </div>
                      <div className="text-[10px] text-gray-500 font-medium">
                        {category}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="px-1.5 py-0.2 bg-black text-white font-mono text-[10px] font-bold rounded-full">
                      {urlCount} {urlCount === 1 ? 'URL' : 'URLs'} {pct > 0 ? `(${pct}%)` : ''}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    )}
                  </div>
                </div>

                {/* Collapsible Issue Details & Fix Section */}
                {isExpanded && (
                  <div className="p-2.5 pt-0 border-t border-black/10 space-y-2.5 text-xs">
                    {/* SEO Impact Description */}
                    {group.description && (
                      <div className="text-gray-700 text-[11px] leading-relaxed pt-2">
                        {group.description}
                      </div>
                    )}

                    {/* How to Fix Callout Box */}
                    <div className="border border-[#C8B670] bg-[#FFF7D6] p-2.5 rounded-xs space-y-2">
                      <div className="flex items-center gap-1.5 font-bold text-xs text-black">
                        <Wrench className="w-3.5 h-3.5 text-[#b45309]" />
                        <span>How to Fix This Issue</span>
                      </div>

                      {/* Step-by-step instructions */}
                      {group.how_to_fix && (
                        <div className="text-gray-800 text-[11px] leading-relaxed whitespace-pre-line font-medium pl-1 border-l-2 border-[#C8B670]">
                          {group.how_to_fix}
                        </div>
                      )}

                      {/* Code Snippet Box */}
                      {group.code_snippet && (
                        <div className="mt-2 space-y-1">
                          <div className="flex items-center justify-between text-[10px] font-mono font-bold text-gray-600">
                            <span className="flex items-center gap-1">
                              <FileCode className="w-3 h-3" />
                              Recommended Configuration / Code:
                            </span>
                            <button
                              onClick={() => handleCopy(group.code_snippet, `snippet-${idx}`)}
                              className="flex items-center gap-1 px-1.5 py-0.5 bg-white border border-[#C8B670] rounded-xs text-black hover:bg-black hover:text-white transition-colors"
                              title="Copy Code Snippet"
                            >
                              {copiedKey === `snippet-${idx}` ? (
                                <>
                                  <Check className="w-3 h-3 text-[#15803d]" />
                                  <span className="text-[#15803d]">Copied!</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-3 h-3" />
                                  <span>Copy Snippet</span>
                                </>
                              )}
                            </button>
                          </div>
                          <pre className="p-2 bg-[#18181b] text-[#f4f4f5] font-mono text-[11px] rounded-xs overflow-x-auto whitespace-pre-wrap select-all leading-snug">
                            {group.code_snippet}
                          </pre>
                        </div>
                      )}

                      {/* Help Documentation Link */}
                      {group.help_url && (
                        <div className="pt-1 flex items-center justify-end">
                          <a
                            href={group.help_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[10px] font-bold text-black hover:underline"
                          >
                            <BookOpen className="w-3 h-3" />
                            Official Documentation
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        </div>
                      )}
                    </div>

                    {/* Affected URLs Accordion */}
                    {urlsList.length > 0 && (
                      <div className="border border-[#E2D5A0] rounded-xs bg-white overflow-hidden">
                        <button
                          onClick={() => toggleShowUrls(title)}
                          className="w-full px-2 py-1.5 bg-[#FFF7D6]/50 flex items-center justify-between text-[11px] font-bold text-gray-800 hover:bg-[#FFE08A]/40 transition-colors"
                        >
                          <span>Affected URLs ({urlsList.length})</span>
                          <span className="text-[10px] text-gray-500">
                            {isUrlsOpen ? 'Hide URLs ▲' : 'Show URLs ▼'}
                          </span>
                        </button>

                        {isUrlsOpen && (
                          <div className="max-h-48 overflow-y-auto divide-y divide-[#E2D5A0] p-1 bg-white font-mono text-[11px]">
                            {urlsList.map((urlStr: string, uIdx: number) => (
                              <div
                                key={uIdx}
                                className="p-1 flex items-center justify-between gap-1 hover:bg-[#FFF7D6]/40"
                              >
                                <span className="truncate flex-1 font-medium select-all" title={urlStr}>
                                  {urlStr}
                                </span>
                                <div className="flex items-center gap-1 shrink-0">
                                  <button
                                    onClick={() => handleInspectUrl(urlStr)}
                                    className="p-1 text-gray-600 hover:text-black hover:bg-gray-200 rounded-xs"
                                    title="Inspect in Table & Inspector"
                                  >
                                    <Eye className="w-3 h-3" />
                                  </button>
                                  <button
                                    onClick={() => handleCopy(urlStr, `url-${idx}-${uIdx}`)}
                                    className="p-1 text-gray-600 hover:text-black hover:bg-gray-200 rounded-xs"
                                    title="Copy URL"
                                  >
                                    {copiedKey === `url-${idx}-${uIdx}` ? (
                                      <Check className="w-3 h-3 text-[#15803d]" />
                                    ) : (
                                      <Copy className="w-3 h-3" />
                                    )}
                                  </button>
                                  <a
                                    href={urlStr}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="p-1 text-gray-600 hover:text-black hover:bg-gray-200 rounded-xs"
                                    title="Open URL in Browser"
                                  >
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

/**
 * Site Structure interactive tree component
 */
function SiteStructureView({ data }: { data: any }) {
  const treeNodes = Array.isArray(data) ? data : (data.tree || []);

  if (treeNodes.length === 0) {
    return <div className="text-center py-8 text-gray-500">No site structure hierarchy available.</div>;
  }

  return (
    <div className="space-y-2">
      <div className="text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-2">
        Directory Path Hierarchy
      </div>
      <div className="border border-[#C8B670] bg-[#FFF7D6]/20 p-2 font-mono text-xs rounded-xs max-h-[500px] overflow-y-auto">
        {treeNodes.map((node: any, idx: number) => (
          <TreeNodeItem key={idx} node={node} level={0} />
        ))}
      </div>
    </div>
  );
}

function TreeNodeItem({ node, level }: { node: any; level: number }) {
  const [open, setOpen] = useState(true);
  const children = Array.isArray(node.children)
    ? node.children
    : node.children
    ? Object.values(node.children)
    : [];
  const hasChildren = children.length > 0;

  return (
    <div className="select-none">
      <div
        onClick={() => hasChildren && setOpen(!open)}
        className="flex items-center gap-1.5 py-1 px-1 hover:bg-[#FFE08A]/40 rounded-xs cursor-pointer text-xs"
        style={{ paddingLeft: `${level * 14 + 4}px` }}
      >
        {hasChildren ? (
          open ? <ChevronDown className="w-3 h-3 text-gray-500" /> : <ChevronRight className="w-3 h-3 text-gray-500" />
        ) : (
          <span className="w-3 inline-block" />
        )}
        <Folder className="w-3.5 h-3.5 text-[#b45309] shrink-0" />
        <span className="font-semibold text-black truncate">{node.path || node.name || '/'}</span>
        <span className="ml-auto text-[10px] font-bold bg-black text-white px-1.5 py-0.2 rounded-full">
          {node.count || 0}
        </span>
      </div>
      {hasChildren && open && (
        <div>
          {children.map((child: any, i: number) => (
            <TreeNodeItem key={i} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
