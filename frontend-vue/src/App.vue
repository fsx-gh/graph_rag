<template>
  <div id="app">
    <!-- 提示信息 -->
    <AlertMessage 
      :show="alert.show"
      :message="alert.message"
      :type="alert.type"
    />

    <!-- 菜单栏 -->
    <MenuBar
      :has-selection="!!selectedNode"
      :node-size="nodeSize"
      :link-distance="linkDistance"
      :charge-strength="chargeStrength"
      @new-graph="newGraph"
      @import-graph="triggerImport"
      @export-graph="exportGraph"
      @load-dataset="loadDataset"
      @add-person="showAddPersonPanel = true"
      @add-relation="showAddRelationPanel = true"
      @search-person="openSearchPanel"
      @delete-selected="deletePerson(selectedNode.id)"
      @find-path="openPathPanel"
      @show-stats="showStatsModal = true"
      @show-overview="showOverviewModal = true"
      @show-ranking="showCentralityRankModal = true"
      @update:node-size="nodeSizeValue = $event"
      @update:link-distance="linkDistanceValue = $event"
      @update:charge-strength="chargeStrengthValue = $event"
      @refresh="loadGraph"
      @show-ai="showAiModal = !showAiModal"
    />

    <!-- 主容器 -->
    <div class="app-container">
      <div style="display: flex; flex: 1; overflow: hidden;">
        <!-- 左侧面板 -->
        <Transition name="slide-panel">
          <LeftPanel
            v-if="selectedNode"
            :selected-node="selectedNode"
            :all-nodes="graphData.nodes"
            :all-relationships="graphData.relationships"
            @delete-person="deletePerson"
            @delete-relation="deleteRelationship"
          />
        </Transition>

        <!-- 图谱主区域 -->
        <GraphCanvas
          ref="graphCanvas"
          :nodes="graphData.nodes"
          :relationships="graphData.relationships"
          :selected-node="selectedNode"
          :highlight-path="highlightPath"
          :node-size="nodeSize"
          :link-distance="linkDistance"
          :charge-strength="chargeStrength"
          @node-selected="handleNodeSelected"
          @canvas-click="handleCanvasClick"
        />
      </div>
    </div>

    <!-- 隐藏的文件输入 -->
    <input 
      id="fileInput" 
      type="file" 
      accept=".json" 
      @change="importGraph" 
      style="display: none;"
    />

    <!-- 各种模态框 -->
    <PersonModal
      :show="showAddPersonPanel"
      @close="showAddPersonPanel = false"
      @submit="addPerson"
    />

    <RelationModal
      :show="showAddRelationPanel"
      :nodes="graphData.nodes"
      @close="showAddRelationPanel = false"
      @submit="addRelationship"
    />

    <SearchModal
      :show="showSearchPanel"
      @close="showSearchPanel = false"
      @search="advancedSearch"
    />

    <PathModal
      :show="showPathPanel"
      :nodes="graphData.nodes"
      :path="currentPath"
      :distance="pathDistance"
      :error="pathError"
      @close="closePathPanel"
      @find-path="findPath"
    />

    <!-- 统计信息 -->
    <StatsModal
      :show="showStatsModal"
      @close="showStatsModal = false"
    />

    <!-- 图谱导览 -->
    <OverviewModal
      :show="showOverviewModal"
      @close="showOverviewModal = false"
      @highlight-node="highlightNode"
    />

    <!-- 关键人物排序 -->
    <CentralityRankModal
      :show="showCentralityRankModal"
      @close="showCentralityRankModal = false"
      @highlight-node="highlightNode"
    />
    <AiModal
      :show="showAiModal"
      @close="showAiModal = false"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import MenuBar from './components/MenuBar.vue'
import AiModal from './components/AiModal.vue'
import LeftPanel from './components/LeftPanel.vue'
import GraphCanvas from './components/GraphCanvas.vue'
import AlertMessage from './components/AlertMessage.vue'
import PersonModal from './components/PersonModal.vue'
import RelationModal from './components/RelationModal.vue'
import SearchModal from './components/SearchModal.vue'
import PathModal from './components/PathModal.vue'
import StatsModal from './components/StatsModal.vue'
import OverviewModal from './components/OverviewModal.vue'
import CentralityRankModal from './components/CentralityRankModal.vue'
import { graphService, personService, relationshipService, networkService } from './services/api'

const loading = ref(false)
const selectedNode = ref(null)
const alert = reactive({
  show: false,
  type: 'success',
  message: ''
})

