import React, { useState, useEffect } from 'react';
import { useCrawlStore } from '../../store/useCrawlStore';
import { api } from '../../services/api';
import type { AuditListItem, ComparisonDiff } from '../../types';
import { GitCompare, X, PlusCircle, MinusCircle, Loader2 } from 'lucide-react';

export const CompareModal: React.FC = () => {
  const { isCompareOpen, setIsCompareOpen, auditId } = useCrawlStore();
  const [audits, setAudits] = useState<AuditListItem[]>([]);
  const [baseId, setBaseId] = useState<string>('');
  const [compareId, setCompareId] = useState<string>('');
  const [comparing, setComparing] = useState(false);
  const [diff, setDiff] = useState<ComparisonDiff | null>(null);
  const [activeTab, setActiveTab] = useState<'summary' | 'added' | 'removed' | 'status' | 'titles' | 'canonicals'>('summary');

  useEffect(() => {
    if (isCompareOpen) {
      loadAudits();
    }
  }, [isCompareOpen]);

  const loadAudits = async () => {
    try {
      const list = await api.listAudits();
      setAudits(list);
      if (list.length >= 2) {
        setBaseId(auditId || list[1]?.id || list[0]?.id || '');
        setCompareId(list[0]?.id || '');
      } else if (list.length === 1) {
        setBaseId(list[0].id);
        setCompareId(list[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCompare = async () => {
    if (!baseId || !compareId) return;
    setComparing(true);
    try {
      const res = await api.compareAudits(baseId, compareId);
      setDiff(res);
      setActiveTab('summary');
    } catch (err) {
      alert("Failed to compare audits. Ensure both audits have completed crawls.");
    } finally {
      setComparing(false);
    }
  };

  if (!isCompareOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white border-2 border-[#C8B670] shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden text-black">
        {/* Header */}
        <div className="bg-[#FFE08A] border-b border-[#C8B670] px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-black" />
            <h2 className="font-bold text-sm text-black">Crawl Comparison & Migration Diffs</h2>
          </div>
          <button
            onClick={() => setIsCompareOpen(false)}
            className="p-1 hover:bg-[#FFF7D6] text-black font-bold"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Audit Selectors */}
        <div className="bg-[#FFF7D6] p-3 border-b border-[#E2D5A0] flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-2">
            <label className="font-bold text-gray-700">Base Audit (A):</label>
            <select
              value={baseId}
              onChange={(e) => setBaseId(e.target.value)}
              className="border border-[#C8B670] bg-white px-2 py-1 outline-none text-xs font-mono max-w-xs"
            >
              {audits.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.domain || a.url} ({a.total_pages} URLs) - {a.created_at?.slice(0, 16)}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="font-bold text-gray-700">Compare Audit (B):</label>
            <select
              value={compareId}
              onChange={(e) => setCompareId(e.target.value)}
              className="border border-[#C8B670] bg-white px-2 py-1 outline-none text-xs font-mono max-w-xs"
            >
              {audits.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.domain || a.url} ({a.total_pages} URLs) - {a.created_at?.slice(0, 16)}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleCompare}
            disabled={comparing || !baseId || !compareId || baseId === compareId}
            className="px-4 py-1 bg-black text-white font-bold hover:bg-neutral-800 disabled:opacity-40 transition-colors flex items-center gap-1.5 ml-auto"
          >
            {comparing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <GitCompare className="w-3.5 h-3.5" />}
            Run Diff
          </button>
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-hidden flex flex-col bg-white">
          {diff ? (
            <>
              {/* Tab navigation */}
              <div className="flex items-center border-b border-[#E2D5A0] bg-[#FFF7D6] px-2 text-xs">
                <button
                  onClick={() => setActiveTab('summary')}
                  className={`px-3 py-1.5 font-bold border-b-2 ${activeTab === 'summary' ? 'border-b-black bg-white' : 'border-b-transparent text-gray-600'}`}
                >
                  Summary
                </button>
                <button
                  onClick={() => setActiveTab('added')}
                  className={`px-3 py-1.5 font-bold border-b-2 ${activeTab === 'added' ? 'border-b-black bg-white text-[#15803d]' : 'border-b-transparent text-gray-600'}`}
                >
                  Added URLs ({diff.added_urls?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab('removed')}
                  className={`px-3 py-1.5 font-bold border-b-2 ${activeTab === 'removed' ? 'border-b-black bg-white text-[#b91c1c]' : 'border-b-transparent text-gray-600'}`}
                >
                  Removed URLs ({diff.removed_urls?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab('status')}
                  className={`px-3 py-1.5 font-bold border-b-2 ${activeTab === 'status' ? 'border-b-black bg-white' : 'border-b-transparent text-gray-600'}`}
                >
                  Status Code Diffs ({diff.status_changes?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab('titles')}
                  className={`px-3 py-1.5 font-bold border-b-2 ${activeTab === 'titles' ? 'border-b-black bg-white' : 'border-b-transparent text-gray-600'}`}
                >
                  Title Changes ({diff.title_changes?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab('canonicals')}
                  className={`px-3 py-1.5 font-bold border-b-2 ${activeTab === 'canonicals' ? 'border-b-black bg-white' : 'border-b-transparent text-gray-600'}`}
                >
                  Canonical Diffs ({diff.canonical_changes?.length || 0})
                </button>
              </div>

              {/* Tab views */}
              <div className="flex-1 overflow-auto p-4 text-xs">
                {activeTab === 'summary' && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-3 border border-[#C8B670] bg-[#FFF7D6]">
                      <div className="text-gray-600 text-[11px] uppercase font-bold">Total URLs (Base A)</div>
                      <div className="text-xl font-bold font-mono mt-1">{diff.summary.base_total}</div>
                    </div>
                    <div className="p-3 border border-[#C8B670] bg-[#FFF7D6]">
                      <div className="text-gray-600 text-[11px] uppercase font-bold">Total URLs (Compare B)</div>
                      <div className="text-xl font-bold font-mono mt-1">{diff.summary.compare_total}</div>
                    </div>
                    <div className="p-3 border border-[#86efac] bg-[#dcfce7]">
                      <div className="text-[#15803d] text-[11px] uppercase font-bold flex items-center gap-1">
                        <PlusCircle className="w-3.5 h-3.5" /> Added URLs
                      </div>
                      <div className="text-xl font-bold font-mono text-[#15803d] mt-1">+{diff.summary.added_urls_count}</div>
                    </div>
                    <div className="p-3 border border-[#fca5a5] bg-[#fee2e2]">
                      <div className="text-[#b91c1c] text-[11px] uppercase font-bold flex items-center gap-1">
                        <MinusCircle className="w-3.5 h-3.5" /> Removed URLs
                      </div>
                      <div className="text-xl font-bold font-mono text-[#b91c1c] mt-1">-{diff.summary.removed_urls_count}</div>
                    </div>
                    <div className="p-3 border border-[#C8B670] bg-white">
                      <div className="text-gray-600 text-[11px] uppercase font-bold">Status Code Changes</div>
                      <div className="text-xl font-bold font-mono mt-1">{diff.summary.status_changed_count}</div>
                    </div>
                    <div className="p-3 border border-[#C8B670] bg-white">
                      <div className="text-gray-600 text-[11px] uppercase font-bold">Page Title Changes</div>
                      <div className="text-xl font-bold font-mono mt-1">{diff.summary.title_changed_count}</div>
                    </div>
                    <div className="p-3 border border-[#C8B670] bg-white">
                      <div className="text-gray-600 text-[11px] uppercase font-bold">Canonical Changes</div>
                      <div className="text-xl font-bold font-mono mt-1">{diff.summary.canonical_changed_count}</div>
                    </div>
                  </div>
                )}

                {activeTab === 'added' && (
                  <div className="space-y-1">
                    {diff.added_urls?.length === 0 ? (
                      <div className="text-gray-400 py-6 text-center">No new URLs added in Compare Audit B.</div>
                    ) : (
                      diff.added_urls.map((u, i) => (
                        <div key={i} className="p-2 border border-[#86efac] bg-[#dcfce7]/40 font-mono text-xs text-[#15803d] break-all select-all">
                          + {u}
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'removed' && (
                  <div className="space-y-1">
                    {diff.removed_urls?.length === 0 ? (
                      <div className="text-gray-400 py-6 text-center">No URLs removed from Base Audit A.</div>
                    ) : (
                      diff.removed_urls.map((u, i) => (
                        <div key={i} className="p-2 border border-[#fca5a5] bg-[#fee2e2]/40 font-mono text-xs text-[#b91c1c] break-all select-all">
                          - {u}
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'status' && (
                  <div className="space-y-2">
                    {diff.status_changes?.length === 0 ? (
                      <div className="text-gray-400 py-6 text-center">No status code changes detected.</div>
                    ) : (
                      <table className="w-full text-left border-collapse font-mono text-xs">
                        <thead>
                          <tr className="bg-[#FFF7D6] border-b border-[#C8B670] font-bold">
                            <th className="p-2 border-r border-[#C8B670]">Address</th>
                            <th className="p-2 border-r border-[#C8B670] w-24 text-center">Base Status</th>
                            <th className="p-2 w-28 text-center">Compare Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#E2D5A0]">
                          {diff.status_changes.map((sc, i) => (
                            <tr key={i} className="hover:bg-[#FFF7D6]">
                              <td className="p-2 border-r border-[#E2D5A0] break-all select-all">{sc.url}</td>
                              <td className="p-2 border-r border-[#E2D5A0] text-center font-bold">{sc.base_status}</td>
                              <td className="p-2 text-center font-bold text-[#b91c1c]">{sc.compare_status}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}

                {activeTab === 'titles' && (
                  <div className="space-y-3">
                    {diff.title_changes?.length === 0 ? (
                      <div className="text-gray-400 py-6 text-center">No page title changes detected.</div>
                    ) : (
                      diff.title_changes.map((tc, i) => (
                        <div key={i} className="p-2.5 border border-[#C8B670] bg-[#FFF7D6]/30 space-y-1">
                          <div className="font-mono text-xs font-bold text-gray-800 break-all">{tc.url}</div>
                          <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                            <div className="p-1.5 bg-[#fee2e2]/50 border border-[#fca5a5]">
                              <span className="font-bold text-[10px] text-[#b91c1c] uppercase block">Base Title</span>
                              {tc.base_title || '—'}
                            </div>
                            <div className="p-1.5 bg-[#dcfce7]/50 border border-[#86efac]">
                              <span className="font-bold text-[10px] text-[#15803d] uppercase block">Compare Title</span>
                              {tc.compare_title || '—'}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'canonicals' && (
                  <div className="space-y-3">
                    {diff.canonical_changes?.length === 0 ? (
                      <div className="text-gray-400 py-6 text-center">No canonical URL changes detected.</div>
                    ) : (
                      diff.canonical_changes.map((cc, i) => (
                        <div key={i} className="p-2.5 border border-[#C8B670] bg-[#FFF7D6]/30 space-y-1">
                          <div className="font-mono text-xs font-bold text-gray-800 break-all">{cc.url}</div>
                          <div className="grid grid-cols-2 gap-2 font-mono text-xs pt-1">
                            <div className="p-1.5 bg-gray-50 border border-gray-200 break-all">
                              <span className="font-bold text-[10px] text-gray-500 uppercase block font-sans">Base Canonical</span>
                              {cc.base_canonical || '—'}
                            </div>
                            <div className="p-1.5 bg-yellow-50 border border-yellow-200 break-all">
                              <span className="font-bold text-[10px] text-yellow-800 uppercase block font-sans">Compare Canonical</span>
                              {cc.compare_canonical || '—'}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-gray-500">
              <GitCompare className="w-12 h-12 text-[#C8B670] mb-2" />
              <p className="font-bold text-black mb-1">Select two crawl audits above and click "Run Diff"</p>
              <p className="text-xs max-w-md">
                Compare Audits calculates added and removed URLs, status code alterations, canonical flips, and title changes between two crawls of your website.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
