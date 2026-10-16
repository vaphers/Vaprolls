import React, { useState, useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useCrawlStore } from '../../store/useCrawlStore';
import { api } from '../../services/api';
import {
  Network,
  FolderTree,
  GitBranch,
  Orbit,
  ZoomIn,
  ZoomOut,
  RefreshCw,
  Maximize2,
  Minimize2,
  Download,
  Search,
  X,
  Loader2,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  File,
  Layers,
  Palette,
  Sliders,
  Play,
  Pause,
  Sun,
  Moon,
  Copy,
  Check,
  Filter
} from 'lucide-react';

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  url: string;
  title: string;
  status_code: number;
  indexability: string;
  depth: number;
  inlinks: number;
  outlinks: number;
  pagerank: number;
  is_orphan: boolean;
  is_seed: boolean;
  parent?: string | null;
  word_count?: number;
  content_type?: string;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
}

interface DirectoryNode {
  name: string;
  path: string;
  page_count?: number;
  url_count?: number;
  status_200?: number;
  status_3xx?: number;
  status_4xx?: number;
  status_codes?: Record<string, number>;
  children: DirectoryNode[];
}

export const VisualizerModal: React.FC = () => {
  const { isVisualizerOpen, setIsVisualizerOpen, auditId } = useCrawlStore();

  // Mode and Theme States
  const [viewType, setViewType] = useState<'force' | 'tree' | 'radial' | 'directory'>('force');
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [colorScheme, setColorScheme] = useState<'status' | 'indexability' | 'depth' | 'orphan'>('status');
  const [sizeScheme, setSizeScheme] = useState<'inlinks' | 'pagerank' | 'uniform'>('inlinks');
  const [labelMode, setLabelMode] = useState<'important' | 'all' | 'hover' | 'none'>('important');
  const [filterStatusCode, setFilterStatusCode] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isPhysicsOpen, setIsPhysicsOpen] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);

  // Physics Simulation Tuning Parameters
  const [chargeStrength, setChargeStrength] = useState(-180);
  const [linkDistance, setLinkDistance] = useState(65);
  const [centerGravity, setCenterGravity] = useState(0.04);
  const [collisionRadius, setCollisionRadius] = useState(8);

  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphLink[] } | null>(null);
  const [directoryData, setDirectoryData] = useState<DirectoryNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);

  const svgRef = useRef<SVGSVGElement | null>(null);
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null);

  const isDark = theme === 'dark';

  useEffect(() => {
    if (isVisualizerOpen && auditId) {
      loadData();
    }
  }, [isVisualizerOpen, auditId]);

  const loadData = async () => {
    if (!auditId) return;
    setLoading(true);
    try {
      const [gData, dData] = await Promise.all([
        api.getGraphVisualization(auditId, 500),
        api.getTreeVisualization(auditId),
      ]);
      setGraphData(gData);
      setDirectoryData(dData);
    } catch (e) {
      console.error('Visualization load error:', e);
    } finally {
      setLoading(false);
    }
  };

  // Node Color Helper
  const getNodeColor = (d: GraphNode) => {
    if (d.is_seed) return isDark ? '#38bdf8' : '#0284c7'; // Vibrant Cyan for Seed

    if (colorScheme === 'status') {
      if (d.status_code === 200) return '#10b981'; // Emerald
      if (d.status_code >= 300 && d.status_code < 400) return '#f59e0b'; // Amber
      if (d.status_code >= 400 && d.status_code < 500) return '#ef4444'; // Rose Red
      return '#a855f7'; // Purple 5xx
    }

    if (colorScheme === 'indexability') {
      return d.indexability === 'Indexable' ? '#10b981' : '#f43f5e';
    }

    if (colorScheme === 'depth') {
      const depthPalette = isDark
        ? ['#38bdf8', '#818cf8', '#a78bfa', '#f472b6', '#fb923c', '#e2e8f0']
        : ['#0284c7', '#4f46e5', '#7c3aed', '#db2777', '#ea580c', '#475569'];
      return depthPalette[Math.min(d.depth || 0, depthPalette.length - 1)];
    }

    if (colorScheme === 'orphan') {
      return d.is_orphan ? '#ef4444' : isDark ? '#64748b' : '#94a3b8';
    }

    return '#10b981';
  };

  // Node Radius Helper
  const getNodeRadius = (d: GraphNode) => {
    if (d.is_seed) return 15;
    if (sizeScheme === 'uniform') return 6.5;
    if (sizeScheme === 'pagerank') {
      const pr = d.pagerank || 0;
      return Math.max(5.5, Math.min(22, 6 + pr * 18));
    }
    // sizeScheme === 'inlinks'
    const inlinks = d.inlinks || 0;
    return Math.max(5.5, Math.min(22, 5.5 + Math.sqrt(inlinks) * 2.8));
  };

  // Check if node matches current search / status filter
  const isNodeActive = (d: GraphNode) => {
    // 1. Status Filter
    if (filterStatusCode !== 'all') {
      if (filterStatusCode === '200' && d.status_code !== 200) return false;
      if (filterStatusCode === '3xx' && (d.status_code < 300 || d.status_code >= 400)) return false;
      if (filterStatusCode === '4xx' && (d.status_code < 400 || d.status_code >= 500)) return false;
      if (filterStatusCode === '5xx' && d.status_code < 500) return false;
      if (filterStatusCode === 'orphan' && !d.is_orphan) return false;
    }

    // 2. Search Term Filter
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase().trim();
      const match = d.url.toLowerCase().includes(term) || (d.title && d.title.toLowerCase().includes(term));
      if (!match) return false;
    }

    return true;
  };

  // Render D3 SVG Scene
  useEffect(() => {
    if (!graphData || !svgRef.current || viewType === 'directory') return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth || 1000;
    const height = svgRef.current.clientHeight || 650;

    // Define defs: glow filters, arrow markers, background grid pattern
    const defs = svg.append('defs');

    // Subtle background grid pattern
    const pattern = defs
      .append('pattern')
      .attr('id', 'bg-grid')
      .attr('width', 36)
      .attr('height', 36)
      .attr('patternUnits', 'userSpaceOnUse');

    pattern
      .append('circle')
      .attr('cx', 18)
      .attr('cy', 18)
      .attr('r', 1)
      .attr('fill', isDark ? '#1e293b' : '#e2e8f0');

    // Soft Radial Glow Filter for Hubs & Seed
    const filter = defs
      .append('filter')
      .attr('id', 'node-glow')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%');
    filter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
    const feMerge = filter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'blur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Canvas Background with Grid
    svg
      .append('rect')
      .attr('width', '100%')
      .attr('height', '100%')
      .attr('fill', isDark ? '#0b0f19' : '#f8fafc');

    svg
      .append('rect')
      .attr('width', '100%')
      .attr('height', '100%')
      .attr('fill', 'url(#bg-grid)');

    const container = svg.append('g').attr('class', 'zoom-viewport');

    // D3 Zoom with smooth inertia
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 6])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom);
    zoomBehaviorRef.current = zoom;

    // Double-click to reset zoom
    svg.on('dblclick.zoom', () => {
      svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.scale(0.85).translate(width * 0.1, height * 0.1));
    });

    // Clone data for rendering
    const nodes: GraphNode[] = graphData.nodes.map((n) => ({ ...n }));
    const links: GraphLink[] = graphData.links.map((l) => ({ ...l }));

    if (viewType === 'force') {
      renderForceLayout(container, nodes, links, width, height, zoom, svg);
    } else if (viewType === 'tree') {
      renderHierarchicalTreeLayout(container, nodes, height, zoom, svg);
    } else if (viewType === 'radial') {
      renderRadialTreeLayout(container, nodes, width, height, zoom, svg);
    }
  }, [
    graphData,
    viewType,
    theme,
    colorScheme,
    sizeScheme,
    labelMode,
    searchTerm,
    filterStatusCode,
    chargeStrength,
    linkDistance,
    centerGravity,
    collisionRadius,
  ]);

  // Toggle simulation freeze/resume
  const togglePauseSimulation = () => {
    if (!simulationRef.current) return;
    if (isPaused) {
      simulationRef.current.alphaTarget(0.2).restart();
      setIsPaused(false);
    } else {
      simulationRef.current.stop();
      setIsPaused(true);
    }
  };

  // 1. Force-Directed Layout Implementation
  const renderForceLayout = (
    container: d3.Selection<SVGGElement, unknown, null, undefined>,
    nodes: GraphNode[],
    links: GraphLink[],
    width: number,
    height: number,
    zoom: d3.ZoomBehavior<SVGSVGElement, unknown>,
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>
  ) => {
    const hasFilter = searchTerm.trim() !== '' || filterStatusCode !== 'all';

    // Links Layer
    const linkGroup = container.append('g').attr('class', 'links');
    const link = linkGroup
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', isDark ? '#334155' : '#cbd5e1')
      .attr('stroke-opacity', isDark ? 0.4 : 0.6)
      .attr('stroke-width', 1.2);

    // Nodes Layer
    const nodeGroup = container.append('g').attr('class', 'nodes');

    const node = nodeGroup
      .selectAll<SVGGElement, GraphNode>('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(
        d3
          .drag<SVGGElement, GraphNode>()
          .on('start', (event, d) => {
            if (!event.active && simulationRef.current && !isPaused) {
              simulationRef.current.alphaTarget(0.3).restart();
            }
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active && simulationRef.current && !isPaused) {
              simulationRef.current.alphaTarget(0);
            }
            // Keep pinned or let float
            d.fx = null;
            d.fy = null;
          })
      );

    // Seed Outer Radiant Halo
    node
      .filter((d) => d.is_seed)
      .append('circle')
      .attr('r', 24)
      .attr('fill', 'none')
      .attr('stroke', isDark ? '#38bdf8' : '#0284c7')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '4,4')
      .attr('opacity', 0.8)
      .attr('filter', 'url(#node-glow)');

    // Search or Filter Highlight Halo
    node
      .filter((d) => hasFilter && isNodeActive(d))
      .append('circle')
      .attr('r', (d) => getNodeRadius(d) + 6)
      .attr('fill', 'none')
      .attr('stroke', '#38bdf8')
      .attr('stroke-width', 2.5)
      .attr('stroke-dasharray', '3,3');

    // Main Node Circle
    node
      .append('circle')
      .attr('r', (d) => getNodeRadius(d))
      .attr('fill', (d) => getNodeColor(d))
      .attr('stroke', isDark ? '#0f172a' : '#ffffff')
      .attr('stroke-width', (d) => (d.is_seed ? 3 : 1.8))
      .attr('opacity', (d) => (hasFilter ? (isNodeActive(d) ? 1 : 0.15) : 1))
      .attr('filter', (d) => (d.is_seed || d.inlinks > 6 ? 'url(#node-glow)' : 'none'));

    // Inner Core Dot for Seed
    node
      .filter((d) => d.is_seed)
      .append('circle')
      .attr('r', 4.5)
      .attr('fill', '#ffffff');

    // Text Labels
    const labels = node
      .append('text')
      .text((d) => d.label)
      .attr('x', (d) => getNodeRadius(d) + 6)
      .attr('y', 3.5)
      .attr('font-size', '10.5px')
      .attr('font-family', 'ui-monospace, SFMono-Regular, Menlo, monospace')
      .attr('font-weight', (d) => (d.is_seed ? '700' : '500'))
      .attr('fill', isDark ? '#f1f5f9' : '#0f172a')
      .attr('paint-order', 'stroke')
      .attr('stroke', isDark ? '#0b0f19' : '#ffffff')
      .attr('stroke-width', isDark ? 3.5 : 3)
      .attr('stroke-linecap', 'round')
      .attr('stroke-linejoin', 'round')
      .attr('opacity', (d) => {
        if (hasFilter) return isNodeActive(d) ? 1 : 0.05;
        if (labelMode === 'all') return 1;
        if (labelMode === 'important') return d.is_seed || d.depth <= 1 || d.inlinks >= 4 ? 1 : 0;
        return 0; // hover or none
      });

    // Hover & Click Interactions
    node
      .on('mouseenter', (_, d) => {
        setHoveredNode(d);
        if (labelMode === 'hover') {
          labels.filter((n) => n.id === d.id).attr('opacity', 1);
        }
        // Highlight active link paths with cyan glow
        link
          .attr('stroke', (l: any) => (l.source.id === d.id || l.target.id === d.id ? '#38bdf8' : isDark ? '#1e293b' : '#e2e8f0'))
          .attr('stroke-width', (l: any) => (l.source.id === d.id || l.target.id === d.id ? 2.5 : 1))
          .attr('stroke-opacity', (l: any) => (l.source.id === d.id || l.target.id === d.id ? 1 : 0.1));
      })
      .on('mouseleave', () => {
        setHoveredNode(null);
        if (labelMode === 'hover') {
          labels.attr('opacity', 0);
        }
        link
          .attr('stroke', isDark ? '#334155' : '#cbd5e1')
          .attr('stroke-width', 1.2)
          .attr('stroke-opacity', isDark ? 0.4 : 0.6);
      })
      .on('click', (_, d) => {
        setSelectedNode(d);
      });

    // D3 Force Physics Setup
    const simulation = d3
      .forceSimulation<GraphNode, GraphLink>(nodes)
      .force(
        'link',
        d3
          .forceLink<GraphNode, GraphLink>(links)
          .id((d) => d.id)
          .distance((l: any) => {
            const srcDepth = l.source.depth || 0;
            return Math.max(35, linkDistance - srcDepth * 6);
          })
          .strength(0.7)
      )
      .force('charge', d3.forceManyBody().strength(chargeStrength))
      .force('collide', d3.forceCollide().radius((d: any) => getNodeRadius(d) + collisionRadius))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('x', d3.forceX(width / 2).strength(centerGravity))
      .force('y', d3.forceY(height / 2).strength(centerGravity));

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    simulationRef.current = simulation;
    setIsPaused(false);

    // Initial center zoom
    svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(0, 0).scale(0.92));
  };

  // 2. Hierarchical Crawl Tree Layout (Tidy Tree)
  const renderHierarchicalTreeLayout = (
    container: d3.Selection<SVGGElement, unknown, null, undefined>,
    nodes: GraphNode[],
    height: number,
    zoom: d3.ZoomBehavior<SVGSVGElement, unknown>,
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>
  ) => {
    const seedNode = nodes.find((n) => n.is_seed) || nodes[0];
    if (!seedNode) return;

    interface HierarchyItem {
      node: GraphNode;
      children: HierarchyItem[];
    }
    const itemMap = new Map<string, HierarchyItem>();
    nodes.forEach((n) => itemMap.set(n.id, { node: n, children: [] }));

    nodes.forEach((n) => {
      if (n.id !== seedNode.id && n.parent && itemMap.has(n.parent)) {
        itemMap.get(n.parent)!.children.push(itemMap.get(n.id)!);
      } else if (n.id !== seedNode.id) {
        itemMap.get(seedNode.id)!.children.push(itemMap.get(n.id)!);
      }
    });

    const rootItem = itemMap.get(seedNode.id)!;
    const root = d3.hierarchy<HierarchyItem>(rootItem, (d) => d.children);

    const treeLayout = d3.tree<HierarchyItem>().nodeSize([32, 240]);
    treeLayout(root);

    // Smooth horizontal Bezier links
    container
      .append('g')
      .selectAll('path')
      .data(root.links())
      .join('path')
      .attr(
        'd',
        d3
          .linkHorizontal<any, any>()
          .x((d) => d.y)
          .y((d) => d.x)
      )
      .attr('fill', 'none')
      .attr('stroke', isDark ? '#334155' : '#cbd5e1')
      .attr('stroke-width', 1.4)
      .attr('stroke-opacity', 0.6);

    // Nodes
    const node = container
      .append('g')
      .selectAll<SVGGElement, d3.HierarchyNode<HierarchyItem>>('g')
      .data(root.descendants())
      .join('g')
      .attr('transform', (d) => `translate(${d.y},${d.x})`)
      .attr('cursor', 'pointer');

    node
      .append('circle')
      .attr('r', (d) => getNodeRadius(d.data.node))
      .attr('fill', (d) => getNodeColor(d.data.node))
      .attr('stroke', isDark ? '#0f172a' : '#ffffff')
      .attr('stroke-width', 2);

    node
      .append('text')
      .text((d) => d.data.node.label)
      .attr('x', (d) => getNodeRadius(d.data.node) + 6)
      .attr('y', 4)
      .attr('font-size', '10.5px')
      .attr('font-family', 'ui-monospace, monospace')
      .attr('font-weight', (d) => (d.data.node.is_seed ? '700' : '500'))
      .attr('fill', isDark ? '#f1f5f9' : '#0f172a')
      .attr('paint-order', 'stroke')
      .attr('stroke', isDark ? '#0b0f19' : '#ffffff')
      .attr('stroke-width', 3);

    node
      .on('mouseenter', (_, d) => setHoveredNode(d.data.node))
      .on('mouseleave', () => setHoveredNode(null))
      .on('click', (_, d) => setSelectedNode(d.data.node));

    svg
      .transition()
      .duration(500)
      .call(zoom.transform, d3.zoomIdentity.translate(80, height / 2).scale(0.85));
  };

  // 3. Radial Orbit Tree Layout
  const renderRadialTreeLayout = (
    container: d3.Selection<SVGGElement, unknown, null, undefined>,
    nodes: GraphNode[],
    width: number,
    height: number,
    zoom: d3.ZoomBehavior<SVGSVGElement, unknown>,
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>
  ) => {
    const seedNode = nodes.find((n) => n.is_seed) || nodes[0];
    if (!seedNode) return;

    interface HierarchyItem {
      node: GraphNode;
      children: HierarchyItem[];
    }
    const itemMap = new Map<string, HierarchyItem>();
    nodes.forEach((n) => itemMap.set(n.id, { node: n, children: [] }));

    nodes.forEach((n) => {
      if (n.id !== seedNode.id && n.parent && itemMap.has(n.parent)) {
        itemMap.get(n.parent)!.children.push(itemMap.get(n.id)!);
      } else if (n.id !== seedNode.id) {
        itemMap.get(seedNode.id)!.children.push(itemMap.get(n.id)!);
      }
    });

    const root = d3.hierarchy<HierarchyItem>(itemMap.get(seedNode.id)!, (d) => d.children);
    const radius = Math.min(width, height) * 0.95;
    const tree = d3
      .tree<HierarchyItem>()
      .size([2 * Math.PI, radius])
      .separation((a, b) => (a.parent === b.parent ? 1 : 2) / a.depth);
    tree(root);

    const radialPoint = (x: number, y: number) => {
      return [(y = +y) * Math.cos((x -= Math.PI / 2)), y * Math.sin(x)];
    };

    // Concentric Orbit Circles
    const depthLevels = [1, 2, 3, 4, 5];
    const ringGroup = container.append('g').attr('class', 'depth-rings');
    depthLevels.forEach((d) => {
      const r = (radius / 5) * d;
      ringGroup
        .append('circle')
        .attr('r', r)
        .attr('fill', 'none')
        .attr('stroke', isDark ? '#1e293b' : '#e2e8f0')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,4');

      ringGroup
        .append('text')
        .attr('x', 6)
        .attr('y', -r + 14)
        .attr('fill', isDark ? '#475569' : '#94a3b8')
        .attr('font-size', '10px')
        .attr('font-weight', 'bold')
        .text(`Click Depth ${d}`);
    });

    // Radial Links
    container
      .append('g')
      .selectAll('path')
      .data(root.links())
      .join('path')
      .attr(
        'd',
        d3
          .linkRadial<any, any>()
          .angle((d) => d.x)
          .radius((d) => d.y)
      )
      .attr('fill', 'none')
      .attr('stroke', isDark ? '#334155' : '#cbd5e1')
      .attr('stroke-width', 1.2)
      .attr('stroke-opacity', 0.5);

    // Nodes
    const node = container
      .append('g')
      .selectAll('g')
      .data(root.descendants())
      .join('g')
      .attr('transform', (d) => `translate(${radialPoint(d.x ?? 0, d.y ?? 0)})`)
      .attr('cursor', 'pointer');

    node
      .append('circle')
      .attr('r', (d) => getNodeRadius(d.data.node))
      .attr('fill', (d) => getNodeColor(d.data.node))
      .attr('stroke', isDark ? '#0f172a' : '#ffffff')
      .attr('stroke-width', 1.8);

    node
      .append('text')
      .attr('transform', (d) => `rotate(${((d.x ?? 0) * 180) / Math.PI - 90}) translate(${d.data.node.is_seed ? 18 : getNodeRadius(d.data.node) + 5},4)`)
      .text((d) => d.data.node.label)
      .attr('font-size', '9.5px')
      .attr('font-family', 'ui-monospace, monospace')
      .attr('fill', isDark ? '#f1f5f9' : '#0f172a')
      .attr('paint-order', 'stroke')
      .attr('stroke', isDark ? '#0b0f19' : '#ffffff')
      .attr('stroke-width', 2.5)
      .attr('opacity', (d) => (d.data.node.is_seed || d.depth <= 2 ? 1 : 0));

    node
      .on('mouseenter', (_, d) => setHoveredNode(d.data.node))
      .on('mouseleave', () => setHoveredNode(null))
      .on('click', (_, d) => setSelectedNode(d.data.node));

    svg
      .transition()
      .duration(500)
      .call(zoom.transform, d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8));
  };

  const handleZoom = (direction: 'in' | 'out' | 'reset') => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    const svg = d3.select(svgRef.current);
    if (direction === 'in') {
      svg.transition().duration(250).call(zoomBehaviorRef.current.scaleBy, 1.3);
    } else if (direction === 'out') {
      svg.transition().duration(250).call(zoomBehaviorRef.current.scaleBy, 0.7);
    } else {
      svg.transition().duration(400).call(zoomBehaviorRef.current.transform, d3.zoomIdentity.scale(0.85));
    }
  };

  const handleExportSvg = () => {
    if (!svgRef.current) return;
    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svgRef.current);
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `crawl_graph_${viewType}_${new Date().toISOString().slice(0, 10)}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 1500);
  };

  if (!isVisualizerOpen) return null;

  // Counts for quick filter pills
  const totalNodes = graphData?.nodes?.length || 0;
  const count200 = graphData?.nodes?.filter((n) => n.status_code === 200).length || 0;
  const count3xx = graphData?.nodes?.filter((n) => n.status_code >= 300 && n.status_code < 400).length || 0;
  const count4xx = graphData?.nodes?.filter((n) => n.status_code >= 400 && n.status_code < 500).length || 0;
  const countOrphan = graphData?.nodes?.filter((n) => n.is_orphan).length || 0;

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-2 sm:p-4 text-white font-sans select-none">
      <div
        className={`bg-[#0b0f19] border border-slate-800 shadow-2xl flex flex-col overflow-hidden transition-all duration-200 ${
          isFullscreen ? 'w-screen h-screen max-w-none max-h-none rounded-none' : 'w-full max-w-7xl h-[94vh] rounded-xl'
        }`}
      >
        {/* Top Header Bar */}
        <div className="bg-[#0f172a]/95 border-b border-slate-800/80 px-4 py-2.5 flex items-center justify-between shrink-0">
          {/* Left: Title & Mode Switcher */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#38bdf8] animate-pulse" />
              <h2 className="font-extrabold text-sm tracking-wide uppercase text-white font-mono">
                Crawl Visualizer
              </h2>
            </div>

            {/* Layout Mode Switcher */}
            <div className="flex items-center bg-[#1e293b] p-0.5 rounded-lg border border-slate-700 text-xs">
              <button
                onClick={() => setViewType('force')}
                className={`px-3 py-1 font-semibold rounded-md flex items-center gap-1.5 transition-all ${
                  viewType === 'force' ? 'bg-[#38bdf8] text-slate-950 shadow-sm' : 'text-slate-300 hover:text-white'
                }`}
              >
                <Network className="w-3.5 h-3.5" />
                Force Graph
              </button>
              <button
                onClick={() => setViewType('tree')}
                className={`px-3 py-1 font-semibold rounded-md flex items-center gap-1.5 transition-all ${
                  viewType === 'tree' ? 'bg-[#38bdf8] text-slate-950 shadow-sm' : 'text-slate-300 hover:text-white'
                }`}
              >
                <GitBranch className="w-3.5 h-3.5" />
                Crawl Tree
              </button>
              <button
                onClick={() => setViewType('radial')}
                className={`px-3 py-1 font-semibold rounded-md flex items-center gap-1.5 transition-all ${
                  viewType === 'radial' ? 'bg-[#38bdf8] text-slate-950 shadow-sm' : 'text-slate-300 hover:text-white'
                }`}
              >
                <Orbit className="w-3.5 h-3.5" />
                Radial Orbit
              </button>
              <button
                onClick={() => setViewType('directory')}
                className={`px-3 py-1 font-semibold rounded-md flex items-center gap-1.5 transition-all ${
                  viewType === 'directory' ? 'bg-[#38bdf8] text-slate-950 shadow-sm' : 'text-slate-300 hover:text-white'
                }`}
              >
                <FolderTree className="w-3.5 h-3.5" />
                Directory Tree
              </button>
            </div>
          </div>

          {/* Right Header Controls */}
          <div className="flex items-center gap-2">
            {/* Live Search */}
            <div className="flex items-center bg-[#1e293b] border border-slate-700 rounded-lg px-2.5 py-1 w-52 text-xs">
              <Search className="w-3.5 h-3.5 text-slate-400 mr-1.5 shrink-0" />
              <input
                type="text"
                placeholder="Search URL or title..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-transparent text-white placeholder-slate-400 outline-none font-mono text-xs"
              />
              {searchTerm && (
                <button onClick={() => setSearchTerm('')} className="text-slate-400 hover:text-white">
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Theme Toggle */}
            <button
              onClick={() => setTheme(isDark ? 'light' : 'dark')}
              className="p-1.5 bg-[#1e293b] hover:bg-slate-700 border border-slate-700 rounded-lg text-slate-300 hover:text-white transition-colors"
              title={isDark ? 'Switch to Light Studio' : 'Switch to Dark Cyber'}
            >
              {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-300" />}
            </button>

            {/* Fullscreen Toggle */}
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 bg-[#1e293b] hover:bg-slate-700 border border-slate-700 rounded-lg text-slate-300 hover:text-white transition-colors"
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>

            {/* Close Button */}
            <button
              onClick={() => setIsVisualizerOpen(false)}
              className="p-1.5 bg-[#1e293b] hover:bg-rose-900/60 hover:text-rose-400 border border-slate-700 rounded-lg text-slate-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Status Filter Pills Bar */}
        {viewType !== 'directory' && (
          <div className="bg-[#0b0f19] border-b border-slate-800/80 px-4 py-1.5 flex items-center justify-between text-xs shrink-0 flex-wrap gap-2">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-bold uppercase text-slate-400 flex items-center gap-1 mr-1">
                <Filter className="w-3 h-3" /> Filter:
              </span>
              <button
                onClick={() => setFilterStatusCode('all')}
                className={`px-2 py-0.5 rounded text-[11px] font-bold border transition-colors ${
                  filterStatusCode === 'all'
                    ? 'bg-slate-200 text-slate-900 border-white'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                }`}
              >
                All ({totalNodes})
              </button>
              <button
                onClick={() => setFilterStatusCode('200')}
                className={`px-2 py-0.5 rounded text-[11px] font-bold border transition-colors ${
                  filterStatusCode === '200'
                    ? 'bg-emerald-500 text-slate-950 border-emerald-400'
                    : 'bg-emerald-950/40 text-emerald-400 border-emerald-900/50 hover:bg-emerald-950/70'
                }`}
              >
                200 OK ({count200})
              </button>
              <button
                onClick={() => setFilterStatusCode('3xx')}
                className={`px-2 py-0.5 rounded text-[11px] font-bold border transition-colors ${
                  filterStatusCode === '3xx'
                    ? 'bg-amber-500 text-slate-950 border-amber-400'
                    : 'bg-amber-950/40 text-amber-400 border-amber-900/50 hover:bg-amber-950/70'
                }`}
              >
                3xx Redirects ({count3xx})
              </button>
              <button
                onClick={() => setFilterStatusCode('4xx')}
                className={`px-2 py-0.5 rounded text-[11px] font-bold border transition-colors ${
                  filterStatusCode === '4xx'
                    ? 'bg-rose-500 text-white border-rose-400'
                    : 'bg-rose-950/40 text-rose-400 border-rose-900/50 hover:bg-rose-950/70'
                }`}
              >
                4xx Broken ({count4xx})
              </button>
              <button
                onClick={() => setFilterStatusCode('orphan')}
                className={`px-2 py-0.5 rounded text-[11px] font-bold border transition-colors ${
                  filterStatusCode === 'orphan'
                    ? 'bg-red-600 text-white border-red-400'
                    : 'bg-red-950/40 text-red-400 border-red-900/50 hover:bg-red-950/70'
                }`}
              >
                Orphan Pages ({countOrphan})
              </button>
            </div>

            {/* Visualization Settings Bar */}
            <div className="flex items-center gap-2">
              {/* Color Scheme */}
              <div className="flex items-center gap-1 text-[11px] text-slate-400">
                <Palette className="w-3 h-3" />
                <select
                  value={colorScheme}
                  onChange={(e) => setColorScheme(e.target.value as any)}
                  className="bg-[#1e293b] border border-slate-700 text-slate-200 px-2 py-0.5 rounded outline-none cursor-pointer"
                >
                  <option value="status">Color: HTTP Status</option>
                  <option value="indexability">Color: Indexability</option>
                  <option value="depth">Color: Click Depth</option>
                  <option value="orphan">Color: Orphan Status</option>
                </select>
              </div>

              {/* Node Sizing */}
              <div className="flex items-center gap-1 text-[11px] text-slate-400">
                <Layers className="w-3 h-3" />
                <select
                  value={sizeScheme}
                  onChange={(e) => setSizeScheme(e.target.value as any)}
                  className="bg-[#1e293b] border border-slate-700 text-slate-200 px-2 py-0.5 rounded outline-none cursor-pointer"
                >
                  <option value="inlinks">Size: By Inlinks</option>
                  <option value="pagerank">Size: By PageRank</option>
                  <option value="uniform">Size: Uniform</option>
                </select>
              </div>

              {/* Labels Mode */}
              <div className="flex items-center gap-1 text-[11px] text-slate-400">
                <select
                  value={labelMode}
                  onChange={(e) => setLabelMode(e.target.value as any)}
                  className="bg-[#1e293b] border border-slate-700 text-slate-200 px-2 py-0.5 rounded outline-none cursor-pointer"
                >
                  <option value="important">Labels: Important Only</option>
                  <option value="all">Labels: Show All</option>
                  <option value="hover">Labels: On Hover</option>
                  <option value="none">Labels: Hide</option>
                </select>
              </div>

              {/* Physics Tuning Toggle */}
              {viewType === 'force' && (
                <button
                  onClick={() => setIsPhysicsOpen(!isPhysicsOpen)}
                  className={`px-2 py-0.5 rounded border text-[11px] font-bold flex items-center gap-1 transition-colors ${
                    isPhysicsOpen
                      ? 'bg-[#38bdf8] text-slate-950 border-[#38bdf8]'
                      : 'bg-[#1e293b] text-slate-300 border-slate-700 hover:text-white'
                  }`}
                >
                  <Sliders className="w-3 h-3" />
                  Physics
                </button>
              )}
            </div>
          </div>
        )}

        {/* Main Canvas Area */}
        <div className="flex-1 overflow-hidden relative flex">
          {loading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/80 z-30">
              <Loader2 className="w-10 h-10 animate-spin text-[#38bdf8] mb-2" />
              <span className="text-xs font-mono text-slate-300">Rendering high-resolution site topology...</span>
            </div>
          ) : viewType === 'directory' ? (
            <div className="flex-1 overflow-auto p-4 text-xs font-mono bg-[#0b0f19] text-slate-200">
              {directoryData ? (
                <DirectoryTreeNode node={directoryData} depth={0} />
              ) : (
                <div className="text-slate-500 py-12 text-center">No directory hierarchy available.</div>
              )}
            </div>
          ) : (
            <div className="w-full h-full relative">
              <svg ref={svgRef} className="w-full h-full block" />

              {/* Floating Zoom & Canvas Controls */}
              <div className="absolute top-4 left-4 flex flex-col gap-1.5 bg-[#0f172a]/90 backdrop-blur-md border border-slate-700/80 p-1.5 rounded-xl shadow-xl z-20">
                <button
                  onClick={() => handleZoom('in')}
                  className="p-2 hover:bg-slate-700 rounded-lg text-slate-300 hover:text-white transition-colors"
                  title="Zoom In"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleZoom('out')}
                  className="p-2 hover:bg-slate-700 rounded-lg text-slate-300 hover:text-white transition-colors"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleZoom('reset')}
                  className="p-2 hover:bg-slate-700 rounded-lg text-slate-300 hover:text-white transition-colors"
                  title="Reset View"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
                {viewType === 'force' && (
                  <button
                    onClick={togglePauseSimulation}
                    className="p-2 hover:bg-slate-700 rounded-lg text-slate-300 hover:text-white transition-colors"
                    title={isPaused ? 'Resume Simulation' : 'Freeze Nodes in Place'}
                  >
                    {isPaused ? <Play className="w-4 h-4 text-emerald-400" /> : <Pause className="w-4 h-4 text-amber-400" />}
                  </button>
                )}
                <div className="border-t border-slate-700/80 my-0.5" />
                <button
                  onClick={handleExportSvg}
                  className="p-2 hover:bg-slate-700 rounded-lg text-slate-300 hover:text-white transition-colors"
                  title="Export Diagram as SVG"
                >
                  <Download className="w-4 h-4" />
                </button>
              </div>

              {/* Floating Physics Controls Panel */}
              {isPhysicsOpen && viewType === 'force' && (
                <div className="absolute top-4 left-18 bg-[#0f172a]/95 backdrop-blur-md border border-slate-700 p-3.5 rounded-xl shadow-2xl text-xs space-y-3 w-64 z-20 animate-in fade-in slide-in-from-left-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 font-bold">
                    <span className="flex items-center gap-1.5 text-white">
                      <Sliders className="w-3.5 h-3.5 text-[#38bdf8]" />
                      Physics Controls
                    </span>
                    <button onClick={() => setIsPhysicsOpen(false)} className="text-slate-400 hover:text-white">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-300">
                      <span>Node Repulsion</span>
                      <span className="font-mono">{Math.abs(chargeStrength)}</span>
                    </div>
                    <input
                      type="range"
                      min="-400"
                      max="-40"
                      value={chargeStrength}
                      onChange={(e) => setChargeStrength(Number(e.target.value))}
                      className="w-full accent-[#38bdf8] cursor-pointer"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-300">
                      <span>Link Distance</span>
                      <span className="font-mono">{linkDistance}px</span>
                    </div>
                    <input
                      type="range"
                      min="25"
                      max="140"
                      value={linkDistance}
                      onChange={(e) => setLinkDistance(Number(e.target.value))}
                      className="w-full accent-[#38bdf8] cursor-pointer"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-300">
                      <span>Center Gravity</span>
                      <span className="font-mono">{(centerGravity * 100).toFixed(0)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.01"
                      max="0.15"
                      step="0.01"
                      value={centerGravity}
                      onChange={(e) => setCenterGravity(Number(e.target.value))}
                      className="w-full accent-[#38bdf8] cursor-pointer"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-300">
                      <span>Collision Spacing</span>
                      <span className="font-mono">{collisionRadius}px</span>
                    </div>
                    <input
                      type="range"
                      min="2"
                      max="20"
                      value={collisionRadius}
                      onChange={(e) => setCollisionRadius(Number(e.target.value))}
                      className="w-full accent-[#38bdf8] cursor-pointer"
                    />
                  </div>
                </div>
              )}

              {/* Floating Bottom Legend */}
              <div className="absolute bottom-4 left-4 bg-[#0f172a]/90 backdrop-blur-md border border-slate-700/80 px-3.5 py-2 rounded-xl text-[11px] shadow-xl z-20 flex items-center gap-4 text-slate-300">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-[#38bdf8] border border-white inline-block shadow-sm" />
                  <span className="font-semibold text-white">Seed</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-[#10b981] inline-block shadow-sm" />
                  <span>200 OK</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-[#f59e0b] inline-block shadow-sm" />
                  <span>3xx</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-[#ef4444] inline-block shadow-sm" />
                  <span>4xx</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-[#dc2626] border border-white inline-block shadow-sm" />
                  <span className="text-red-400 font-bold">Orphan</span>
                </div>
                <div className="text-slate-500 border-l border-slate-700 pl-3">
                  {graphData?.nodes?.length || 0} nodes • {graphData?.links?.length || 0} links
                </div>
              </div>

              {/* Selected Node Floating HUD Card */}
              {selectedNode && (
                <div className="absolute top-4 right-4 bg-[#0f172a]/95 backdrop-blur-md border border-slate-700 shadow-2xl p-4 rounded-xl w-84 text-xs font-mono space-y-3 z-30 animate-in fade-in slide-in-from-top-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="font-bold font-sans text-xs uppercase text-slate-300 flex items-center gap-1.5">
                      <Network className="w-4 h-4 text-[#38bdf8]" />
                      URL Details
                    </span>
                    <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-white">
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="space-y-1">
                    <div className="text-[10px] uppercase font-bold text-slate-400 font-sans">Address</div>
                    <div className="break-all font-bold text-white select-all text-[11px] bg-slate-900 p-2 rounded border border-slate-800">
                      {selectedNode.url}
                    </div>
                  </div>

                  {selectedNode.title && (
                    <div className="space-y-0.5">
                      <div className="text-[10px] uppercase font-bold text-slate-400 font-sans">Title</div>
                      <div className="truncate text-slate-200 text-[11px] font-sans">{selectedNode.title}</div>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2 pt-1 font-sans text-[11px]">
                    <div className="p-2 border border-slate-800 bg-slate-900 rounded-lg">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Status Code</span>
                      <span
                        className={`font-bold text-xs ${
                          selectedNode.status_code === 200 ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {selectedNode.status_code} ({selectedNode.indexability})
                      </span>
                    </div>

                    <div className="p-2 border border-slate-800 bg-slate-900 rounded-lg">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Exact Click Depth</span>
                      <span className="font-bold text-xs text-white">
                        Depth {selectedNode.depth} {selectedNode.is_seed ? '(Seed)' : ''}
                      </span>
                    </div>

                    <div className="p-2 border border-slate-800 bg-slate-900 rounded-lg">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Link Equity</span>
                      <span className="font-bold text-xs text-white font-mono">
                        {selectedNode.inlinks} in • {selectedNode.outlinks} out
                      </span>
                    </div>

                    <div className="p-2 border border-slate-800 bg-slate-900 rounded-lg">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">PageRank</span>
                      <span className="font-bold text-xs text-white font-mono">
                        {(selectedNode.pagerank || 0).toFixed(4)}
                      </span>
                    </div>
                  </div>

                  {selectedNode.is_orphan && (
                    <div className="p-2 bg-rose-950/60 border border-rose-800 text-rose-300 font-bold text-[11px] text-center rounded-lg">
                      ⚠ ISOLATED ORPHAN PAGE (0 INTERNAL INLINKS)
                    </div>
                  )}

                  <div className="flex items-center gap-2 pt-1 font-sans">
                    <button
                      onClick={() => handleCopyUrl(selectedNode.url)}
                      className="flex-1 py-1.5 px-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-semibold text-center flex items-center justify-center gap-1 text-[11px] transition-colors"
                    >
                      {copiedUrl ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      {copiedUrl ? 'Copied' : 'Copy URL'}
                    </button>
                    <a
                      href={selectedNode.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex-1 py-1.5 px-2 bg-[#38bdf8] hover:bg-[#0284c7] text-slate-950 rounded-lg font-bold text-center flex items-center justify-center gap-1 text-[11px] transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      Open URL
                    </a>
                  </div>
                </div>
              )}

              {/* Hover Quick Tooltip */}
              {hoveredNode && !selectedNode && (
                <div className="absolute top-4 right-4 bg-[#0f172a]/95 backdrop-blur-md border border-slate-700 p-3 rounded-xl shadow-xl text-xs font-mono space-y-1 max-w-sm pointer-events-none animate-in fade-in">
                  <div className="text-[10px] uppercase font-bold text-slate-400 font-sans">Node Inspector</div>
                  <div className="break-all font-bold text-white text-[11px]">{hoveredNode.url}</div>
                  <div className="flex items-center gap-2 text-[10px] font-sans pt-0.5 text-slate-300">
                    <span className={`font-bold ${hoveredNode.status_code === 200 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {hoveredNode.status_code}
                    </span>
                    <span>•</span>
                    <span>Depth: {hoveredNode.depth}</span>
                    <span>•</span>
                    <span>Inlinks: {hoveredNode.inlinks}</span>
                    <span>•</span>
                    <span>PR: {(hoveredNode.pagerank || 0).toFixed(3)}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Recursive Collapsible Directory Tree Node Component
const DirectoryTreeNode: React.FC<{ node: DirectoryNode; depth: number }> = ({ node, depth }) => {
  const [isOpen, setIsOpen] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className="space-y-1 select-none">
      <div
        onClick={() => hasChildren && setIsOpen(!isOpen)}
        className={`flex items-center gap-2 p-1.5 hover:bg-slate-800/60 rounded-lg cursor-pointer ${
          depth === 0 ? 'font-bold bg-slate-800/40 text-white' : 'text-slate-300'
        }`}
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        {hasChildren ? (
          isOpen ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
        ) : (
          <File className="w-3.5 h-3.5 text-slate-500" />
        )}

        <span className="font-semibold font-mono text-white">{node.name || '/'}</span>
        <span className="text-[11px] text-slate-400 font-sans">({node.url_count || node.page_count || 0} URLs)</span>

        {/* Status Code Pills */}
        <div className="flex items-center gap-1.5 ml-auto font-sans text-[10px]">
          {node.status_200 !== undefined && node.status_200 > 0 && (
            <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-900/60 font-bold">
              200: {node.status_200}
            </span>
          )}
          {node.status_3xx !== undefined && node.status_3xx > 0 && (
            <span className="px-2 py-0.5 rounded bg-amber-950/60 text-amber-400 border border-amber-900/60 font-bold">
              3xx: {node.status_3xx}
            </span>
          )}
          {node.status_4xx !== undefined && node.status_4xx > 0 && (
            <span className="px-2 py-0.5 rounded bg-rose-950/60 text-rose-400 border border-rose-900/60 font-bold">
              4xx: {node.status_4xx}
            </span>
          )}
          {node.status_codes &&
            Object.entries(node.status_codes).map(([code, count]) => (
              <span key={code} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold">
                {code}: {count}
              </span>
            ))}
        </div>
      </div>

      {isOpen && hasChildren && (
        <div className="border-l border-slate-800 ml-4">
          {node.children.map((child, i) => (
            <DirectoryTreeNode key={i} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
};