const showCentralityRankModal = ref(false)
const showStatsModal = ref(false)
const showOverviewModal = ref(false)
const showAiModal = ref(false)
const showAddPersonPanel = ref(false)
const showAddRelationPanel = ref(false)
const showSearchPanel = ref(false)
const showPathPanel = ref(false)

const graphData = reactive({
  nodes: [],
  relationships: []
})

const pathError = ref('')
const highlightPath = ref([])
const currentPath = ref([])
const pathDistance = ref(0)
const graphCanvas = ref(null)

// 图谱参数
const nodeSizeValue = ref(35)
const linkDistanceValue = ref(150)
const chargeStrengthValue = ref(-500)

const nodeSize = computed(() => {
  return nodeSizeValue.value
})

const linkDistance = computed(() => {
  return linkDistanceValue.value
})

const chargeStrength = computed(() => {
  return chargeStrengthValue.value
})

// 显示提示信息
const showAlert = (message, type = 'success') => {
  alert.message = message
  alert.type = type
  alert.show = true
  setTimeout(() => {
    alert.show = false
  }, 3000)
}

// 处理节点选择
const handleNodeSelected = (node) => {
  selectedNode.value = node
  highlightPath.value = []
  currentPath.value = []
  pathDistance.value = 0
}

// 点击画布空白处
// 点击画布空白处
const handleCanvasClick = () => {
  selectedNode.value = null
}

// 新建图谱
const newGraph = () => {
  if (graphData.nodes.length > 0) {
    if (!confirm('确定清空当前图谱?')) return
  }
  graphData.nodes = []
  graphData.relationships = []
  selectedNode.value = null
  showAlert('新建成功')
}

// 加载图谱
const loadGraph = async () => {
  try {
    loading.value = true
    // 先立即清空旧数据，让界面响应更快
    graphData.nodes = []
    graphData.relationships = []
    selectedNode.value = null
    await nextTick()
    
    // 再加载新数据
    const data = await graphService.getGraph()
    graphData.nodes = data.nodes
    graphData.relationships = data.relationships
    await nextTick()
    graphCanvas.value?.drawGraph()
  } catch (error) {
    showAlert('无法连接后端服务', 'error')
  } finally {
    loading.value = false
  }
}

// 添加人物
const addPerson = async (personData) => {
  try {
    loading.value = true
    const created = await personService.addPerson(personData)
    graphData.nodes.push({
      id: created.id,
      name: created.name,
      age: created.age ?? null,
      occupation: created.occupation ?? null,
      description: created.description ?? ''
    })
    showAlert('人物添加成功')
    await nextTick()
    graphCanvas.value?.drawGraph()
    showAddPersonPanel.value = false
  } catch (error) {
    showAlert('添加失败: ' + error.message, 'error')
  } finally {
    loading.value = false
  }
}

// 添加关系
const addRelationship = async (relationData) => {
  try {
    loading.value = true
    const rel = await relationshipService.addRelationship(relationData)
    graphData.relationships.push({
      id: rel.id,
      source: rel.source,
      target: rel.target,
      type: rel.type
    })
    showAlert('关系建立成功')
    await nextTick()
    graphCanvas.value?.drawGraph()
    showAddRelationPanel.value = false
  } catch (error) {
    showAlert('建立失败: ' + error.message, 'error')
  } finally {
    loading.value = false
  }
}

// 删除人物
const deletePerson = async (personId) => {
  try {
    loading.value = true
    await personService.deletePerson(personId)
    graphData.nodes = graphData.nodes.filter(n => n.id !== personId)
    graphData.relationships = graphData.relationships.filter(
      r => r.source !== personId && r.target !== personId
    )
    selectedNode.value = null
    showAlert('人物删除成功')
    await nextTick()
    graphCanvas.value?.drawGraph()
  } catch (error) {
    showAlert('删除失败: ' + error.message, 'error')
  } finally {
    loading.value = false
  }
}

// 删除关系
const deleteRelationship = async (relId) => {
  try {
    loading.value = true
    await relationshipService.deleteRelationship(relId)
    graphData.relationships = graphData.relationships.filter(r => r.id !== relId)
    showAlert('关系删除成功')
    await nextTick()
    graphCanvas.value?.drawGraph()
  } catch (error) {
    showAlert('删除失败: ' + error.message, 'error')
  } finally {
    loading.value = false
  }
}

// 搜索人物
const advancedSearch = async ({ keyword, field }) => {
  try {
    loading.value = true
    const results = await personService.searchPerson(keyword, field)
    
    if (results.length > 0) {
      currentPath.value = []
      pathDistance.value = 0
      highlightPath.value = results.map(r => r.id)
      selectedNode.value = results[0]
      showSearchPanel.value = false
      await nextTick()
      graphCanvas.value?.drawGraph()
      showAlert(`找到 ${results.length} 个相关人物`)
    } else {
      showAlert('未找到匹配结果', 'error')
    }
  } catch (error) {
    showAlert('搜索失败: ' + error.message, 'error')
  } finally {
    loading.value = false
  }
}

