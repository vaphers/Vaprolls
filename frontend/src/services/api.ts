import type { PageRow, InspectorData } from '../types';

export const api = {
  async startAudit(payload: {
    url: string;
    max_pages: number;
    concurrency: number;
    crawl_delay: number;
    user_agent_preset: string;
    mode: 'spider' | 'sitemaps';
    sitemaps_text?: string;
    rendering_mode?: 'text' | 'javascript';
    custom_extractors?: any[];
    custom_search?: any[];
  }): Promise<{ audit_id: string; status: string }> {
    const res = await fetch('/api/audit/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Failed to start crawl: ${res.statusText}`);
    return res.json();
  },

  async stopAudit(auditId: string): Promise<void> {
    await fetch(`/api/audit/${auditId}/stop`, { method: 'POST' });
  },

  async clearAuditData(): Promise<void> {
    await fetch('/api/audit/clear', { method: 'POST' });
  },

  async getAuditStatus(auditId: string): Promise<{ status: string; pages_crawled?: number }> {
    const res = await fetch(`/api/audit/${auditId}/status`);
    if (!res.ok) throw new Error(`Status check failed: ${res.statusText}`);
    return res.json();
  },

  async getTabRows(auditId: string, tabKey: string, sortBy?: string, sortDir?: string): Promise<{ rows: PageRow[]; columns?: any[]; total?: number }> {
    const params = new URLSearchParams();
    if (sortBy && sortBy !== 'row') {
      params.set('sort_by', sortBy);
      params.set('sort_dir', sortDir || 'asc');
    }
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`/api/audit/${auditId}/tab/${tabKey}${qs}`);
    if (!res.ok) throw new Error(`Failed to fetch tab data: ${res.statusText}`);
    return res.json();
  },

  async getInspectorData(auditId: string, pageId: number): Promise<InspectorData> {
    const res = await fetch(`/api/audit/${auditId}/page/${pageId}/inspector`);
    if (!res.ok) throw new Error(`Inspector fetch failed: ${res.statusText}`);
    return res.json();
  },

  async getRightPanelData(auditId: string, panelType: string): Promise<any> {
    let endpoint = '';
    switch (panelType) {
      case 'site-issues': endpoint = 'issues'; break;
      case 'structure': endpoint = 'site-structure'; break;
      case 'segments': endpoint = 'segments'; break;
      case 'response-times': endpoint = 'response-times'; break;
      case 'depth': endpoint = 'depth'; break;
      default: return null;
    }
    const res = await fetch(`/api/audit/${auditId}/right-panel/${endpoint}`);
    if (!res.ok) return null;
    return res.json();
  },

  async listAudits(): Promise<any[]> {
    const res = await fetch('/api/audit/list');
    if (!res.ok) return [];
    return res.json();
  },

  async compareAudits(baseId: string, compareId: string): Promise<any> {
    const res = await fetch(`/api/audit/compare?base_id=${baseId}&compare_id=${compareId}`);
    if (!res.ok) throw new Error("Comparison failed");
    return res.json();
  },

  async getGraphVisualization(auditId: string, maxNodes: number = 300): Promise<{ nodes: any[]; links: any[] }> {
    const res = await fetch(`/api/audit/${auditId}/visualization/graph?max_nodes=${maxNodes}`);
    if (!res.ok) return { nodes: [], links: [] };
    return res.json();
  },

  async getTreeVisualization(auditId: string): Promise<any> {
    const res = await fetch(`/api/audit/${auditId}/visualization/tree`);
    if (!res.ok) return null;
    return res.json();
  }
};
