import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import { useNavigate } from 'react-router-dom'

export default function NetworkTopology({ data, height = 600 }) {
  const svgRef = useRef()
  const navigate = useNavigate()
  const [selectedNode, setSelectedNode] = useState(null)

  useEffect(() => {
    if (!data || !data.nodes || data.nodes.length === 0) return

    // Clear previous SVG content
    d3.select(svgRef.current).selectAll('*').remove()

    const width = svgRef.current.clientWidth
    const svg = d3
      .select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height])

    // Add zoom behavior
    const g = svg.append('g')

    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      })

    svg.call(zoom)

    // Create force simulation
    const simulation = d3
      .forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.links).id(d => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40))

    // Create links
    const link = g
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(data.links)
      .join('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', d => {
        // Thicker lines for better quality
        if (d.quality === 'excellent') return 3
        if (d.quality === 'good') return 2
        return 1
      })

    // Create node groups
    const node = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(data.nodes)
      .join('g')
      .call(
        d3
          .drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended)
      )

    // Add circles to nodes
    node
      .append('circle')
      .attr('r', 20)
      .attr('fill', d => getNodeColor(d.status))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedNode(d)
      })
      .on('dblclick', (event, d) => {
        navigate(`/devices/${d.id}`)
      })

    // Add status indicator (small dot)
    node
      .append('circle')
      .attr('r', 5)
      .attr('cx', 15)
      .attr('cy', -15)
      .attr('fill', d => d.status === 'online' ? '#22c55e' : '#ef4444')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1)

    // Add labels
    node
      .append('text')
      .text(d => d.label)
      .attr('x', 0)
      .attr('y', 35)
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('fill', '#333')
      .style('pointer-events', 'none')

    // Add IP address below label
    node
      .append('text')
      .text(d => d.ip || '')
      .attr('x', 0)
      .attr('y', 48)
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#666')
      .style('pointer-events', 'none')

    // Add tooltips
    const tooltip = d3
      .select('body')
      .append('div')
      .attr('class', 'topology-tooltip')
      .style('position', 'absolute')
      .style('visibility', 'hidden')
      .style('background-color', 'white')
      .style('border', '1px solid #ddd')
      .style('border-radius', '4px')
      .style('padding', '8px')
      .style('font-size', '12px')
      .style('box-shadow', '0 2px 4px rgba(0,0,0,0.1)')
      .style('pointer-events', 'none')
      .style('z-index', '1000')

    node
      .on('mouseover', (event, d) => {
        tooltip
          .html(`
            <strong>${d.label}</strong><br/>
            IP: ${d.ip || 'N/A'}<br/>
            MAC: ${d.mac || 'N/A'}<br/>
            Status: <span style="color: ${d.status === 'online' ? '#22c55e' : '#ef4444'}">${d.status}</span>
          `)
          .style('visibility', 'visible')
      })
      .on('mousemove', (event) => {
        tooltip
          .style('top', (event.pageY - 10) + 'px')
          .style('left', (event.pageX + 10) + 'px')
      })
      .on('mouseout', () => {
        tooltip.style('visibility', 'hidden')
      })

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)

      node.attr('transform', d => `translate(${d.x},${d.y})`)
    })

    // Drag functions
    function dragstarted(event) {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      event.subject.fx = event.subject.x
      event.subject.fy = event.subject.y
    }

    function dragged(event) {
      event.subject.fx = event.x
      event.subject.fy = event.y
    }

    function dragended(event) {
      if (!event.active) simulation.alphaTarget(0)
      event.subject.fx = null
      event.subject.fy = null
    }

    // Cleanup tooltip and stop simulation on unmount to prevent memory leak
    return () => {
      simulation.stop()
      tooltip.remove()
    }
  }, [data, height, navigate])

  const getNodeColor = (status) => {
    switch (status) {
      case 'online':
        return '#3b82f6' // blue
      case 'offline':
        return '#9ca3af' // gray
      case 'pending':
        return '#f59e0b' // amber
      case 'failed':
        return '#ef4444' // red
      default:
        return '#9ca3af'
    }
  }

  return (
    <div className="network-topology">
      <svg ref={svgRef} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: '8px' }} />

      {selectedNode && (
        <div className="selected-node-info" style={{
          marginTop: '16px',
          padding: '16px',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          backgroundColor: '#f9fafb'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>Selected Device</h3>
            <button
              onClick={() => setSelectedNode(null)}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '20px',
                cursor: 'pointer',
                color: '#666'
              }}
            >
              ×
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '14px' }}>
            <div>
              <div style={{ color: '#666', marginBottom: '4px' }}>Hostname</div>
              <div style={{ fontWeight: '500' }}>{selectedNode.label}</div>
            </div>
            <div>
              <div style={{ color: '#666', marginBottom: '4px' }}>Status</div>
              <div>
                <span style={{
                  display: 'inline-block',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '12px',
                  fontWeight: '500',
                  backgroundColor: selectedNode.status === 'online' ? '#dcfce7' : '#fee2e2',
                  color: selectedNode.status === 'online' ? '#166534' : '#991b1b'
                }}>
                  {selectedNode.status}
                </span>
              </div>
            </div>
            <div>
              <div style={{ color: '#666', marginBottom: '4px' }}>IP Address</div>
              <div style={{ fontFamily: 'monospace' }}>{selectedNode.ip || 'N/A'}</div>
            </div>
            <div>
              <div style={{ color: '#666', marginBottom: '4px' }}>MAC Address</div>
              <div style={{ fontFamily: 'monospace', fontSize: '12px' }}>{selectedNode.mac || 'N/A'}</div>
            </div>
          </div>
          <button
            onClick={() => navigate(`/devices/${selectedNode.id}`)}
            style={{
              marginTop: '12px',
              width: '100%',
              padding: '8px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500'
            }}
          >
            View Device Details
          </button>
        </div>
      )}

      <div className="topology-legend" style={{
        marginTop: '16px',
        padding: '12px',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        backgroundColor: '#fafafa',
        display: 'flex',
        gap: '24px',
        flexWrap: 'wrap',
        fontSize: '14px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#3b82f6' }}></div>
          <span>Online</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#9ca3af' }}></div>
          <span>Offline</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#f59e0b' }}></div>
          <span>Pending</span>
        </div>
        <div style={{ marginLeft: 'auto', color: '#666', fontSize: '12px' }}>
          💡 Tip: Drag nodes to rearrange, double-click to view details, scroll to zoom
        </div>
      </div>
    </div>
  )
}
