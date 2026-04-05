<template>
  <div class="topology-page">
    <div class="toolbar">
      <div class="left">
        <el-select v-model="selectedSystem" placeholder="全部业务系统" clearable style="width:200px" @change="loadTopology">
          <el-option v-for="s in systems" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-button @click="loadTopology" :icon="Refresh">刷新</el-button>
      </div>
      <div class="right">
        <el-button-group>
          <el-button :type="layout==='force'?'primary':''" @click="layout='force'">力导向</el-button>
          <el-button :type="layout==='dagre'?'primary':''" @click="layout='dagre'">层次</el-button>
        </el-button-group>
        <el-button-group>
          <el-button :icon="ZoomIn" @click="zoomIn" />
          <el-button :icon="ZoomOut" @click="zoomOut" />
          <el-button :icon="RefreshRight" @click="resetZoom" />
        </el-button-group>
      </div>
    </div>

    <div class="canvas" ref="canvasRef">
      <svg ref="svgRef" :viewBox="viewBox" class="topology-svg">
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#909399" />
          </marker>
        </defs>
        <g v-for="edge in edges" :key="edge.source+'-'+edge.target">
          <line
            :x1="getNode(edge.source)?.x || 0"
            :y1="getNode(edge.source)?.y || 0"
            :x2="getNode(edge.target)?.x || 0"
            :y2="getNode(edge.target)?.y || 0"
            stroke="#909399"
            stroke-width="2"
            marker-end="url(#arrowhead)"
          />
          <text
            :x="(getNode(edge.source)?.x + getNode(edge.target)?.x)/2"
            :y="(getNode(edge.source)?.y + getNode(edge.target)?.y)/2 - 5"
            font-size="10"
            fill="#909399"
          >{{ edge.label }}</text>
        </g>
        <g
          v-for="node in nodes"
          :key="node.id"
          class="node"
          :transform="`translate(${node.x || 0}, ${node.y || 0})`"
          @click="showDetail(node)"
        >
          <rect x="-40" y="-25" width="80" height="50" rx="6" :fill="getNodeColor(node.type)" stroke="#dcdfe6" />
          <text y="5" text-anchor="middle" font-size="20">{{ getNodeIcon(node.icon) }}</text>
          <text y="25" text-anchor="middle" font-size="12" fill="#303133">{{ node.name }}</text>
          <text y="38" text-anchor="middle" font-size="10" fill="#909399">{{ node.host }}</text>
        </g>
      </svg>
    </div>

    <el-drawer v-model="detailVisible" :title="detailData.name" size="400px">
      <div class="detail-content">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="类型">{{ getTypeName(detailData.type) }}</el-descriptions-item>
          <el-descriptions-item label="主机">{{ detailData.host }}</el-descriptions-item>
          <el-descriptions-item label="端口" v-if="detailData.port">{{ detailData.port }}</el-descriptions-item>
          <el-descriptions-item label="业务系统" v-if="detailData.business_system">{{ detailData.business_system }}</el-descriptions-item>
          <el-descriptions-item label="环境" v-if="detailData.env">{{ detailData.env }}</el-descriptions-item>
          <el-descriptions-item label="负责人" v-if="detailData.owner">{{ detailData.owner }}</el-descriptions-item>
          <el-descriptions-item label="备注" v-if="detailData.remark">{{ detailData.remark }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { topologyAPI, systemsAPI } from '@/api/services'
import { Refresh, ZoomIn, ZoomOut, RefreshRight } from '@element-plus/icons-vue'

const canvasRef = ref(null)
const svgRef = ref(null)
const nodes = ref([])
const edges = ref([])
const systems = ref([])
const selectedSystem = ref(null)
const layout = ref('force')
const detailVisible = ref(false)
const detailData = ref({})
const viewBox = ref('0 0 1200 800')
const zoom = ref(1)

const nodePositions = ref({})

const getNode = (id) => nodePositions.value[id]

const getNodeColor = (type) => {
  const colors = { host: '#e6f7ff', database: '#f6ffed', middleware: '#fff7e6' }
  return colors[type] || '#ffffff'
}

const getNodeIcon = (icon) => {
  const icons = { Monitor: '🖥', Grid: '🗄', Connection: '🔗' }
  return icons[icon] || '📦'
}

const getTypeName = (type) => {
  const names = { host: '主机', database: '数据库', middleware: '中间件' }
  return names[type] || type
}

const loadTopology = async () => {
  try {
    const res = await topologyAPI.getTopology(selectedSystem.value)
    nodes.value = res.nodes || []
    edges.value = res.edges || []
    applyLayout()
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const loadSystems = async () => {
  try {
    const res = await systemsAPI.list()
    systems.value = res.systems || []
  } catch (e) {
    console.error(e)
  }
}

// Simple force-directed layout
const applyLayout = () => {
  const width = 1200
  const height = 800

  // Initialize positions randomly
  nodes.value.forEach((n, i) => {
    n.x = (i % 5) * 200 + 100 + Math.random() * 50
    n.y = Math.floor(i / 5) * 150 + 100 + Math.random() * 50
  })

  // Simple iterative layout
  for (let iter = 0; iter < 50; iter++) {
    const forces = {}
    nodes.value.forEach(n => { forces[n.id] = { x: 0, y: 0 } })

    // Repulsion between nodes
    for (let i = 0; i < nodes.value.length; i++) {
      for (let j = i + 1; j < nodes.value.length; j++) {
        const n1 = nodes.value[i], n2 = nodes.value[j]
        const dx = n1.x - n2.x, dy = n1.y - n2.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = 50000 / (dist * dist)
        forces[n1.id].x += (dx / dist) * force
        forces[n1.id].y += (dy / dist) * force
        forces[n2.id].x -= (dx / dist) * force
        forces[n2.id].y -= (dy / dist) * force
      }
    }

    // Attraction along edges
    edges.value.forEach(e => {
      const n1 = nodes.value.find(n => n.id === e.source)
      const n2 = nodes.value.find(n => n.id === e.target)
      if (n1 && n2) {
        const dx = n2.x - n1.x, dy = n2.y - n1.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = dist * 0.1
        forces[n1.id].x += (dx / dist) * force
        forces[n1.id].y += (dy / dist) * force
        forces[n2.id].x -= (dx / dist) * force
        forces[n2.id].y -= (dy / dist) * force
      }
    })

    // Apply forces
    nodes.value.forEach(n => {
      n.x += forces[n.id].x * 0.5
      n.y += forces[n.id].y * 0.5
      // Bounds
      n.x = Math.max(50, Math.min(width - 50, n.x))
      n.y = Math.max(50, Math.min(height - 50, n.y))
    })
  }

  nodePositions.value = {}
  nodes.value.forEach(n => { nodePositions.value[n.id] = { x: n.x, y: n.y } })
}

const showDetail = async (node) => {
  try {
    const [type, id] = node.id.split('_')
    const res = await topologyAPI.getNodeDetail(type, id)
    detailData.value = res
    detailVisible.value = true
  } catch (e) {
    ElMessage.error('获取详情失败')
  }
}

const zoomIn = () => {
  zoom.value = Math.min(2, zoom.value + 0.2)
  updateViewBox()
}

const zoomOut = () => {
  zoom.value = Math.max(0.4, zoom.value - 0.2)
  updateViewBox()
}

const resetZoom = () => {
  zoom.value = 1
  updateViewBox()
}

const updateViewBox = () => {
  const w = 1200 / zoom.value
  const h = 800 / zoom.value
  const x = (1200 - w) / 2
  const y = (800 - h) / 2
  viewBox.value = `${x} ${y} ${w} ${h}`
}

onMounted(() => {
  loadSystems()
  loadTopology()
})
</script>

<style scoped>
.topology-page { display: flex; flex-direction: column; height: 100vh; background: #fafafa; }
.toolbar { display: flex; justify-content: space-between; padding: 12px 16px; background: #fff; border-bottom: 1px solid #e4e7ed; }
.toolbar .left, .toolbar .right { display: flex; gap: 8px; align-items: center; }
.canvas { flex: 1; overflow: hidden; }
.topology-svg { width: 100%; height: 100%; cursor: grab; }
.node { cursor: pointer; transition: transform 0.1s; }
.node:hover rect { stroke: #409eff; stroke-width: 2; }
.detail-content { padding: 16px; }
</style>