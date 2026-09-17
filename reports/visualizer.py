"""
Link Graph Visualizer for Vaprolls SEO Spider.
Generates interactive force-directed link graphs (D3.js) and GEXF files for Gephi.
"""
import json
import logging
import os
from typing import Optional, Any, Dict, List
from database.db import Database

logger = logging.getLogger(__name__)

class LinkGraphVisualizer:
    """
    Exports internal site architecture as an interactive visual graph.
    - D3.js interactive HTML visualization with zoom, drag, and node tooltips
    - GEXF format export for advanced network analysis in Gephi
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def export_d3_html(self, output_path: str, max_nodes: int = 400) -> str:
        """Generates a standalone, interactive HTML file featuring a D3.js force-directed graph."""
        pages = await self.db.get_pages(self.audit_id)
        links = await self.db.get_links(self.audit_id, is_internal=True)

        # Build node list (sample top nodes by inlinks/pagerank if large)
        sorted_pages = sorted(
            pages,
            key=lambda p: (p.get('internal_pagerank', 0.0) or 0.0, p.get('unique_inlinks', 0)),
            reverse=True
        )[:max_nodes]

        allowed_pids = {p['id'] for p in sorted_pages}
        url_to_id = {p['url']: p['id'] for p in sorted_pages}

        nodes = []
        for p in sorted_pages:
            status = p.get('status_code', 200)
            depth = p.get('crawl_depth', 0) or 0
            pr = p.get('internal_pagerank', 0.0) or 0.0
            inlinks = p.get('unique_inlinks', 0)
            
            # Group colors: 0=Homepage, 1=Level1, 2=Level2, 3=Deep, 4=Redirect, 5=Error
            group = 0 if depth == 0 else (4 if 300 <= status < 400 else (5 if status >= 400 else min(3, depth)))
            radius = max(5, min(30, int(inlinks * 1.5) + 6))

            nodes.append({
                'id': p['id'],
                'url': p['url'],
                'title': (p.get('title') or p['url'])[:50],
                'status': status,
                'depth': depth,
                'inlinks': inlinks,
                'pagerank': round(pr, 4),
                'group': group,
                'radius': radius
            })

        edges = []
        edge_seen = set()
        for link in links:
            s_id = link.get('source_page_id')
            t_url = link.get('target_url')
            t_id = url_to_id.get(t_url)

            if s_id in allowed_pids and t_id in allowed_pids and s_id != t_id:
                key = (s_id, t_id)
                if key not in edge_seen:
                    edge_seen.add(key)
                    edges.append({
                        'source': s_id,
                        'target': t_id
                    })

        graph_data = json.dumps({'nodes': nodes, 'links': edges})

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Internal Link Architecture Graph - Audit {self.audit_id}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            margin: 0;
            background: #0d1117;
            color: #c9d1d9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            overflow: hidden;
        }}
        #header {{
            position: absolute;
            top: 16px;
            left: 20px;
            z-index: 10;
            background: rgba(22, 27, 34, 0.85);
            backdrop-filter: blur(8px);
            padding: 12px 20px;
            border-radius: 10px;
            border: 1px solid #30363d;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }}
        h1 {{
            margin: 0 0 6px 0;
            font-size: 18px;
            font-weight: 600;
            color: #58a6ff;
        }}
        .stats {{
            font-size: 13px;
            color: #8b949e;
        }}
        #legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            z-index: 10;
            background: rgba(22, 27, 34, 0.85);
            backdrop-filter: blur(8px);
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid #30363d;
            font-size: 12px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 6px;
        }}
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        #tooltip {{
            position: absolute;
            display: none;
            background: rgba(13, 17, 23, 0.95);
            border: 1px solid #58a6ff;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 13px;
            pointer-events: none;
            z-index: 100;
            box-shadow: 0 4px 16px rgba(0,0,0,0.6);
            max-width: 380px;
        }}
        .link {{
            stroke: #30363d;
            stroke-opacity: 0.5;
            stroke-width: 1px;
        }}
        .node {{
            cursor: pointer;
            stroke: #0d1117;
            stroke-width: 1.5px;
            transition: stroke 0.2s;
        }}
        .node:hover {{
            stroke: #fff;
            stroke-width: 2.5px;
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>Vaprolls Internal Link Graph</h1>
        <div class="stats">Nodes: {len(nodes)} pages | Edges: {len(edges)} links | Zoom: Scroll | Pan: Drag</div>
    </div>

    <div id="legend">
        <div class="legend-item"><div class="legend-color" style="background:#58a6ff;"></div>Homepage (Depth 0)</div>
        <div class="legend-item"><div class="legend-color" style="background:#3fb950;"></div>Depth 1 Category</div>
        <div class="legend-item"><div class="legend-color" style="background:#d29922;"></div>Depth 2 Subcategory</div>
        <div class="legend-item"><div class="legend-color" style="background:#a371f7;"></div>Depth 3+ Articles/Products</div>
        <div class="legend-item"><div class="legend-color" style="background:#f85149;"></div>4xx / 5xx Broken</div>
    </div>

    <div id="tooltip"></div>
    <svg id="graph" width="100%" height="100%"></svg>

    <script>
        const data = {graph_data};
        const width = window.innerWidth;
        const height = window.innerHeight;

        const colors = {{
            0: "#58a6ff", // Homepage
            1: "#3fb950", // Level 1
            2: "#d29922", // Level 2
            3: "#a371f7", // Deep
            4: "#db61a2", // Redirect
            5: "#f85149"  // Broken
        }};

        const svg = d3.select("#graph")
            .attr("viewBox", [0, 0, width, height]);

        const g = svg.append("g");

        svg.call(d3.zoom()
            .extent([[0, 0], [width, height]])
            .scaleExtent([0.1, 8])
            .on("zoom", ({{transform}}) => g.attr("transform", transform)));

        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id).distance(60))
            .force("charge", d3.forceManyBody().strength(-120))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => d.radius + 4));

        const link = g.append("g")
            .selectAll("line")
            .data(data.links)
            .join("line")
            .attr("class", "link");

        const tooltip = d3.select("#tooltip");

        const node = g.append("g")
            .selectAll("circle")
            .data(data.nodes)
            .join("circle")
            .attr("class", "node")
            .attr("r", d => d.radius)
            .attr("fill", d => colors[d.group] || "#8b949e")
            .on("mouseover", (event, d) => {{
                tooltip.style("display", "block")
                    .html(`<strong>${{d.title}}</strong><br>` +
                          `<span style="color:#8b949e; word-break:break-all;">${{d.url}}</span><br>` +
                          `<span style="color:#58a6ff;">Status:</span> ${{d.status}} | ` +
                          `<span style="color:#3fb950;">Depth:</span> ${{d.depth}} | ` +
                          `<span style="color:#d29922;">Inlinks:</span> ${{d.inlinks}}`);
            }})
            .on("mousemove", (event) => {{
                tooltip.style("left", (event.pageX + 14) + "px")
                       .style("top", (event.pageY + 14) + "px");
            }})
            .on("mouseout", () => tooltip.style("display", "none"))
            .call(drag(simulation));

        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
        }});

        function drag(sim) {{
            function dragstarted(event) {{
                if (!event.active) sim.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }}
            function dragged(event) {{
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }}
            function dragended(event) {{
                if (!event.active) sim.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }}
            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended);
        }}
    </script>
</body>
</html>
"""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"Interactive link graph exported to {output_path}")
        return output_path

    async def export_gexf(self, output_path: str) -> str:
        """Exports link graph to standard GEXF XML format for Gephi."""
        pages = await self.db.get_pages(self.audit_id)
        links = await self.db.get_links(self.audit_id, is_internal=True)

        url_to_id = {p['url']: p['id'] for p in pages}

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">',
            f'  <meta lastmodifieddate="{self.audit_id}">',
            '    <creator>Vaprolls SEO Spider</creator>',
            '    <description>Internal Link Structure Graph</description>',
            '  </meta>',
            '  <graph defaultedgetype="directed" mode="static">',
            '    <attributes class="node">',
            '      <attribute id="0" title="status" type="integer"/>',
            '      <attribute id="1" title="depth" type="integer"/>',
            '      <attribute id="2" title="pagerank" type="float"/>',
            '    </attributes>',
            '    <nodes>'
        ]

        for p in pages:
            url_clean = (p.get('url') or '').replace('&', '&amp;').replace('"', '&quot;')
            title_clean = (p.get('title') or url_clean).replace('&', '&amp;').replace('"', '&quot;')
            status = p.get('status_code', 200)
            depth = p.get('crawl_depth', 0) or 0
            pr = p.get('internal_pagerank', 0.0) or 0.0
            lines.append(f'      <node id="{p["id"]}" label="{title_clean[:60]}">')
            lines.append('        <attvalues>')
            lines.append(f'          <attvalue for="0" value="{status}"/>')
            lines.append(f'          <attvalue for="1" value="{depth}"/>')
            lines.append(f'          <attvalue for="2" value="{pr:.6f}"/>')
            lines.append('        </attvalues>')
            lines.append('      </node>')

        lines.append('    </nodes>')
        lines.append('    <edges>')

        for idx, link in enumerate(links):
            s_id = link.get('source_page_id')
            t_url = link.get('target_url')
            t_id = url_to_id.get(t_url)
            if s_id and t_id:
                lines.append(f'      <edge id="{idx}" source="{s_id}" target="{t_id}"/>')

        lines.append('    </edges>')
        lines.append('  </graph>')
        lines.append('</gexf>')

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info(f"GEXF network graph exported to {output_path}")
        return output_path