// 查找路径
const findPath = async ({ start, end }) => {
  try {
    loading.value = true
    pathError.value = ''
    const data = await networkService.findPath(start, end)
    // 后端返回的是 {name, pathLength}，需要将名字转换为节点ID
    const pathNodeNames = (data.nodes || []).map(n => n.name)
    
    if (!pathNodeNames || pathNodeNames.length === 0) {
      pathError.value = '两点之间不存在路径'
      highlightPath.value = []
      currentPath.value = []
      return
    }
    
    // 将名字转换为节点ID（为了在graph canvas中高亮显示）
    const pathNodeIds = pathNodeNames.map(name => {
      const node = graphData.nodes.find(n => n.name === name)
      return node ? node.id : null
    }).filter(id => id !== null)
    
    pathError.value = ''
    highlightPath.value = pathNodeIds
    currentPath.value = pathNodeNames  // 存储名字供PathModal使用
    pathDistance.value = data.pathLength || 0
    selectedNode.value = null
    
    await nextTick()
    graphCanvas.value?.drawGraph()
  } catch (error) {
    pathError.value = '路径查询失败: ' + error.message
    highlightPath.value = []
    currentPath.value = []
  } finally {
    loading.value = false
  }
}

// 导出图谱
const exportGraph = async () => {
  try {
    const result = await graphService.exportGraph(graphData)
    showAlert(`导出成功：${result.filename}`)
  } catch (error) {
    showAlert('导出失败', 'error')
  }
}

// 触发导入
const triggerImport = () => {
  document.getElementById('fileInput').click()
}

// 导入图谱
const importGraph = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  try {
    loading.value = true
    // 清空高亮状态
    highlightPath.value = []
    currentPath.value = []
    selectedNode.value = null
    
    const text = await file.text()
    const data = JSON.parse(text)
    
    if (!data.nodes || !Array.isArray(data.nodes)) {
      throw new Error('节点数据格式错误')
    }
    
    // Neo4j 使用字符串 ID，不需要转换
    
    await graphService.importGraph(data)
    showAlert('导入成功')
    document.getElementById('fileInput').value = ''
    await loadGraph()
  } catch (error) {
    showAlert('导入失败: ' + error.message, 'error')
  } finally {
    loading.value = false
  }
}

// 加载数据集
const loadDataset = async (dataset) => {
  try {
    loading.value = true
    // 立即清空旧数据
    graphData.nodes = []
    graphData.relationships = []
    selectedNode.value = null
    highlightPath.value = []
    currentPath.value = []
    await nextTick()
    
    await graphService.initData(dataset)
    
    const datasetNames = {
      'qing-dynasty': '清朝历史',
      'journey-to-west': '西游记',
      'dream-of-red-mansion': '红楼梦',
      'four-gen-family': '四代家谱树',
      'water-margin': '水浒传'
    }
    showAlert(`${datasetNames[dataset] || dataset}数据加载成功`)
    await loadGraph()
  } catch (error) {
    showAlert('加载失败: ' + error.message, 'error')
  } finally {
    loading.value = false
  }
}

// 打开搜索面板
const openSearchPanel = () => {
  highlightPath.value = []
  currentPath.value = []
  showSearchPanel.value = true
}

// 打开路径面板
const openPathPanel = () => {
  highlightPath.value = []
  currentPath.value = []
  showPathPanel.value = true
}

// 关闭路径面板
const closePathPanel = () => {
  showPathPanel.value = false
  pathError.value = ''
}

// 高亮指定节点
const highlightNode = (nodeId) => {
  highlightPath.value = [nodeId]
  const node = graphData.nodes.find(n => n.id === nodeId)
  if (node) {
    selectedNode.value = node
  }
  nextTick(() => {
    graphCanvas.value?.drawGraph()
  })
}

// 查看社区详情
const viewCommunity = ({ members }) => {
  // 高亮社区内所有成员
  const communityNodeIds = members.map(m => m.id)
  highlightPath.value = communityNodeIds
  
  // 聚焦到社区中心
  if (members.length > 0) {
    selectedNode.value = members[0]
  }
  
  showCommunityModal.value = false
  
  nextTick(() => {
    graphCanvas.value?.drawGraph()
  })
}

onMounted(() => {
  loadGraph()
})
</script>

<style>
@import './styles/main.css';
</style>
