import React, { useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useCrawlStore } from '../../store/useCrawlStore';
import { TAB_SCHEMAS, COLUMN_PRESETS } from './columnSchemas';
import { ExternalLink, ArrowUp, ArrowDown } from 'lucide-react';

const ROW_HEIGHT = 28;

export const MasterTable: React.FC = () => {
  const {
    currentTab,
    filteredRows,
    selectedPageId,
    selectPage,
    sortBy,
    sortDir,
    setSort,
    columnPreset,
    columnWidths,
    setColumnWidth,
    progress,
  } = useCrawlStore();

  const [parentEl, setParentEl] = useState<HTMLDivElement | null>(null);

  // Column resizing state
  const [resizingCol, setResizingCol] = useState<{ key: string; startX: number; startWidth: number } | null>(null);

  const schema = TAB_SCHEMAS[currentTab] || TAB_SCHEMAS.all;
  const activePreset = COLUMN_PRESETS[columnPreset];

  // Filter columns based on active preset
  const visibleColumns = schema.columns.filter(
    (c) => c.key === 'row' || !activePreset || activePreset.includes(c.key)
  );

  const rowVirtualizer = useVirtualizer({
    count: filteredRows.length,
    getScrollElement: () => parentEl,
    estimateSize: () => ROW_HEIGHT,
    overscan: 20,
  });

  const getColWidth = (colKey: string, defaultWidth: number) => {
    return columnWidths[colKey] || defaultWidth;
  };

  // Start Resizing Column
  const onMouseDownResizer = (e: React.MouseEvent, colKey: string, currentWidth: number) => {
    e.preventDefault();
    e.stopPropagation();
    setResizingCol({ key: colKey, startX: e.pageX, startWidth: currentWidth });

    const onMouseMove = (moveEvent: MouseEvent) => {
      const diff = moveEvent.pageX - e.pageX;
      const newWidth = Math.max(50, currentWidth + diff);
      setColumnWidth(colKey, newWidth);
    };

    const onMouseUp = () => {
      setResizingCol(null);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  const formatStatusCode = (code: number) => {
    if (!code) return <span className="status-pill-other">—</span>;
    if (code === 200) return <span className="status-pill-200">200</span>;
    if (code >= 300 && code < 400) return <span className="status-pill-3xx">{code}</span>;
    if (code >= 400) return <span className="status-pill-4xx">{code}</span>;
    return <span className="status-pill-other">{code}</span>;
  };

  const formatBytes = (bytes?: number) => {
    if (!bytes || isNaN(bytes)) return '0 KB';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(2)} MB`;
  };

  const formatSeconds = (ms?: number) => {
    if (!ms || isNaN(ms)) return '0.00s';
    const sec = ms > 10 ? ms / 1000 : ms;
    return `${sec.toFixed(2)}s`;
  };

  // Render cell content based on column key
  const renderCellContent = (row: any, colKey: string, idx: number) => {
    switch (colKey) {
      case 'row':
        return <span className="font-bold tabular-nums text-black">{idx + 1}</span>;

      case 'url':
        return (
          <div className="flex items-center gap-1.5 whitespace-nowrap overflow-hidden">
            <a
              href={row.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-gray-400 hover:text-black shrink-0"
              title="Open link in new browser tab"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <span className="truncate select-all text-[12px] font-normal text-black" title={row.url}>
              {row.url}
            </span>
          </div>
        );

      case 'status_code':
        return formatStatusCode(row.status_code);

      case 'indexability':
        return (
          <span
            className={`px-1.5 py-0.5 text-[11px] font-bold ${
              row.indexability === 'Indexable'
                ? 'bg-[#dcfce7] text-[#15803d]'
                : 'bg-[#fef3c7] text-[#b45309]'
            }`}
          >
            {row.indexability || '—'}
          </span>
        );

      case 'canonical_status':
        if (row.canonical_status === 'Self-Referential') {
          return <span className="status-pill-200">Self-Referential</span>;
        }
        if (row.canonical_status === 'Canonicalised') {
          return <span className="status-pill-3xx">Canonicalised</span>;
        }
        return <span className="text-gray-400">—</span>;

      case 'size_bytes':
      case 'length':
        return <span className="font-mono text-black">{formatBytes(row.size_bytes || row.length)}</span>;

      case 'response_time':
        return <span className="font-mono text-black">{formatSeconds(row.response_time || row.response_time_ms)}</span>;

      default:
        const val = row[colKey];
        if (val === undefined || val === null || val === '') return <span className="text-gray-400">—</span>;
        return <span className="truncate block" title={String(val)}>{String(val)}</span>;
    }
  };

  const isCrawling = progress.status === 'crawling' || progress.status === 'analyzing' || progress.status === 'analyzing_deep';
  const totalTableWidth = visibleColumns.reduce((sum, c) => sum + getColWidth(c.key, c.defaultWidth), 0);

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-white select-none">
      {/* Scrollable Virtual Table Viewport */}
      <div ref={setParentEl} className="flex-1 min-h-0 overflow-auto relative">
        <div style={{ width: Math.max(totalTableWidth, 1100), minWidth: '100%' }}>
          {/* Sticky Table Header */}
          <div className="sticky top-0 z-10 flex bg-[#FFE08A] border-b border-[#C8B670] text-xs font-bold uppercase text-black tracking-wider">
            {visibleColumns.map((col) => {
              const width = getColWidth(col.key, col.defaultWidth);
              const isSorted = sortBy === col.key;
              const align = col.align === 'text-center' ? 'justify-center' : col.align === 'text-right' ? 'justify-end' : 'justify-start';

              return (
                <div
                  key={col.key}
                  style={{ width, minWidth: width, maxWidth: width }}
                  onClick={() => col.key !== 'row' && setSort(col.key)}
                  className={`relative flex items-center px-2 py-1.5 border-r border-[#C8B670] hover:bg-[#FFD76A] cursor-pointer transition-colors ${align}`}
                >
                  <span className="truncate">{col.label}</span>
                  {isSorted && (
                    <span className="ml-1 shrink-0">
                      {sortDir === 'asc' ? <ArrowUp className="w-3 h-3 inline" /> : <ArrowDown className="w-3 h-3 inline" />}
                    </span>
                  )}
                  {/* Resizer Handle */}
                  <div
                    onMouseDown={(e) => onMouseDownResizer(e, col.key, width)}
                    className={`col-resizer ${resizingCol?.key === col.key ? 'is-resizing' : ''}`}
                  />
                </div>
              );
            })}
          </div>

          {/* Table Rows or In-Table Status */}
          {filteredRows.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
              {isCrawling ? (
                <div className="flex items-center gap-2 text-xs font-semibold text-gray-800">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-ping inline-block" />
                  Crawling target website... Discovered URLs will appear here in real time.
                </div>
              ) : (
                <>
                  <h3 className="font-bold text-sm text-black mb-1">Ready to Crawl</h3>
                  <p className="text-xs text-gray-500 max-w-md">
                    Enter a website URL in the top bar above and click <strong>Start</strong> to begin real-time crawling.
                  </p>
                </>
              )}
            </div>
          ) : (
            <div
              style={{
                height: `${rowVirtualizer.getTotalSize()}px`,
                position: 'relative',
                width: '100%',
              }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const row = filteredRows[virtualRow.index];
                if (!row) return null;

                const isSelected = selectedPageId === row.id;

                return (
                  <div
                    key={virtualRow.key}
                    data-index={virtualRow.index}
                    onClick={() => selectPage(row.id)}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    className={`flex items-center text-xs border-b border-[#E2D5A0] cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-[#FFE08A] font-semibold'
                        : virtualRow.index % 2 === 0
                        ? 'bg-white hover:bg-[#FFF7D6]'
                        : 'bg-[#FCFBF7] hover:bg-[#FFF7D6]'
                    }`}
                  >
                    {visibleColumns.map((col) => {
                      const width = getColWidth(col.key, col.defaultWidth);
                      const align = col.align === 'text-center' ? 'text-center' : col.align === 'text-right' ? 'text-right' : 'text-left';

                      return (
                        <div
                          key={col.key}
                          style={{ width, minWidth: width, maxWidth: width }}
                          className={`px-2 py-1 border-r border-[#E2D5A0] truncate align-middle ${align}`}
                        >
                          {renderCellContent(row, col.key, virtualRow.index)}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
