const API_URL = 'http://localhost:5000/api'
export const API_BASE_URL = 'http://localhost:5000'

export const graphService = {
  // 获取图谱数据
  async getGraph() {
    const response = await fetch(`${API_URL}/graph`)
    return await response.json()
  },

  // 导入图谱数据
  async importGraph(data) {
    const response = await fetch(`${API_URL}/graph/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('导入失败')
    return await response.json()
  },

  // 导出图谱数据
  async exportGraph(data) {
    const response = await fetch(`${API_URL}/graph/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('导出失败')
    return await response.json()
  },

  // 初始化数据
  async initData(dataset = null) {
    const url = dataset ? `${API_URL}/init?dataset=${dataset}` : `${API_URL}/init`
    const response = await fetch(url, { method: 'POST' })
    if (!response.ok) throw new Error('初始化失败')
    return await response.json()
  }
}

export const personService = {
  // 添加人物
  async addPerson(data) {
    const response = await fetch(`${API_URL}/persons`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error)
    }
    return await response.json()
  },

  // 更新人物
  async updatePerson(personId, data) {
    const response = await fetch(`${API_URL}/persons/${personId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.error || '更新失败')
    }
    return await response.json()
  },

  // 删除人物
  async deletePerson(personId) {
    const response = await fetch(`${API_URL}/persons/${personId}`, {
      method: 'DELETE'
    })
    if (!response.ok) throw new Error('删除失败')
    return await response.json()
  },

  // 搜索人物
  async searchPerson(keyword, field = 'name') {
    const url = new URL(`${API_URL}/search`)
    url.searchParams.append('keyword', keyword)
    url.searchParams.append('field', field)
    const response = await fetch(url)
    return await response.json()
  }
}

export const relationshipService = {
  // 添加关系
  async addRelationship(data) {
    const response = await fetch(`${API_URL}/relationships`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error)
    }
    return await response.json()
  },

  // 删除关系
  async deleteRelationship(relId) {
    const response = await fetch(`${API_URL}/relationships/${relId}`, {
      method: 'DELETE'
    })
    if (!response.ok) throw new Error('删除失败')
    return await response.json()
  }
}

export const networkService = {
  // 查找路径
  async findPath(start, end) {
    const url = new URL(`${API_URL}/network/path`)
    url.searchParams.append('start', start)
    url.searchParams.append('end', end)
    const response = await fetch(url)
    if (!response.ok) throw new Error('查询失败')
    return await response.json()
  }
}

// 关系相关补充接口
export const relationshipServiceExtra = {
  // 获取所有关系
  async getAllRelationships() {
    const response = await fetch(`${API_URL}/relationships`)
    if (!response.ok) throw new Error('获取关系失败')
    return await response.json()
  }
}

// AI 问答服务
export const aiService = {
  // 原始接口名（保留）
  async aiAsk(question, prompt = '') {
    const response = await fetch(`${API_URL}/ai_ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, prompt })
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.error || 'AI 问答失败')
    }
    return await response.json()
  },

  // 兼容旧调用：aiService.ask(...)
  async ask(question, prompt = '') {
    return await this.aiAsk(question, prompt)
  }
}