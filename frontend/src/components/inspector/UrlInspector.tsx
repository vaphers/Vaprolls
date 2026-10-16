import React, { useState } from 'react';
import { useCrawlStore } from '../../store/useCrawlStore';
import {
  ChevronDown,
  ChevronUp,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  Wrench,
  Copy,
  Check,
  ExternalLink,
  FileCode,
  BookOpen
} from 'lucide-react';

export const UrlInspector: React.FC = () => {
  const {
    isInspectorOpen,
    toggleInspector,
    selectedPageId,
    inspectorData,
    inspectorLoading,
    activeInspectorTab,
    setActiveInspectorTab,
    filteredRows,
  } = useCrawlStore();

  if (!isInspectorOpen) {
    return (
      <div className="border-t border-[#C8B670] bg-[#FFF7D6] px-3 py-1 flex items-center justify-between text-xs select-none">
        <span className="font-bold text-gray-700">URL Inspector (Collapsed)</span>
        <button onClick={toggleInspector} className="text-gray-500 hover:text-black">
          <ChevronUp className="w-4 h-4" />
        </button>
      </div>
    );
  }

  const selectedRow = filteredRows.find((r) => r.id === selectedPageId) || inspectorData?.page;

  const chainHops = (inspectorData as any)?.redirect_chain_details || inspectorData?.redirect_chain || [];
  const customExt = (inspectorData as any)?.custom_extractions || {};
  const customSrch = (inspectorData as any)?.custom_search || {};
  const hreflangIssues = (inspectorData as any)?.hreflang_issues || [];
  const schemaVal = (inspectorData as any)?.schema_validation || [];

  const tabs = [
    { key: 'overview', label: 'URL Details' },
    { key: 'inlinks', label: `Inlinks (${inspectorData?.inlinks?.length || 0})` },
    { key: 'outlinks', label: `Outlinks (${inspectorData?.outlinks?.length || 0})` },
    { key: 'redirect_chain', label: `Redirect Chain (${chainHops.length})` },
    { key: 'custom_data', label: `Custom Data (${Object.keys(customExt).length + Object.keys(customSrch).length})` },
    { key: 'hreflang', label: `Hreflang (${hreflangIssues.length} issues)` },
    { key: 'structured_data', label: `Schema (${inspectorData?.structured_data?.length || schemaVal.length})` },
    { key: 'images', label: `Images (${inspectorData?.images?.length || 0})` },
    { key: 'resources', label: `Resources (${inspectorData?.resources?.length || 0})` },
    { key: 'headers', label: 'HTTP Headers' },
    { key: 'issues', label: `Issues (${inspectorData?.issues?.length || 0})` },
  ];

  return (
    <div className="h-72 md:h-80 border-t border-[#C8B670] bg-white flex flex-col select-none overflow-hidden text-black">
      {/* Inspector Top Bar */}
      <div className="bg-[#FFE08A] border-b border-[#C8B670] px-3 py-1 flex items-center justify-between text-xs shrink-0">
        <div className="flex items-center gap-2 truncate min-w-0 mr-2">
          <span className="font-bold uppercase tracking-wider text-[11px] text-gray-800 shrink-0">
            Inspector:
          </span>
          {selectedRow ? (
            <span className="truncate font-mono font-medium text-black select-all" title={selectedRow.url}>
              {selectedRow.url}
            </span>
          ) : (
            <span className="text-gray-600 italic">Select a URL in the table to inspect details</span>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {selectedRow && (
            <div className="flex items-center gap-1.5">
              <span
                className={`px-1.5 py-0.2 text-[10px] font-bold border ${
                  selectedRow.status_code === 200
                    ? 'border-[#15803d] text-[#15803d] bg-white'
                    : 'border-[#b91c1c] text-[#b91c1c] bg-white'
                }`}
              >
                {selectedRow.status_code || 0}
              </span>
              <span className="px-1.5 py-0.2 text-[10px] font-bold border border-[#C8B670] bg-white text-black">
                {selectedRow.indexability || '—'}
              </span>
            </div>
          )}
          <button onClick={toggleInspector} className="text-gray-600 hover:text-black">
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Inspector Tabs */}
      <div className="flex items-center overflow-x-auto no-scrollbar border-b border-[#E2D5A0] bg-[#FFF7D6] px-2 text-xs shrink-0">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveInspectorTab(t.key)}
            className={`px-3 py-1 whitespace-nowrap font-medium text-xs border-b-2 transition-colors ${
              activeInspectorTab === t.key
                ? 'border-b-black bg-white font-bold text-black'
                : 'border-b-transparent text-gray-600 hover:bg-white/60'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Inspector Body Content */}
      <div className="flex-1 overflow-auto p-3 text-xs bg-white">
        {inspectorLoading ? (
          <div className="flex items-center justify-center h-full text-gray-400">Loading details...</div>
        ) : !selectedRow ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            Click on any URL row in the table above to view technical breakdown, redirect hops, custom data, and schema.
          </div>
        ) : (
          renderActiveTabContent(activeInspectorTab, selectedRow, inspectorData)
        )}
      </div>
    </div>
  );
};

function renderActiveTabContent(tab: string, row: any, data: any) {
  switch (tab) {
    case 'overview':
      return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <div className="text-[10px] uppercase font-bold text-gray-500">Address</div>
            <div className="font-mono text-xs break-all select-all font-medium">{row.url}</div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] uppercase font-bold text-gray-500">Page Title</div>
            <div className="text-xs">{row.title || '—'}</div>
            <div className="text-[10px] text-gray-500">{row.title ? `${row.title.length} chars` : ''}</div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] uppercase font-bold text-gray-500">Meta Description</div>
            <div className="text-xs">{row.meta_description || '—'}</div>
            <div className="text-[10px] text-gray-500">{row.meta_description ? `${row.meta_description.length} chars` : ''}</div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] uppercase font-bold text-gray-500">H1 Tag</div>
            <div className="text-xs font-semibold">{row.h1 || '—'}</div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] uppercase font-bold text-gray-500">Canonical Element</div>
            <div className="font-mono text-[11px] truncate select-all">{row.canonical_url || '—'}</div>
            <div className="text-[10px] font-bold text-gray-700">{row.canonical_status || ''}</div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] uppercase font-bold text-gray-500">Word Count / Length</div>
            <div className="text-xs font-mono">{row.word_count || 0} words ({row.size_bytes || row.length || 0} bytes)</div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] uppercase font-bold text-gray-500">Click Depth & Orphan Status</div>
            <div className="text-xs font-mono flex items-center gap-2">
              <span>Click Depth: <strong>{row.click_depth !== undefined ? row.click_depth : (row.crawl_depth || 0)}</strong></span>
              {row.is_orphan ? (
                <span className="px-1.5 py-0.2 bg-[#fee2e2] text-[#b91c1c] border border-[#fca5a5] font-bold text-[10px]">
                  ORPHAN (0 Inlinks)
                </span>
              ) : (
                <span className="px-1.5 py-0.2 bg-[#dcfce7] text-[#15803d] border border-[#86efac] font-bold text-[10px]">
                  Connected
                </span>
              )}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] uppercase font-bold text-gray-500">Indexability Status</div>
            <div className="text-xs font-bold text-[#15803d]">{row.indexability_status || row.indexability || 'Indexable'}</div>
          </div>
        </div>
      );

    case 'redirect_chain':
      const chain = data?.redirect_chain_details || data?.redirect_chain || [];
      return chain.length === 0 ? (
        <div className="text-gray-400 py-4 text-center">No redirection hops recorded for this URL (Direct response).</div>
      ) : (
        <div className="space-y-3">
          <div className="font-bold text-xs text-gray-700 uppercase">
            Hop-by-Hop Redirection Path ({chain.length} Hops)
          </div>
          <div className="flex flex-col space-y-2">
            {chain.map((hop: any, idx: number) => {
              const statusCode = hop.status_code || hop.status || 301;
              const isFinal = idx === chain.length - 1;
              return (
                <div key={idx} className="flex items-center gap-3 p-2 border border-[#C8B670] bg-[#FFF7D6]/30 font-mono text-xs">
                  <span className="px-2 py-0.5 bg-black text-white font-bold text-[11px] shrink-0">
                    Hop {idx + 1}
                  </span>
                  <span className={`px-1.5 py-0.5 border font-bold text-xs ${
                    statusCode === 200
                      ? 'border-[#86efac] bg-[#dcfce7] text-[#15803d]'
                      : 'border-[#fde68a] bg-[#fef3c7] text-[#b45309]'
                  }`}>
                    {statusCode}
                  </span>
                  <span className="break-all select-all flex-1 font-medium">
                    {hop.url}
                  </span>
                  {!isFinal && (
                    <ArrowRight className="w-4 h-4 text-gray-400 shrink-0" />
                  )}
                  {isFinal && (
                    <span className="text-[10px] uppercase font-bold text-[#15803d] bg-white border border-[#86efac] px-2 py-0.5 shrink-0">
                      Final Destination
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      );

    case 'custom_data':
      const ext = data?.custom_extractions || {};
      const srch = data?.custom_search || {};
      const extKeys = Object.keys(ext);
      const srchKeys = Object.keys(srch);

      if (extKeys.length === 0 && srchKeys.length === 0) {
        return (
          <div className="text-gray-400 py-4 text-center">
            No custom extractions or search rules configured. Use the "Custom Rules" button in the header.
          </div>
        );
      }

      return (
        <div className="space-y-4">
          {extKeys.length > 0 && (
            <div>
              <div className="font-bold text-xs text-gray-700 uppercase mb-1">Custom Extractions</div>
              <table className="w-full text-left border-collapse font-mono text-xs">
                <thead>
                  <tr className="bg-[#FFF7D6] border-b border-[#C8B670] font-bold">
                    <th className="p-1.5 border-r border-[#C8B670] w-48 font-sans">Field Name</th>
                    <th className="p-1.5 font-sans">Extracted Value(s)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E2D5A0]">
                  {extKeys.map((k) => (
                    <tr key={k} className="hover:bg-[#FFF7D6]">
                      <td className="p-1.5 border-r border-[#E2D5A0] font-bold text-gray-800">{k}</td>
                      <td className="p-1.5 break-all select-all">
                        {Array.isArray(ext[k]) ? ext[k].join(', ') : String(ext[k])}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {srchKeys.length > 0 && (
            <div>
              <div className="font-bold text-xs text-gray-700 uppercase mb-1">Custom Search Matches</div>
              <table className="w-full text-left border-collapse font-mono text-xs">
                <thead>
                  <tr className="bg-[#FFF7D6] border-b border-[#C8B670] font-bold">
                    <th className="p-1.5 border-r border-[#C8B670] w-48 font-sans">Search Rule</th>
                    <th className="p-1.5 border-r border-[#C8B670] w-24 text-center font-sans">Match</th>
                    <th className="p-1.5 font-sans">Matched Snippet</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E2D5A0]">
                  {srchKeys.map((k) => {
                    const item = srch[k];
                    const matched = typeof item === 'object' ? item.matched : Boolean(item);
                    const snippet = typeof item === 'object' ? item.snippet : '';
                    return (
                      <tr key={k} className="hover:bg-[#FFF7D6]">
                        <td className="p-1.5 border-r border-[#E2D5A0] font-bold text-gray-800">{k}</td>
                        <td className="p-1.5 border-r border-[#E2D5A0] text-center font-bold">
                          {matched ? (
                            <span className="text-[#15803d]">YES</span>
                          ) : (
                            <span className="text-gray-400">NO</span>
                          )}
                        </td>
                        <td className="p-1.5 break-all select-all text-gray-700">{snippet || '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      );

    case 'hreflang':
      const hreflang = data?.hreflang_issues || [];
      return hreflang.length === 0 ? (
        <div className="text-center py-6 text-gray-500">
          <CheckCircle className="w-6 h-6 text-[#15803d] mx-auto mb-1" />
          No Hreflang reciprocity issues or missing return tags detected.
        </div>
      ) : (
        <div className="space-y-2">
          {hreflang.map((iss: any, i: number) => (
            <div key={i} className="p-2 border border-[#C8B670] bg-[#FFF7D6]/30 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-black flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-[#b45309]" />
                  {iss.issue_type || 'Hreflang Reciprocal Issue'}
                </span>
                <span className="uppercase text-[10px] font-bold px-1.5 py-0.5 bg-white border border-[#C8B670]">
                  {iss.severity || 'warning'}
                </span>
              </div>
              <p className="text-gray-700">{iss.message || iss.description}</p>
              {iss.target_url && (
                <div className="font-mono text-[11px] text-gray-600 break-all select-all">
                  Target: {iss.target_url} ({iss.lang || 'default'})
                </div>
              )}
            </div>
          ))}
        </div>
      );

    case 'structured_data':
      const sdList = data?.structured_data || [];
      return sdList.length === 0 ? (
        <div className="text-gray-400 py-4 text-center">No Schema / Structured Data detected on this page.</div>
      ) : (
        <div className="space-y-3">
          {sdList.map((sd: any, idx: number) => (
            <div key={idx} className="border border-[#C8B670] p-2.5 bg-[#FFF7D6]/20 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-black">
                  Schema Type: <code className="bg-white px-1.5 py-0.5 border border-[#C8B670]">{sd.schema_type}</code>
                </span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 border ${
                  sd.is_valid
                    ? 'bg-[#dcfce7] text-[#15803d] border-[#86efac]'
                    : 'bg-[#fee2e2] text-[#b91c1c] border-[#fca5a5]'
                }`}>
                  {sd.is_valid ? 'Valid JSON-LD' : 'Schema Error'}
                </span>
              </div>
              <pre className="bg-white p-2 border border-[#E2D5A0] text-[11px] font-mono overflow-auto max-h-40 select-all">
                {typeof sd.data_json === 'string' ? sd.data_json : JSON.stringify(sd.data_json, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      );

    case 'inlinks':
      const inlinks = data?.inlinks || [];
      return inlinks.length === 0 ? (
        <div className="text-gray-400 py-4 text-center">No inlinks recorded for this URL.</div>
      ) : (
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-[#FFF7D6] border-b border-[#C8B670] font-bold">
              <th className="p-1.5 border-r border-[#C8B670]">Source URL</th>
              <th className="p-1.5 border-r border-[#C8B670]">Anchor Text</th>
              <th className="p-1.5 border-r border-[#C8B670] text-center w-16">Status</th>
              <th className="p-1.5 text-center w-20">Nofollow</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E2D5A0]">
            {inlinks.map((link: any, i: number) => (
              <tr key={i} className="hover:bg-[#FFF7D6]">
                <td className="p-1.5 border-r border-[#E2D5A0] font-mono break-all">{link.source_url}</td>
                <td className="p-1.5 border-r border-[#E2D5A0] font-medium">{link.anchor_text || '—'}</td>
                <td className="p-1.5 border-r border-[#E2D5A0] text-center font-bold text-[#15803d]">{link.status_code || 200}</td>
                <td className="p-1.5 text-center">{link.nofollow ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      );

    case 'outlinks':
      const outlinks = data?.outlinks || [];
      return outlinks.length === 0 ? (
        <div className="text-gray-400 py-4 text-center">No outlinks recorded for this URL.</div>
      ) : (
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-[#FFF7D6] border-b border-[#C8B670] font-bold">
              <th className="p-1.5 border-r border-[#C8B670]">Target Destination URL</th>
              <th className="p-1.5 border-r border-[#C8B670]">Anchor Text</th>
              <th className="p-1.5 border-r border-[#C8B670] text-center w-20">Type</th>
              <th className="p-1.5 text-center w-20">Nofollow</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E2D5A0]">
            {outlinks.map((link: any, i: number) => (
              <tr key={i} className="hover:bg-[#FFF7D6]">
                <td className="p-1.5 border-r border-[#E2D5A0] font-mono break-all">{link.target_url}</td>
                <td className="p-1.5 border-r border-[#E2D5A0] font-medium">{link.anchor_text || '—'}</td>
                <td className="p-1.5 border-r border-[#E2D5A0] text-center">{link.is_internal ? 'Internal' : 'External'}</td>
                <td className="p-1.5 text-center">{link.nofollow ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      );

    case 'headers':
      const headers = data?.headers || {};
      const entries = Object.entries(headers);
      return entries.length === 0 ? (
        <div className="text-gray-400 py-4 text-center">No HTTP headers cached.</div>
      ) : (
        <table className="w-full text-left border-collapse font-mono text-xs">
          <thead>
            <tr className="bg-[#FFF7D6] border-b border-[#C8B670] font-bold">
              <th className="p-1.5 border-r border-[#C8B670] w-64">Header Field</th>
              <th className="p-1.5">Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E2D5A0]">
            {entries.map(([k, v], i) => (
              <tr key={i} className="hover:bg-[#FFF7D6]">
                <td className="p-1.5 border-r border-[#E2D5A0] font-bold text-gray-700">{k}</td>
                <td className="p-1.5 break-all select-all">{String(v)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      );

    case 'issues':
      return <PageIssuesTab issues={data?.issues || []} />;

    default:
      return <div className="text-gray-400 py-4 text-center">Data loaded for {tab}.</div>;
  }
}

function PageIssuesTab({ issues }: { issues: any[] }) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  if (!issues || issues.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <CheckCircle className="w-8 h-8 text-[#15803d] mx-auto mb-2" />
        <p className="font-bold text-xs text-gray-800">No SEO Issues Found On This Page</p>
        <p className="text-[11px] text-gray-400 mt-1">Status code is 200 OK, essential on-page tags are present, and canonical is valid.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="text-[11px] font-bold text-gray-700 uppercase tracking-wider">
        Detected SEO Issues ({issues.length})
      </div>
      {issues.map((iss: any, i: number) => {
        const title = iss.title || iss.issue_name || iss.code || iss.issue_type || 'SEO Issue';
        const severity = (iss.severity || 'warning').toLowerCase();
        const isCritical = severity === 'critical';
        const isWarning = severity === 'warning' || severity === 'high';
        const howToFix = iss.how_to_fix || iss.recommendation || '';
        const codeSnippet = iss.code_snippet || '';
        const helpUrl = iss.help_url || '';

        return (
          <div
            key={i}
            className={`p-3 border rounded-xs space-y-2 ${
              isCritical
                ? 'border-[#fca5a5] bg-[#fff5f5]'
                : isWarning
                ? 'border-[#fde68a] bg-[#fffdf0]'
                : 'border-[#bfdbfe] bg-[#f8faff]'
            }`}
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <span className="font-bold text-black flex items-center gap-1.5 text-xs">
                <AlertTriangle
                  className={`w-4 h-4 ${
                    isCritical ? 'text-[#b91c1c]' : isWarning ? 'text-[#b45309]' : 'text-[#1d4ed8]'
                  }`}
                />
                {title}
              </span>
              <span
                className={`uppercase text-[10px] font-black px-2 py-0.5 rounded-xs tracking-wider ${
                  isCritical
                    ? 'bg-[#b91c1c] text-white'
                    : isWarning
                    ? 'bg-[#b45309] text-white'
                    : 'bg-[#1d4ed8] text-white'
                }`}
              >
                {isCritical ? 'CRITICAL' : isWarning ? 'WARNING' : 'NOTICE'}
              </span>
            </div>

            {/* Description */}
            {(iss.description || iss.message) && (
              <p className="text-gray-700 text-xs leading-relaxed">
                {iss.description || iss.message}
              </p>
            )}

            {/* Actionable Fix Box */}
            {(howToFix || codeSnippet) && (
              <div className="border border-[#C8B670] bg-[#FFF7D6] p-2.5 rounded-xs space-y-2 mt-2">
                <div className="flex items-center gap-1.5 font-bold text-xs text-black">
                  <Wrench className="w-3.5 h-3.5 text-[#b45309]" />
                  <span>Recommended Fix & Implementation:</span>
                </div>

                {howToFix && (
                  <div className="text-gray-800 text-[11px] leading-relaxed whitespace-pre-line font-medium pl-1 border-l-2 border-[#C8B670]">
                    {howToFix}
                  </div>
                )}

                {codeSnippet && (
                  <div className="mt-2 space-y-1">
                    <div className="flex items-center justify-between text-[10px] font-mono font-bold text-gray-600">
                      <span className="flex items-center gap-1">
                        <FileCode className="w-3 h-3" />
                        Code / Configuration Example:
                      </span>
                      <button
                        onClick={() => handleCopy(codeSnippet, `insp-code-${i}`)}
                        className="flex items-center gap-1 px-1.5 py-0.5 bg-white border border-[#C8B670] rounded-xs text-black hover:bg-black hover:text-white transition-colors"
                      >
                        {copiedKey === `insp-code-${i}` ? (
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
                      {codeSnippet}
                    </pre>
                  </div>
                )}

                {helpUrl && (
                  <div className="pt-1 flex items-center justify-end">
                    <a
                      href={helpUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[10px] font-bold text-black hover:underline"
                    >
                      <BookOpen className="w-3 h-3" />
                      Official Google Search Docs
                      <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
