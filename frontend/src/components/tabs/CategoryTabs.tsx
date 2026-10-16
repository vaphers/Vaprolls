import React from 'react';
import { useCrawlStore } from '../../store/useCrawlStore';
import { TAB_SCHEMAS } from '../table/columnSchemas';
import { Search, Download, X } from 'lucide-react';

export const CategoryTabs: React.FC = () => {
  const {
    currentTab,
    switchTab,
    rows,
    filteredRows,
    searchTerm,
    setSearchTerm,
    includeRegex,
    setIncludeRegex,
    excludeRegex,
    setExcludeRegex,
    contentTypeFilter,
    setContentTypeFilter,
    columnPreset,
    setColumnPreset,
  } = useCrawlStore();

  const handleExportCsv = () => {
    if (filteredRows.length === 0) {
      alert("No matching URLs to export.");
      return;
    }

    const schema = TAB_SCHEMAS[currentTab] || TAB_SCHEMAS.all;
    const columns = schema.columns;

    const headers = columns.map(c => `"${c.label.replace(/"/g, '""')}"`);
    const csvRows = filteredRows.map((r, idx) => {
      return columns.map(c => {
        let val: any;
        if (c.key === 'row') val = idx + 1;
        else if (c.key === 'length') val = r.size_bytes || r.length || 0;
        else val = r[c.key] !== undefined && r[c.key] !== null ? r[c.key] : '';
        return `"${String(val).replace(/"/g, '""')}"`;
      }).join(',');
    });

    const csvContent = "\uFEFF" + [headers.join(','), ...csvRows].join("\r\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
    link.href = url;
    link.download = `audit_${currentTab}_${timestamp}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-[#FFF7D6] border-b border-[#C8B670] select-none text-black">
      {/* 1. Category Tabs Bar */}
      <div className="flex items-center overflow-x-auto no-scrollbar border-b border-[#E2D5A0] bg-[#FFF7D6] px-1 text-xs">
        {Object.entries(TAB_SCHEMAS).map(([key, schema]) => {
          const isActive = currentTab === key;
          return (
            <button
              key={key}
              onClick={() => switchTab(key)}
              className={`px-3 py-1.5 whitespace-nowrap font-medium text-xs border-b-2 transition-all flex items-center gap-1 ${
                isActive
                  ? 'border-b-[#000000] bg-[#FFE08A] font-bold text-black'
                  : 'border-b-transparent text-gray-700 hover:bg-[#FFE08A]/50'
              }`}
            >
              <span>{schema.label}</span>
              {isActive && (
                <span className="text-[10px] opacity-75 font-normal">
                  ({filteredRows.length})
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* 2. Secondary Filter & Search Toolbar */}
      <div className="flex flex-wrap items-center justify-between px-3 py-1 gap-2 text-xs bg-white border-b border-[#E2D5A0]">
        {/* Left Filter Controls */}
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          {/* Quick Search */}
          <div className="flex items-center border border-[#C8B670] bg-white px-2 py-0.5 w-44">
            <Search className="w-3.5 h-3.5 text-gray-400 mr-1.5 shrink-0" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search in table..."
              className="w-full text-xs outline-none bg-transparent"
            />
            {searchTerm && (
              <button onClick={() => setSearchTerm('')} className="text-gray-400 hover:text-black">
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Include Regex Filter */}
          <div className="flex items-center border border-[#C8B670] bg-white px-2 py-0.5 w-40">
            <span className="text-[10px] text-gray-400 mr-1 font-mono">inc:</span>
            <input
              type="text"
              value={includeRegex}
              onChange={(e) => setIncludeRegex(e.target.value)}
              placeholder="Regex match..."
              className="w-full text-xs outline-none bg-transparent font-mono"
            />
            {includeRegex && (
              <button onClick={() => setIncludeRegex('')} className="text-gray-400 hover:text-black">
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Exclude Regex Filter */}
          <div className="flex items-center border border-[#C8B670] bg-white px-2 py-0.5 w-40">
            <span className="text-[10px] text-gray-400 mr-1 font-mono">exc:</span>
            <input
              type="text"
              value={excludeRegex}
              onChange={(e) => setExcludeRegex(e.target.value)}
              placeholder="Regex exclude..."
              className="w-full text-xs outline-none bg-transparent font-mono"
            />
            {excludeRegex && (
              <button onClick={() => setExcludeRegex('')} className="text-gray-400 hover:text-black">
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Content Type Selector */}
          <select
            value={contentTypeFilter}
            onChange={(e) => setContentTypeFilter(e.target.value)}
            className="border border-[#C8B670] bg-white px-2 py-0.5 text-xs outline-none font-medium text-black cursor-pointer"
          >
            <option value="all">Content: All Types</option>
            <option value="text/html">HTML Only</option>
            <option value="image">Images Only</option>
            <option value="javascript">JavaScript Only</option>
            <option value="css">CSS Only</option>
            <option value="pdf">PDF Only</option>
          </select>

          {/* Column Presets */}
          <select
            value={columnPreset}
            onChange={(e) => setColumnPreset(e.target.value)}
            className="border border-[#C8B670] bg-white px-2 py-0.5 text-xs outline-none font-medium text-black cursor-pointer"
          >
            <option value="all">Columns: All Standard</option>
            <option value="seo_basics">Columns: SEO Basics</option>
            <option value="technical">Columns: Technical</option>
            <option value="link_equity">Columns: Link Equity</option>
            <option value="content">Columns: Content Quality</option>
          </select>
        </div>

        {/* Right Status & Export */}
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-gray-600 font-medium">
            Showing <strong className="text-black">{filteredRows.length}</strong> of{' '}
            <strong className="text-black">{rows.length}</strong> URLs
          </span>

          <button
            onClick={handleExportCsv}
            className="flex items-center gap-1 px-2.5 py-0.5 bg-white border border-[#C8B670] hover:bg-[#FFE08A] text-xs font-semibold text-black transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </button>
        </div>
      </div>
    </div>
  );
};
