<template>
  <div class="graph-area">
    <div class="graph-container">
      <svg ref="graphSvg" id="graph">
        <!-- 定义渐变 -->
        <defs>
          <!-- 节点默认渐变 -->
          <radialGradient id="nodeGradient" cx="30%" cy="30%">
            <stop offset="0%" style="stop-color:#a0826d;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#a0826d;stop-opacity:1" />
          </radialGradient>
          
          <!-- 选中节点渐变 -->
          <radialGradient id="selectedGradient" cx="30%" cy="30%">
            <stop offset="0%" style="stop-color:#f87171;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#ef4444;stop-opacity:1" />
          </radialGradient>
          
          <!-- 路径高亮节点渐变 -->
          <radialGradient id="pathGradient" cx="30%" cy="30%">
            <stop offset="0%" style="stop-color:#fde047;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#fbbf24;stop-opacity:1" />
          </radialGradient>
          
          <!-- 连接线渐变 -->
          <linearGradient id="linkGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#22c55e;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#10b981;stop-opacity:1" />
          </linearGradient>
          
          <!-- 箭头标记 -->
          <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <polygon points="0 0, 10 3, 0 6" fill="#334155" opacity="0.4" />
          </marker>
          
          <!-- 路径高亮箭头 -->
          <marker id="arrowhead-path" markerWidth="12" markerHeight="12" refX="11" refY="3" orient="auto">
            <polygon points="0 0, 12 3, 0 6" fill="#22c55e" opacity="1" />
          </marker>
        </defs>
      </svg>
      <div v-if="nodes.length === 0" class="empty-state">
        <div style="font-size: 64px; margin-bottom: 20px;">🕸️</div>
        <h3>暂无图谱数据</h3>
        <p>请从菜单"文件 → 加载示例"开始探索</p>
      </div>
    </div>

    <div class="status-bar">
      <div class="status-item">
        <span class="label">人物节点:</span>
        <span class="value">{{ nodes.length }}</span>
      </div>
      <div class="status-item">
        <span class="label">关系数:</span>
        <span class="value">{{ relationships.length }}</span>
      </div>
      <div v-if="selectedNode" class="status-item">
        <span class="label">已选中:</span>
        <span class="value">{{ selectedNode.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  nodes: Array,
  relationships: Array,
  selectedNode: Object,
  highlightPath: Array,
  nodeSize: Number,
  linkDistance: Number,
  chargeStrength: Number
})

const emit = defineEmits(['node-selected'])

const graphSvg = ref(null)
let d3Viewport = null
let d3LinkGroup = null
let d3LabelGroup = null
let d3NodeGroup = null
let d3Zoom = null
let d3Simulation = null
let d3Initialized = false

