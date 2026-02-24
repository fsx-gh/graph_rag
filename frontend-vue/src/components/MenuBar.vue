<template>
  <div class="menubar">
    <div class="menu-left">
      <div class="app-title">
        <span class="icon">🕸️</span>
        <span class="title">人物关联知识图谱</span>
      </div>
    </div>

    <div class="menu-center">
      <!-- 文件菜单 -->
      <div class="menu-item dropdown">
        <button @click="toggleMenu('file')">文件</button>
        <div v-if="activeMenu === 'file'" class="dropdown-menu">
          <div class="menu-option" @click="$emit('new-graph'); closeMenu()">📄 新建</div>
          <div class="menu-option" @click="$emit('import-graph'); closeMenu()">📂 打开...</div>
          <div class="menu-option" @click="$emit('export-graph'); closeMenu()">💾 导出</div>
          <div class="divider"></div>
          <div class="menu-option" @click="$emit('load-dataset', 'qing-dynasty'); closeMenu()">📦 清朝历史</div>
          <div class="menu-option" @click="$emit('load-dataset', 'journey-to-west'); closeMenu()">📖 西游记</div>
          <div class="menu-option" @click="$emit('load-dataset', 'dream-of-red-mansion'); closeMenu()">🏮 红楼梦</div>
          <div class="menu-option" @click="$emit('load-dataset', 'four-gen-family'); closeMenu()">🌳 四代家谱树</div>
          <div class="menu-option" @click="$emit('load-dataset', 'water-margin'); closeMenu()">🏹 水浒传</div>
          <div class="menu-option" @click="$emit('load-dataset', 'advanced-analysis'); closeMenu()">🔬 高级分析测试</div>
        </div>
      </div>

      <!-- 编辑菜单 -->
      <div class="menu-item dropdown">
        <button @click="toggleMenu('edit')">编辑</button>
        <div v-if="activeMenu === 'edit'" class="dropdown-menu">
          <div class="menu-option" @click="$emit('add-person'); closeMenu()">➕ 添加人物</div>
          <div class="menu-option" @click="$emit('add-relation'); closeMenu()">🔗 添加关系</div>
          <div class="menu-option" @click="$emit('search-person'); closeMenu()">🔍 搜索人物</div>
          <div class="divider"></div>
          <div v-if="hasSelection" class="menu-option danger" @click="$emit('delete-selected'); closeMenu()">❌ 删除选中</div>
        </div>
      </div>

      <!-- 分析菜单 -->
      <div class="menu-item dropdown">
        <button @click="toggleMenu('analysis')">📊 分析</button>
        <div v-if="activeMenu === 'analysis'" class="dropdown-menu">
          <div class="menu-option" @click="$emit('show-stats'); closeMenu()">📈 图谱统计</div>
          <div class="menu-option" @click="$emit('show-overview'); closeMenu()">📚 图谱导览</div>
          <div class="menu-option" @click="$emit('show-ranking'); closeMenu()">👑 关键人物</div>
          <div class="divider"></div>
          <div class="menu-option" @click="$emit('find-path'); closeMenu()">🔗 路径查询</div>
        </div>
      </div>

      <!-- 刷新图谱 -->
      <div class="menu-item">
        <button @click="$emit('refresh')">🔄 刷新图谱</button>
      </div>
      <!-- AI 问答 -->
      <div class="menu-item">
        <button @click="$emit('show-ai')">🧠 AI 问答</button>
      </div>
    </div>

    <!-- 参数调节 -->
    <div class="settings-panel">
      <div class="setting-item">
        <label>节点大小:</label>
        <input 
          type="range" 
          :value="nodeSize" 
          @input="$emit('update:nodeSize', parseInt($event.target.value))"
          min="30" 
          max="60" 
          step="5"
          class="slider">
        <span class="slider-value">{{ nodeSize }}</span>
      </div>
      <div class="setting-item">
        <label>路径距离:</label>
        <input 
          type="range" 
          :value="linkDistance" 
          @input="$emit('update:linkDistance', parseInt($event.target.value))"
          min="80" 
          max="300" 
          step="20"
          class="slider">
        <span class="slider-value">{{ linkDistance }}</span>
      </div>
      <div class="setting-item">
        <label>排斥力:</label>
        <input 
          type="range" 
          :value="chargeStrength" 
          @input="$emit('update:chargeStrength', parseInt($event.target.value))"
          min="-1500" 
          max="-100" 
          step="100"
          class="slider">
        <span class="slider-value">{{ chargeStrength }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

defineProps({
  hasSelection: Boolean,
  nodeSize: Number,
  linkDistance: Number,
  chargeStrength: Number
})

defineEmits([
  'new-graph',
  'import-graph',
  'export-graph',
  'load-dataset',
  'add-person',
  'add-relation',
  'search-person',
  'delete-selected',
  'find-path',
  'show-centrality',
  'show-communities',
  'show-influence',
  'show-recommend',
  'show-triangles',
  'show-pattern',
  'show-ai',
  'show-similarity',
  'show-density',
  'refresh',
  'update:nodeSize',
  'update:linkDistance',
  'update:chargeStrength'
])

const activeMenu = ref(null)

const toggleMenu = (menu) => {
  activeMenu.value = activeMenu.value === menu ? null : menu
}

const closeMenu = () => {
  activeMenu.value = null
}

// 点击任何地方都关闭菜单（除非点击的是菜单按钮）
const handleClickOutside = (event) => {
  const menuButtons = document.querySelectorAll('.menu-item button')
  const isClickingMenuButton = Array.from(menuButtons).some(btn => btn.contains(event.target))
  
  if (!isClickingMenuButton) {
    closeMenu()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.menubar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  position: relative;
  z-index: 100;
}

.menu-left {
  display: flex;
  align-items: center;
}

.app-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: white;
  font-weight: 600;
  font-size: 18px;
}

.app-title .icon {
  font-size: 24px;
}

.menu-center {
  display: flex;
  gap: 5px;
  flex: 1;
  justify-content: center;
}

.menu-item {
  position: relative;
}

.menu-item button {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
}

.menu-item button:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 5px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  min-width: 180px;
  z-index: 1000;
  overflow: hidden;
}

.menu-option {
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  color: #333;
}

.menu-option:hover {
  background: #f0f0f0;
}

.menu-option.danger {
  color: #f44336;
}

.menu-option.danger:hover {
  background: #ffebee;
}

.divider {
  height: 1px;
  background: #e0e0e0;
  margin: 5px 0;
}

.settings-panel {
  display: flex;
  gap: 15px;
  align-items: center;
}

.setting-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.setting-item label {
  color: white;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  min-width: 60px;
}

.slider {
  width: 100px;
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.3);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  transition: all 0.2s;
}

.slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 4px 8px rgba(0,0,0,0.3);
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  transition: all 0.2s;
}

.slider::-moz-range-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 4px 8px rgba(0,0,0,0.3);
}

.slider-value {
  color: white;
  font-size: 12px;
  font-weight: 600;
  min-width: 30px;
  text-align: right;
}
</style>
