import React, { useState } from 'react';
import { useCrawlStore } from '../../store/useCrawlStore';
import {
  Play,
  Square,
  Trash2,
  Settings,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Code,
  Network,
  GitCompare,
  Download,
  ChevronDown
} from 'lucide-react';
import { CompareModal } from '../modals/CompareModal';
import { VisualizerModal } from '../modals/VisualizerModal';
import { CustomRulesModal } from '../modals/CustomRulesModal';

export const SpiderHeader: React.FC = () => {
  const {
    auditId,
    startUrl,
    setStartUrl,
    mode,
    setMode,
    sitemapsText,
    setSitemapsText,
    concurrency,
    setConcurrency,
    maxPages,
    setMaxPages,
    renderingMode,
    setRenderingMode,
    customExtractors,
    customSearchRules,
    setIsCompareOpen,
    setIsVisualizerOpen,
    setIsCustomRulesOpen,
    startCrawl,
    stopCrawl,
    clearAll,
    progress,
    elapsedSeconds,
  } = useCrawlStore();

  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [isSitemapModalOpen, setIsSitemapModalOpen] = useState(false);
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);

  const isCrawling =
    progress.status === 'crawling' ||
    progress.status === 'analyzing' ||
    progress.status === 'analyzing_deep';

  const formatTimer = (sec: number) => {
    const m = String(Math.floor(sec / 60)).padStart(2, '0');
    const s = String(sec % 60).padStart(2, '0');
    return `${m}:${s}`;
  };

  const calculatePct = () => {
    if (progress.status === 'complete') return 100;
    if (progress.status === 'analyzing' || progress.status === 'analyzing_deep') return 95;
    if (!progress.max_pages || progress.max_pages === 0) return 0;
    return Math.min(100, Math.round((progress.crawled / progress.max_pages) * 100));
  };

  const getStatusBadge = () => {
    switch (progress.status) {
      case 'crawling':
        return (
          <span className="flex items-center gap-1.5 px-2 py-0.5 bg-[#FFE08A] text-black font-bold text-xs border border-[#C8B670]">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-black" />
            CRAWLING {progress.max_pages > 0 ? `(${calculatePct()}%)` : ''}
          </span>
        );
      case 'analyzing':
      case 'analyzing_deep':
        return (
          <span className="flex items-center gap-1.5 px-2 py-0.5 bg-[#FFF7D6] text-black font-bold text-xs border border-[#C8B670]">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-black" />
            ANALYZING...
          </span>
        );
      case 'complete':
        return (
          <span className="flex items-center gap-1.5 px-2 py-0.5 bg-[#dcfce7] text-[#15803d] font-bold text-xs border border-[#86efac]">
            <CheckCircle2 className="w-3.5 h-3.5" />
            COMPLETE (100%)
          </span>
        );
      case 'stopped':
        return (
          <span className="px-2 py-0.5 bg-[#fef3c7] text-[#b45309] font-bold text-xs border border-[#fde68a]">
            STOPPED
          </span>
        );
      case 'error':
        return (
          <span className="flex items-center gap-1.5 px-2 py-0.5 bg-[#fee2e2] text-[#b91c1c] font-bold text-xs border border-[#fca5a5]">
            <AlertCircle className="w-3.5 h-3.5" />
            ERROR
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 bg-white text-gray-600 font-medium text-xs border border-[#C8B670]">
            READY
          </span>
        );
    }
  };

  const totalCustomRules = customExtractors.length + customSearchRules.length;

  return (
    <header className="bg-[#FFF7D6] border-b border-[#C8B670] select-none text-black relative z-40">
      {/* Top Controls Row */}
      <div className="flex items-center justify-between px-3 py-1.5 gap-2">
        {/* App Title & URL Bar */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <a href="/" className="flex items-center shrink-0 select-none no-underline mr-1" title="VAPLERS">
            <span
              className="text-2xl tracking-wider uppercase leading-none font-normal"
              style={{ fontFamily: "'Bungee Shade', cursive", color: '#000000' }}
            >
              VAPLERS
            </span>
          </a>

          {/* Mode Switcher */}
          <div className="flex items-center border border-[#C8B670] bg-white text-xs shrink-0">
            <button
              onClick={() => setMode('spider')}
              className={`px-2.5 py-1 font-medium transition-colors ${
                mode === 'spider' ? 'bg-[#FFE08A] font-bold text-black' : 'text-gray-600 hover:bg-[#FFF7D6]'
              }`}
            >
              Full Spider
            </button>
            <button
              onClick={() => {
                setMode('sitemaps');
                setIsSitemapModalOpen(true);
              }}
              className={`px-2.5 py-1 font-medium transition-colors border-l border-[#C8B670] flex items-center gap-1 ${
                mode === 'sitemaps' ? 'bg-[#FFE08A] font-bold text-black' : 'text-gray-600 hover:bg-[#FFF7D6]'
              }`}
            >
              <FileText className="w-3 h-3" />
              Sitemap Only
              {sitemapsText.trim() && (
                <span className="ml-1 text-[10px] bg-black text-white px-1 rounded-full">
                  {sitemapsText.split('\n').filter(Boolean).length}
                </span>
              )}
            </button>
          </div>

          {/* Target URL Input */}
          <div className="flex items-center flex-1 max-w-xl border border-[#C8B670] bg-white">
            <span className="px-2.5 text-xs text-gray-500 font-medium border-r border-[#E2D5A0] bg-[#FFF7D6] py-1 shrink-0">
              Target
            </span>
            <input
              type="text"
              value={startUrl}
              onChange={(e) => setStartUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !isCrawling && startCrawl()}
              placeholder="https://example.com"
              disabled={isCrawling}
              className="w-full px-2.5 py-1 text-xs outline-none text-black font-medium disabled:bg-gray-100"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-1 shrink-0">
            {!isCrawling ? (
              <button
                onClick={startCrawl}
                disabled={!startUrl.trim()}
                className="flex items-center gap-1 px-3 py-1 bg-black text-white text-xs font-bold hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors border border-black shadow-sm"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                Start
              </button>
            ) : (
              <button
                onClick={stopCrawl}
                className="flex items-center gap-1 px-3 py-1 bg-[#b91c1c] text-white text-xs font-bold hover:bg-[#991b1b] transition-colors border border-[#7f1d1d] shadow-sm animate-pulse"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                Stop
              </button>
            )}

            {/* Custom Rules Button */}
            <button
              onClick={() => setIsCustomRulesOpen(true)}
              title="Custom Extraction & Custom Search"
              className="px-2 py-1 bg-white hover:bg-[#FFE08A] border border-[#C8B670] text-xs font-medium flex items-center gap-1 transition-colors"
            >
              <Code className="w-3.5 h-3.5 text-gray-700" />
              <span>Custom Rules</span>
              {totalCustomRules > 0 && (
                <span className="bg-black text-white text-[10px] px-1 font-bold rounded-full">
                  {totalCustomRules}
                </span>
              )}
            </button>

            {/* Visualizations Button */}
            <button
              onClick={() => setIsVisualizerOpen(true)}
              title="Site Architecture & Visualizations"
              disabled={!auditId}
              className="px-2 py-1 bg-white hover:bg-[#FFE08A] border border-[#C8B670] text-xs font-medium flex items-center gap-1 transition-colors disabled:opacity-40"
            >
              <Network className="w-3.5 h-3.5 text-gray-700" />
              <span>Visualizations</span>
            </button>

            {/* Compare Button */}
            <button
              onClick={() => setIsCompareOpen(true)}
              title="Crawl Comparison & Migration Diffs"
              className="px-2 py-1 bg-white hover:bg-[#FFE08A] border border-[#C8B670] text-xs font-medium flex items-center gap-1 transition-colors"
            >
              <GitCompare className="w-3.5 h-3.5 text-gray-700" />
              <span>Compare</span>
            </button>

            {/* Bulk Export Dropdown */}
            <div className="relative">
              <button
                onClick={() => setIsExportMenuOpen(!isExportMenuOpen)}
                disabled={!auditId}
                title="Bulk Relational Exports & Sitemap"
                className="px-2 py-1 bg-white hover:bg-[#FFE08A] border border-[#C8B670] text-xs font-medium flex items-center gap-1 transition-colors disabled:opacity-40"
              >
                <Download className="w-3.5 h-3.5 text-gray-700" />
                <span>Export</span>
                <ChevronDown className="w-3 h-3 text-gray-500" />
              </button>

              {isExportMenuOpen && auditId && (
                <div
                  className="absolute right-0 mt-1 w-56 bg-white border border-[#C8B670] shadow-xl text-xs z-50 py-1"
                  onClick={() => setIsExportMenuOpen(false)}
                >
                  <a
                    href={`/api/audit/${auditId}/export/sitemap.xml`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 px-3 py-1.5 hover:bg-[#FFF7D6] text-black font-medium"
                  >
                    <FileText className="w-3.5 h-3.5 text-[#15803d]" />
                    Export XML Sitemap
                  </a>
                  <div className="border-t border-[#E2D5A0] my-1" />
                  <a
                    href={`/api/audit/${auditId}/export/inlinks`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 px-3 py-1.5 hover:bg-[#FFF7D6] text-black"
                  >
                    <Download className="w-3.5 h-3.5 text-gray-600" />
                    All Inlinks (CSV)
                  </a>
                  <a
                    href={`/api/audit/${auditId}/export/outlinks`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 px-3 py-1.5 hover:bg-[#FFF7D6] text-black"
                  >
                    <Download className="w-3.5 h-3.5 text-gray-600" />
                    All Outlinks (CSV)
                  </a>
                  <a
                    href={`/api/audit/${auditId}/export/images`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 px-3 py-1.5 hover:bg-[#FFF7D6] text-black"
                  >
                    <Download className="w-3.5 h-3.5 text-gray-600" />
                    All Images & Alt Text (CSV)
                  </a>
                  <a
                    href={`/api/audit/${auditId}/export/redirect-chains`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 px-3 py-1.5 hover:bg-[#FFF7D6] text-black"
                  >
                    <Download className="w-3.5 h-3.5 text-gray-600" />
                    Redirect Chains (CSV)
                  </a>
                </div>
              )}
            </div>

            {/* Settings button */}
            <button
              onClick={() => setIsConfigOpen(!isConfigOpen)}
              title="Crawl Concurrency & Rendering Settings"
              className="p-1 hover:bg-[#FFE08A] border border-[#C8B670] bg-white transition-colors"
            >
              <Settings className="w-4 h-4 text-gray-700" />
            </button>

            {/* Clear All */}
            <button
              onClick={clearAll}
              title="Clear all stored audits & cache"
              disabled={isCrawling}
              className="p-1 hover:bg-[#fee2e2] hover:text-[#b91c1c] border border-[#C8B670] bg-white transition-colors disabled:opacity-40"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Live Metrics & Timer */}
        <div className="flex items-center gap-2 shrink-0">
          {progress.status !== 'idle' && (
            <div className="flex items-center gap-2 text-xs font-medium">
              <span className="font-mono text-gray-700">⏱ {formatTimer(elapsedSeconds)}</span>
              {progress.pages_per_sec > 0 && (
                <span className="text-[#15803d] font-bold">({progress.pages_per_sec}/s)</span>
              )}
              {progress.memory_mb > 0 && (
                <span className="text-gray-500 font-mono text-[11px]">{progress.memory_mb} MB</span>
              )}
            </div>
          )}
          {getStatusBadge()}
        </div>
      </div>

      {/* Progress Bar */}
      {progress.status !== 'idle' && (
        <div className="w-full bg-[#E2D5A0] h-1.5 overflow-hidden">
          {progress.max_pages === 0 ? (
            <div
              className={`h-full bg-black ${progress.status === 'crawling' ? 'progress-indeterminate w-full' : 'w-full'}`}
              style={{ width: progress.status === 'complete' ? '100%' : '100%' }}
            />
          ) : (
            <div
              className="h-full bg-black transition-all duration-300"
              style={{ width: `${calculatePct()}%` }}
            />
          )}
        </div>
      )}

      {/* Concurrency & Rendering Configuration Panel */}
      {isConfigOpen && (
        <div className="border-t border-[#C8B670] bg-white px-4 py-2.5 flex flex-wrap items-center gap-6 text-xs animate-in slide-in-from-top-1">
          {/* Threads */}
          <div className="flex items-center gap-2">
            <span className="font-bold text-gray-700">Threads:</span>
            {[5, 15, 30, 50, 100].map((t) => (
              <button
                key={t}
                onClick={() => setConcurrency(t)}
                className={`px-2 py-0.5 border ${
                  concurrency === t
                    ? 'bg-black text-white border-black font-bold'
                    : 'bg-[#FFF7D6] text-black border-[#C8B670] hover:bg-[#FFE08A]'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Max Pages Limit */}
          <div className="flex items-center gap-2">
            <span className="font-bold text-gray-700">Page Limit:</span>
            {[0, 50, 100, 500, 1000].map((lim) => (
              <button
                key={lim}
                onClick={() => setMaxPages(lim)}
                className={`px-2 py-0.5 border ${
                  maxPages === lim
                    ? 'bg-black text-white border-black font-bold'
                    : 'bg-[#FFF7D6] text-black border-[#C8B670] hover:bg-[#FFE08A]'
                }`}
              >
                {lim === 0 ? 'Unlimited' : lim}
              </button>
            ))}
          </div>

          {/* Rendering Mode */}
          <div className="flex items-center gap-2">
            <span className="font-bold text-gray-700">Rendering Engine:</span>
            <button
              onClick={() => setRenderingMode('text')}
              className={`px-2.5 py-0.5 border ${
                renderingMode === 'text'
                  ? 'bg-black text-white border-black font-bold'
                  : 'bg-[#FFF7D6] text-black border-[#C8B670] hover:bg-[#FFE08A]'
              }`}
            >
              Text Only (Ultra-Fast)
            </button>
            <button
              onClick={() => setRenderingMode('javascript')}
              className={`px-2.5 py-0.5 border ${
                renderingMode === 'javascript'
                  ? 'bg-black text-white border-black font-bold'
                  : 'bg-[#FFF7D6] text-black border-[#C8B670] hover:bg-[#FFE08A]'
              }`}
            >
              JavaScript (Playwright Chromium)
            </button>
          </div>
        </div>
      )}

      {/* Multi-Sitemap Modal */}
      {isSitemapModalOpen && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white border-2 border-[#C8B670] shadow-xl w-full max-w-lg p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-[#E2D5A0] pb-2">
              <h3 className="font-bold text-sm text-black flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-[#b45309]" />
                Sitemap URLs (1 or more from same domain)
              </h3>
              <button
                onClick={() => setIsSitemapModalOpen(false)}
                className="text-gray-400 hover:text-black font-bold"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-gray-600">
              Enter one sitemap URL per line. The spider will strictly crawl and audit only URLs discovered in these sitemaps.
            </p>
            <textarea
              rows={5}
              value={sitemapsText}
              onChange={(e) => setSitemapsText(e.target.value)}
              placeholder="https://example.com/sitemap.xml&#10;https://example.com/sitemap-products.xml"
              className="w-full border border-[#C8B670] p-2 text-xs font-mono outline-none focus:border-black"
            />
            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={() => setIsSitemapModalOpen(false)}
                className="px-4 py-1.5 bg-black text-white text-xs font-bold hover:bg-neutral-800"
              >
                Save & Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Global Modals */}
      <CompareModal />
      <VisualizerModal />
      <CustomRulesModal />
    </header>
  );
};
