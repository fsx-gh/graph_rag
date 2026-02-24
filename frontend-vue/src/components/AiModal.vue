<template>
  <div v-if="show" class="ai-floating ai-compact">
    <div class="ai-modal">
      <textarea
        ref="inputEl"
        class="ai-input"
        v-model="question"
        placeholder="请输入问题（必填）"
        @keydown="handleKeydown"
        @input="handleInput"
        rows="1"
      ></textarea>

      <div class="ai-output">
        <div class="output-toolbar" v-if="answer || error">
          <div class="output-actions">
            <button class="small" @click="copyAnswer" title="复制回答">复制</button>
          </div>
        </div>

        <div v-if="loading" class="loading"><span class="spinner"></span>正在请求 AI，请稍候…</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else>
          <div class="answer" v-text="answer"></div>
          <div class="evidence" v-if="evidence.length">
            <div class="evidence-title">证据</div>
            <div class="evidence-list">
              <div class="item" v-for="(ev, idx) in evidence" :key="idx">
                <div><strong>ID:</strong> {{ ev.node_id || ev.id || ev.source || ev.target }}</div>
                <div v-if="ev.node_name"><strong>名称:</strong> {{ ev.node_name }}</div>
                <div v-if="ev.relation"><strong>关系:</strong> {{ ev.relation }}</div>
                <div v-if="ev.snippet"><em>{{ ev.snippet }}</em></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { aiService } from '../services/api'
import '../styles/ai-modal.css'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['close'])

const question = ref('')
const loading = ref(false)
  const answer = ref('')
  const evidence = ref([])
  const error = ref('')

watch(() => props.show, (v) => {
  if (!v) {
    // reset when closed
    question.value = ''
    loading.value = false
    answer.value = ''
    error.value = ''
  }
})

const ask = async () => {
  if (!question.value) return
  loading.value = true
  answer.value = ''
  error.value = ''
    try {
    const res = await aiService.ask(question.value)
    // res.answer may be plain text or a JSON string with structured fields
    let mainText = ''
    evidence.value = []
    if (res && typeof res.answer === 'string') {
      try {
        const parsed = JSON.parse(res.answer)
        if (parsed && typeof parsed === 'object') {
          mainText = parsed.answer || ''
          if (Array.isArray(parsed.evidence)) evidence.value = parsed.evidence
          if (!mainText && parsed.explanation) mainText = parsed.explanation
        } else {
          mainText = res.answer
        }
      } catch (err) {
        mainText = res.answer
      }
    } else if (res && typeof res === 'object') {
      if (res.answer) mainText = res.answer
      if (res.evidence) evidence.value = res.evidence
      if (!mainText) mainText = JSON.stringify(res, null, 2)
    } else {
      mainText = String(res)
    }
    answer.value = mainText || ''
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

const copyAnswer = async () => {
  try {
    await navigator.clipboard.writeText(answer.value || '')
  } catch (e) {
    // ignore
  }
}

const handleKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    // send if not already loading and there is content
    if (!loading.value && question.value) ask()
  }
}

const inputEl = ref(null)

const autosize = () => {
  const el = inputEl.value
  if (!el) return
  el.style.height = 'auto'
  const max = 160
  if (el.scrollHeight > max) {
    el.style.height = max + 'px'
    el.style.overflowY = 'auto'
  } else {
    el.style.height = el.scrollHeight + 'px'
    el.style.overflowY = 'hidden'
  }
}

const handleInput = () => {
  autosize()
}

onMounted(() => {
  autosize()
})
</script>

