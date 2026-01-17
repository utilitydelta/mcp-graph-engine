// src/mcp_graph_engine/visualization/static/graph.js

class GraphVisualization {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.nodes = [];
        this.edges = [];
        this.nodeMap = new Map();
        this.simulation = null;
        this.transform = d3.zoomIdentity;
        this.hoveredNode = null;
        this.showEdgeLabels = true;
        this.sizeByDegree = true;
        this.criticalPath = new Set();
        this.typeColors = new Map();

        this.setupCanvas();
        this.setupSimulation();
        this.setupInteraction();
        this.connectWebSocket();
    }

    setupCanvas() {
        const resize = () => {
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
            this.render();
        };
        window.addEventListener('resize', resize);
        resize();
    }

    setupSimulation() {
        this.simulation = d3.forceSimulation()
            .force('link', d3.forceLink()
                .id(d => d.id)
                .distance(d => {
                    const sourceRadius = this.getNodeRadius(d.source, false);
                    const targetRadius = this.getNodeRadius(d.target, false);
                    return 180 + sourceRadius + targetRadius;  // Base distance + both radii
                })
            )
            .force('charge', d3.forceManyBody().strength(-1800))
            .force('center', d3.forceCenter(this.canvas.width / 2, this.canvas.height / 2))
            .force('collision', d3.forceCollide().radius(d => this.getNodeRadius(d, false) + 20))
            .on('tick', () => this.render());
    }

    setupInteraction() {
        // Track dragged node
        this.draggedNode = null;

        // Zoom for scroll wheel only
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .filter((event) => event.type === 'wheel')
            .on('zoom', (event) => {
                this.transform = event.transform;
                this.render();
            });

        d3.select(this.canvas).call(zoom);

        // Store zoom behavior to update transform during pan
        this.zoomBehavior = zoom;

        // Single drag handles both node dragging and canvas panning
        const drag = d3.drag()
            .on('start', (event) => {
                const [x, y] = this.transform.invert([event.x, event.y]);
                this.draggedNode = this.findNodeAt(x, y);

                if (this.draggedNode) {
                    // Dragging a node - heat up simulation
                    if (!event.active) this.simulation.alphaTarget(0.3).restart();
                    this.draggedNode.fx = this.draggedNode.x;
                    this.draggedNode.fy = this.draggedNode.y;
                }
            })
            .on('drag', (event) => {
                if (this.draggedNode) {
                    // Move the node
                    const [x, y] = this.transform.invert([event.x, event.y]);
                    this.draggedNode.fx = x;
                    this.draggedNode.fy = y;
                } else {
                    // Pan the canvas
                    this.transform = this.transform.translate(event.dx / this.transform.k, event.dy / this.transform.k);
                    // Sync with D3 zoom behavior so wheel zoom uses current position
                    d3.select(this.canvas).call(this.zoomBehavior.transform, this.transform);
                    this.render();
                }
            })
            .on('end', (event) => {
                if (this.draggedNode) {
                    // Release the node
                    if (!event.active) this.simulation.alphaTarget(0);
                    this.draggedNode.fx = null;
                    this.draggedNode.fy = null;
                    this.draggedNode = null;
                }
            });

        d3.select(this.canvas).call(drag);

        // Edge label toggle
        const labelToggle = document.getElementById('toggle-labels');
        if (labelToggle) {
            labelToggle.addEventListener('change', (e) => {
                this.showEdgeLabels = e.target.checked;
                this.render();
            });
        }

        // Degree sizing toggle
        const degreeSizingToggle = document.getElementById('toggle-degree-sizing');
        if (degreeSizingToggle) {
            degreeSizingToggle.addEventListener('change', (e) => {
                this.sizeByDegree = e.target.checked;
                this.simulation.force('collision').radius(d => this.getNodeRadius(d, false) + 20);
                this.simulation.force('link').distance(d => {
                    const sourceRadius = this.getNodeRadius(d.source, false);
                    const targetRadius = this.getNodeRadius(d.target, false);
                    return 180 + sourceRadius + targetRadius;
                });
                this.simulation.alpha(0.3).restart();
            });
        }

        // Hover detection
        this.canvas.addEventListener('mousemove', (event) => {
            const [x, y] = this.transform.invert([event.clientX, event.clientY]);
            this.hoveredNode = this.findNodeAt(x, y);
            this.updateTooltip(event.clientX, event.clientY);
            this.render();
        });

        this.canvas.addEventListener('mouseout', () => {
            this.hoveredNode = null;
            this.hideTooltip();
            this.render();
        });
    }

    connectWebSocket() {
        // Close existing WebSocket if present to prevent accumulation
        if (this.ws) {
            this.ws.onclose = null; // Prevent reconnect trigger from manual close
            this.ws.close();
            this.ws = null;
        }

        const graphName = window.location.pathname.split('/').pop() || 'default';
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${graphName}`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.setConnectionStatus('connected');
        };

        this.ws.onclose = () => {
            this.setConnectionStatus('disconnected');
            // Reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.ws.onerror = () => {
            this.setConnectionStatus('disconnected');
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };
    }

    handleMessage(message) {
        switch (message.type) {
            case 'initial_state':
            case 'full_refresh':
            case 'filter_update':
                this.setGraphData(message.graph, message.nodes, message.edges, message.filter, message.criticalPath || []);
                break;

            case 'graph_update':
                this.applyUpdate(message);
                break;
        }
    }

    setGraphData(graphName, nodes, edges, filter, criticalPath) {
        this.nodes = nodes;
        this.edges = edges.map(e => ({
            ...e,
            source: e.source,
            target: e.target
        }));

        // Rebuild node map
        this.nodeMap.clear();
        this.nodes.forEach(n => this.nodeMap.set(n.id, n));

        // Rebuild critical path set
        this.criticalPath.clear();
        criticalPath.forEach(edge => {
            const key = edge.source + '->' + edge.target;
            this.criticalPath.add(key);
        });

        // Update UI
        document.getElementById('graph-name').textContent = graphName;
        document.getElementById('node-count').textContent = nodes.length;
        document.getElementById('edge-count').textContent = edges.length;
        document.getElementById('filter-info').textContent = filter ? `Filter: ${filter.substring(0, 50)}...` : '';

        // Update simulation
        this.simulation.nodes(this.nodes);
        this.simulation.force('link').links(this.edges);
        this.simulation.alpha(1).restart();
    }

    applyUpdate(update) {
        // Remove nodes
        if (update.removed_nodes) {
            update.removed_nodes.forEach(id => {
                const idx = this.nodes.findIndex(n => n.id === id);
                if (idx >= 0) this.nodes.splice(idx, 1);
                this.nodeMap.delete(id);
            });
        }

        // Add nodes
        if (update.added_nodes) {
            update.added_nodes.forEach(node => {
                if (!this.nodeMap.has(node.id)) {
                    // Position new nodes near center
                    node.x = this.canvas.width / 2 + (Math.random() - 0.5) * 100;
                    node.y = this.canvas.height / 2 + (Math.random() - 0.5) * 100;
                    this.nodes.push(node);
                    this.nodeMap.set(node.id, node);
                }
            });
        }

        // Remove edges
        if (update.removed_edges) {
            update.removed_edges.forEach(e => {
                const idx = this.edges.findIndex(
                    edge => edge.source.id === e.source &&
                            edge.target.id === e.target &&
                            edge.relation === e.relation
                );
                if (idx >= 0) {
                    this.edges.splice(idx, 1);
                    // Update degree counts
                    const sourceNode = this.nodeMap.get(e.source);
                    const targetNode = this.nodeMap.get(e.target);
                    if (sourceNode) sourceNode.outDegree = Math.max(0, (sourceNode.outDegree || 0) - 1);
                    if (targetNode) targetNode.inDegree = Math.max(0, (targetNode.inDegree || 0) - 1);
                }
            });
        }

        // Add edges
        if (update.added_edges) {
            update.added_edges.forEach(edge => {
                this.edges.push({
                    ...edge,
                    source: edge.source,
                    target: edge.target
                });
                // Update degree counts
                const sourceNode = this.nodeMap.get(edge.source);
                const targetNode = this.nodeMap.get(edge.target);
                if (sourceNode) sourceNode.outDegree = (sourceNode.outDegree || 0) + 1;
                if (targetNode) targetNode.inDegree = (targetNode.inDegree || 0) + 1;
            });
        }

        // Update critical path if present
        if (update.criticalPath) {
            this.criticalPath.clear();
            update.criticalPath.forEach(edge => {
                const key = edge.source + '->' + edge.target;
                this.criticalPath.add(key);
            });
        }

        // Update counts
        document.getElementById('node-count').textContent = this.nodes.length;
        document.getElementById('edge-count').textContent = this.edges.length;

        // Restart simulation
        this.simulation.nodes(this.nodes);
        this.simulation.force('link').links(this.edges);
        this.simulation.alpha(0.3).restart();
    }

    getNodeRadius(node, isHovered = false) {
        if (!this.sizeByDegree) {
            return isHovered ? 12 : 8;  // Original fixed sizing
        }
        const totalDegree = (node.inDegree || 0) + (node.outDegree || 0);
        const minRadius = 6;
        const maxRadius = 24;
        const scale = 2;  // Pixels per connection
        const baseRadius = Math.min(maxRadius, minRadius + totalDegree * scale);
        return isHovered ? baseRadius + 4 : baseRadius;
    }

    render() {
        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;

        // Clear
        ctx.fillStyle = '#fafafa';
        ctx.fillRect(0, 0, width, height);

        ctx.save();
        ctx.translate(this.transform.x, this.transform.y);
        ctx.scale(this.transform.k, this.transform.k);

        // Pure position-based curve parameters using vis.js polar math
        const edgeCurveParams = new Map();

        // Detect multi-edges between same node pairs (bidirectional)
        const pairCounts = new Map();
        this.edges.forEach(edge => {
            const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
            const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
            // Create normalized pair key (both A→B and B→A map to same key)
            const key = sourceId < targetId ? sourceId + '|' + targetId : targetId + '|' + sourceId;
            pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
        });

        // Track index within each pair for alternating direction
        const pairIndices = new Map();

        this.edges.forEach(edge => {
            const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
            const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
            const key = sourceId < targetId ? sourceId + '|' + targetId : targetId + '|' + sourceId;

            const idx = pairIndices.get(key) || 0;
            pairIndices.set(key, idx + 1);

            const count = pairCounts.get(key) || 1;

            // Get actual node objects for position comparison
            const source = typeof edge.source === 'object' ? edge.source : this.nodeMap.get(edge.source);
            const target = typeof edge.target === 'object' ? edge.target : this.nodeMap.get(edge.target);

            // Position-aware direction: base direction determined by node positions
            // When source is left of (or at same x as) target: baseDirection = 1
            // When source is right of target: baseDirection = -1
            // This causes curves to flip when nodes cross sides
            const baseDirection = (source && target && source.x <= target.x) ? 1 : -1;

            // For parallel edges, alternate direction to create fan-out
            // Even indices use base direction, odd indices use opposite
            const direction = (idx % 2 === 0) ? baseDirection : -baseDirection;

            // Roundness: small for single edges, larger for multi-edges
            const roundness = count === 1 ? 0.2 : 0.3 + idx * 0.1;

            edgeCurveParams.set(edge, { roundness, direction });
        });

        // Draw edges
        this.edges.forEach(edge => {
            const source = typeof edge.source === 'object' ? edge.source : this.nodeMap.get(edge.source);
            const target = typeof edge.target === 'object' ? edge.target : this.nodeMap.get(edge.target);
            if (!source || !target) return;

            // Check if edge is on critical path
            const edgeKey = source.id + '->' + target.id;
            const isCritical = this.criticalPath.has(edgeKey);

            // Set style based on critical path membership
            if (isCritical) {
                ctx.strokeStyle = '#2196F3';
                ctx.lineWidth = 3;
            } else {
                ctx.strokeStyle = '#999';
                ctx.lineWidth = 1;
            }

            // Get roundness and direction (vis.js polar math adapts to positions)
            const { roundness, direction } = edgeCurveParams.get(edge) || { roundness: 0.2, direction: 1 };
            const curve = this.calculateCurvePoints(source, target, roundness, direction);

            // Draw curved edge using quadratic Bezier
            ctx.beginPath();
            ctx.moveTo(source.x, source.y);
            ctx.quadraticCurveTo(curve.cpx, curve.cpy, target.x, target.y);
            ctx.stroke();

            // Draw arrow (inherits strokeStyle, uses curve tangent)
            this.drawArrow(ctx, source, target, curve.tangentAngle);

            // Draw relation label (only if enabled)
            if (this.showEdgeLabels) {
                const midX = (source.x + target.x) / 2;
                const midY = (source.y + target.y) / 2;
                ctx.fillStyle = '#666';
                ctx.font = '10px system-ui';
                ctx.textAlign = 'center';
                ctx.fillText(edge.relation, midX, midY - 5);
            }
        });

        // Draw nodes
        this.nodes.forEach(node => {
            const isHovered = this.hoveredNode === node;
            const radius = this.getNodeRadius(node, isHovered);

            // Node circle
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
            ctx.fillStyle = this.getNodeColor(node.type);
            ctx.fill();

            if (isHovered) {
                ctx.strokeStyle = '#333';
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Label
            ctx.fillStyle = '#333';
            ctx.font = '12px system-ui';
            ctx.textAlign = 'center';
            ctx.fillText(node.label || node.id, node.x, node.y + radius + 14);
        });

        ctx.restore();
    }

    calculateCurvePoints(source, target, roundness = 0.5, direction = 1) {
        const sx = source.x, sy = source.y;
        const tx = target.x, ty = target.y;

        // vis.js polar rotation formula (note: they invert dy)
        const dx = tx - sx;
        const dy = sy - ty;  // inverted like vis.js
        const radius = Math.sqrt(dx * dx + dy * dy);

        if (radius === 0) {
            // Self-loop or same position - return straight line
            return { cpx: sx, cpy: sy, tangentAngle: 0 };
        }

        const originalAngle = Math.atan2(dy, dx);
        const factor = roundness * direction;  // direction is 1 or -1
        const myAngle = (originalAngle + (factor * 0.5 + 0.5) * Math.PI) % (2 * Math.PI);

        // Single control point (quadratic bezier) - use factor directly, not Math.abs
        const cpx = sx + (factor * 0.5 + 0.5) * radius * Math.sin(myAngle);
        const cpy = sy + (factor * 0.5 + 0.5) * radius * Math.cos(myAngle);

        // Tangent for arrow: from control point to target
        const tangentAngle = Math.atan2(ty - cpy, tx - cpx);

        return { cpx, cpy, tangentAngle };
    }

    drawArrow(ctx, sourceNode, targetNode, tangentAngle) {
        const headLen = 8;
        const nodeRadius = this.getNodeRadius(targetNode, false);

        // Position arrow endpoint at node edge along curve tangent direction
        const endX = targetNode.x - nodeRadius * Math.cos(tangentAngle);
        const endY = targetNode.y - nodeRadius * Math.sin(tangentAngle);

        // Draw arrow head pointing in tangent direction
        ctx.beginPath();
        ctx.moveTo(endX, endY);
        ctx.lineTo(endX - headLen * Math.cos(tangentAngle - Math.PI / 6), endY - headLen * Math.sin(tangentAngle - Math.PI / 6));
        ctx.moveTo(endX, endY);
        ctx.lineTo(endX - headLen * Math.cos(tangentAngle + Math.PI / 6), endY - headLen * Math.sin(tangentAngle + Math.PI / 6));
        ctx.stroke();
    }

    getNodeColor(type) {
        if (!type) return '#6366f1';
        if (this.typeColors.has(type)) return this.typeColors.get(type);

        // Hash the type string to get a consistent hue
        let hash = 0;
        for (let i = 0; i < type.length; i++) {
            hash = type.charCodeAt(i) + ((hash << 5) - hash);
        }

        // Use golden ratio to spread hues evenly
        const hue = (Math.abs(hash) * 137.508) % 360;
        const color = `hsl(${hue}, 65%, 55%)`;
        this.typeColors.set(type, color);
        return color;
    }

    findNodeAt(x, y) {
        return this.nodes.find(node => {
            const radius = this.getNodeRadius(node, false) + 4;
            const dx = node.x - x;
            const dy = node.y - y;
            return dx * dx + dy * dy < radius * radius;
        });
    }

    updateTooltip(mouseX, mouseY) {
        const tooltip = document.getElementById('tooltip');
        if (this.hoveredNode) {
            const node = this.hoveredNode;

            // Clear existing content safely
            tooltip.textContent = '';

            // Build tooltip using safe DOM APIs to prevent XSS
            const strong = document.createElement('strong');
            strong.textContent = node.label || node.id;
            tooltip.appendChild(strong);

            if (node.type) {
                tooltip.appendChild(document.createElement('br'));
                const typeSpan = document.createElement('span');
                typeSpan.textContent = 'Type: ' + node.type;
                tooltip.appendChild(typeSpan);
            }

            // Show additional properties
            const props = Object.entries(node)
                .filter(([k]) => !['id', 'label', 'type', 'x', 'y', 'vx', 'vy', 'index'].includes(k));
            props.forEach(([k, v]) => {
                tooltip.appendChild(document.createElement('br'));
                const propSpan = document.createElement('span');
                propSpan.textContent = k + ': ' + v;
                tooltip.appendChild(propSpan);
            });

            tooltip.style.display = 'block';
            tooltip.style.left = (mouseX + 15) + 'px';
            tooltip.style.top = (mouseY + 15) + 'px';
        } else {
            tooltip.style.display = 'none';
        }
    }

    hideTooltip() {
        document.getElementById('tooltip').style.display = 'none';
    }

    setConnectionStatus(status) {
        const el = document.getElementById('connection-status');
        el.className = status;
        el.textContent = {
            'connected': 'Connected',
            'disconnected': 'Disconnected - Reconnecting...',
            'connecting': 'Connecting...'
        }[status];
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.graphViz = new GraphVisualization('graph-canvas');
});