const drawGraph = () => {
  if (!graphSvg.value) return

  const svg = d3.select(graphSvg.value)
  const container = graphSvg.value.parentElement
  const width = container.clientWidth
  const height = container.clientHeight
  svg.attr('width', width).attr('height', height)

  // 停止正在运行的simulation，避免旧数据的计算影响性能
  if (d3Simulation) {
    d3Simulation.stop()
  }

  // 构造 links 数据（有向图）
  const links = props.relationships.map(r => {
    // 使用严格相等 ===，因为 Neo4j 的 elementId 是字符串格式
    const sourceNode = props.nodes.find(n => n.id === r.source)
    const targetNode = props.nodes.find(n => n.id === r.target)

    if (!sourceNode || !targetNode) {
      console.warn('找不到节点:', { 
        source: r.source, 
        target: r.target, 
        sourceType: typeof r.source,
        targetType: typeof r.target,
        relationship: r,
        sampleNodeIds: props.nodes.slice(0, 3).map(n => ({ id: n.id, type: typeof n.id }))
      })
      return null
    }

    return {
      source: sourceNode,
      target: targetNode,
      type: r.type,
      id: r.id
    }
  }).filter(l => l !== null)

  // 初始化（仅一次）
  if (!d3Initialized) {
    d3Viewport = svg.append('g')

    d3Zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .wheelDelta((event) => {
        const k = event.deltaMode === 1 ? 0.05 : event.deltaMode ? 1 : 0.002
        return -event.deltaY * k * 0.3
      })
      .on('zoom', (event) => {
        d3Viewport.attr('transform', event.transform)
      })
    svg.call(d3Zoom).on('dblclick.zoom', null)

    d3LinkGroup = d3Viewport.append('g')
    d3LabelGroup = d3Viewport.append('g')
    d3NodeGroup = d3Viewport.append('g')

    // 点击空白处取消选择
    svg.on('click', (event) => {
      // 如果点击的不是节点，取消选择
      if (event.target === graphSvg.value) {
        emit('node-selected', null)
      }
    })

    d3Simulation = d3.forceSimulation(props.nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(props.linkDistance))
      .force('charge', d3.forceManyBody().strength(props.chargeStrength))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(60))

    d3Simulation.on('tick', () => {
      d3LinkGroup.selectAll('line')
        .each(function(d) {
          // 计算从source到target的角度
          const dx = d.target.x - d.source.x
          const dy = d.target.y - d.source.y
          const angle = Math.atan2(dy, dx)
          
          // 获取节点半径（根据节点大小和状态）
          let targetRadius = props.nodeSize
          if (props.selectedNode && props.selectedNode.id === d.target.id) {
            targetRadius += 8
          } else if (props.highlightPath.includes(d.target.id)) {
            targetRadius += 5
          }
          
          // 箭头要停在节点边缘，留出箭头的空间（约10px）
          const arrowOffset = targetRadius + 10
          
          // 计算终点坐标
          const x2 = d.target.x - Math.cos(angle) * arrowOffset
          const y2 = d.target.y - Math.sin(angle) * arrowOffset
          
          d3.select(this)
            .attr('x1', d.source.x)
            .attr('y1', d.source.y)
            .attr('x2', x2)
            .attr('y2', y2)
        })

      d3LabelGroup.selectAll('text')
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2 - 10)

      d3NodeGroup.selectAll('g')
        .attr('transform', d => `translate(${d.x},${d.y})`)
    })

    d3Initialized = true
  } else {
    d3Simulation.force('center', d3.forceCenter(width / 2, height / 2))
    d3Simulation.force('link').distance(props.linkDistance)
    d3Simulation.force('charge').strength(props.chargeStrength)
  }

  // 更新链接 - 立即移除旧数据，快速显示新数据
  const linkSel = d3LinkGroup.selectAll('line').data(links, d => d.id)
  linkSel.exit().remove()  // 立即移除，不使用过渡动画
  
  const linkEnter = linkSel.enter().append('line').style('opacity', 0)
  linkEnter.merge(linkSel)
    .attr('class', d => {
      const inPath = props.highlightPath.length > 0 && d.source && d.target &&
        props.highlightPath.includes(d.source.id) && props.highlightPath.includes(d.target.id)
      return inPath ? 'link path-link' : 'link'
    })
    .attr('marker-end', d => {
      const inPath = props.highlightPath.length > 0 && d.source && d.target &&
        props.highlightPath.includes(d.source.id) && props.highlightPath.includes(d.target.id)
      return inPath ? 'url(#arrowhead-path)' : 'url(#arrowhead)'
    })
    .transition().duration(100).style('opacity', 1)  // 缩短动画时间到100ms

  // 更新标签 - 立即移除旧标签
  const labelSel = d3LabelGroup.selectAll('text').data(links, d => d.id)
  labelSel.exit().remove()  // 立即移除
  
  const labelEnter = labelSel.enter()
    .append('text')
    .attr('class', 'link-label')
    .attr('text-anchor', 'middle')
    .style('opacity', 0)
  
  labelEnter.merge(labelSel)
    .text(d => d.type)
    .transition().duration(100).style('opacity', 1)  // 缩短动画时间

  // 更新节点 - 立即移除旧节点
  const nodeSel = d3NodeGroup.selectAll('g').data(props.nodes, d => d.id)
  nodeSel.exit().remove()  // 立即移除，不使用过渡动画
  
  const nodeEnter = nodeSel.enter().append('g')
    .style('opacity', 0)
    .call(d3.drag()
      .clickDistance(4)  // 允许小范围移动仍算作点击
      .on('start', (event, d) => {
        if (event.sourceEvent) event.sourceEvent.stopPropagation()
        if (!event.active) d3Simulation.alphaTarget(0.15).restart()
        d.fx = d.x
        d.fy = d.y
        // 记录起始位置
        d.dragStartX = event.x
        d.dragStartY = event.y
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
        // 标记为正在拖拽
        d.isDragging = true
      })
      .on('end', (event, d) => {
        if (!event.active) d3Simulation.alphaTarget(0)
        d.fx = null
        d.fy = null
        // 延迟重置拖拽状态，避免影响点击事件
        setTimeout(() => {
          d.isDragging = false
        }, 100)
      }))

  nodeEnter.append('circle')
  nodeEnter.append('text')
    .attr('dy', 0)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')

  nodeEnter.transition().duration(100).style('opacity', 1)  // 缩短动画时间到100ms

  const allNodes = nodeEnter.merge(nodeSel)
  allNodes
    .attr('class', d => {
      const isSelected = props.selectedNode && props.selectedNode.id === d.id
      const isHighlighted = props.highlightPath.includes(d.id)
      if (isSelected && isHighlighted) return 'node selected search-result'
      if (isSelected) return 'node selected'
      if (isHighlighted) return 'node path-highlight'
      return 'node'
    })
    .select('circle')
    .attr('r', d => {
      if (props.selectedNode && props.selectedNode.id === d.id) return props.nodeSize + 8
      if (props.highlightPath.includes(d.id)) return props.nodeSize + 5
      return props.nodeSize
    })

  allNodes.select('text')
    .text(d => d.name.length > 8 ? d.name.substring(0, 6) + '...' : d.name)

  allNodes.on('click', (event, d) => {
    // 如果正在拖拽，忽略点击事件
    if (d.isDragging) {
      return
    }
    if (props.selectedNode && props.selectedNode.id === d.id) {
      emit('node-selected', null)
    } else {
      emit('node-selected', d)
      // 居中显示选中的节点
      const centerX = width / 2, centerY = height / 2
      d3.select(graphSvg.value)
        .transition().duration(800).ease(d3.easeCubicInOut)
        .call(d3Zoom.transform, d3.zoomIdentity
          .translate(centerX, centerY)
          .scale(1.2)
          .translate(-d.x, -d.y))
    }
  })

  d3Simulation.nodes(props.nodes)
  d3Simulation.force('link').links(links)
  d3Simulation.alpha(0.12).restart()
}

watch(
  () => [props.nodes, props.relationships, props.selectedNode, props.highlightPath,
         props.nodeSize, props.linkDistance, props.chargeStrength],
  () => {
    nextTick(() => {
      // 如果节点为空，立即清空画布
      if (props.nodes.length === 0) {
        if (d3LinkGroup) d3LinkGroup.selectAll('*').remove()
        if (d3LabelGroup) d3LabelGroup.selectAll('*').remove()
        if (d3NodeGroup) d3NodeGroup.selectAll('*').remove()
        if (d3Simulation) d3Simulation.stop()
      } else {
        drawGraph()
      }
    })
  },
  { deep: true }
)

onMounted(() => {
  if (props.nodes.length > 0) drawGraph()
  
  window.addEventListener('resize', () => {
    if (props.nodes.length > 0) drawGraph()
  })
})

defineExpose({ drawGraph })
</script>
