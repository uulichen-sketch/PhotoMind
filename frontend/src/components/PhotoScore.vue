<template>
  <div class="photo-score">
    <div class="overall-score">
      <div class="score-circle" :style="circleStyle">
        <span class="score-value">{{ overallScore }}</span>
        <span class="score-max">/5</span>
      </div>
      <div class="score-label">综合评分</div>
    </div>

    <div class="score-details">
      <div v-for="item in scoreItems" :key="item.key" class="score-item">
        <div class="score-item-header">
          <span class="item-icon">{{ item.icon }}</span>
          <span class="item-name">{{ item.name }}</span>
          <span class="item-value">{{ getScore(item.key) }}</span>
        </div>
        <div class="score-bar">
          <div
            class="score-bar-fill"
            :style="{ width: `${(getScore(item.key) / 5) * 100}%`, background: item.color }"
          />
        </div>
      </div>
    </div>

    <div v-if="scores?.reason" class="score-reason">
      <div class="reason-header">
        <span class="reason-icon">📝</span>
        <span>评分理由</span>
      </div>
      <p class="reason-text">{{ scores.reason }}</p>
    </div>

    <div v-if="scoreSuggestions.length" class="score-suggestions">
      <div class="reason-header">
        <span class="reason-icon">📷</span>
        <span>拍摄建议</span>
      </div>
      <ul class="suggestion-list">
        <li v-for="(item, idx) in scoreSuggestions" :key="`${idx}-${item}`">
          {{ item }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  scores: {
    type: Object,
    default: null
  }
})

const scoreItems = [
  { key: 'composition', name: '构图', icon: '📐', color: 'linear-gradient(90deg, #6366f1, #8b5cf6)' },
  { key: 'color', name: '色彩', icon: '🎨', color: 'linear-gradient(90deg, #f59e0b, #fbbf24)' },
  { key: 'lighting', name: '光线', icon: '💡', color: 'linear-gradient(90deg, #06b6d4, #22d3ee)' },
  { key: 'sharpness', name: '清晰度', icon: '🔍', color: 'linear-gradient(90deg, #10b981, #34d399)' }
]

const getScore = (key) => {
  return props.scores?.[key] || 0
}

const overallScore = computed(() => {
  return props.scores?.overall?.toFixed(1) || '0.0'
})

const scoreSuggestions = computed(() => {
  const suggestions = props.scores?.suggestions
  if (!Array.isArray(suggestions)) return []
  return suggestions.filter(Boolean)
})

const circleStyle = computed(() => {
  const score = parseFloat(overallScore.value)
  const percentage = (score / 5) * 100
  const color = getScoreColor(score)

  return {
    background: `conic-gradient(${color} ${percentage}%, #e2e8f0 ${percentage}%)`
  }
})

const getScoreColor = (score) => {
  if (score >= 4.5) return '#10b981'
  if (score >= 4.0) return '#6366f1'
  if (score >= 3.0) return '#f59e0b'
  return '#ef4444'
}
</script>

<style scoped>
.photo-score {
  background: var(--bg-color);
  border-radius: var(--radius);
  padding: 20px;
}

.overall-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px dashed var(--border-color);
}

.score-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 12px;
}

.score-circle::before {
  content: '';
  position: absolute;
  inset: 8px;
  background: var(--card-bg);
  border-radius: 50%;
}

.score-value {
  position: relative;
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.score-max {
  position: relative;
  font-size: 14px;
  color: var(--text-muted);
  margin-left: 2px;
}

.score-label {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.score-details {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.score-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.score-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-icon {
  font-size: 16px;
}

.item-name {
  flex: 1;
  font-size: 14px;
  color: var(--text-secondary);
}

.item-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.score-bar {
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.score-reason {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed var(--border-color);
}

.reason-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.reason-icon {
  font-size: 16px;
}

.reason-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
  margin: 0;
}

.score-suggestions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed var(--border-color);
}

.suggestion-list {
  margin: 0;
  padding-left: 18px;
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
  gap: 8px;
  line-height: 1.6;
  font-size: 14px;
}

.photo-score.compact {
  padding: 16px;
}

.photo-score.compact .overall-score {
  flex-direction: row;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 16px;
}

.photo-score.compact .score-circle {
  width: 60px;
  height: 60px;
}

.photo-score.compact .score-circle::before {
  inset: 6px;
}

.photo-score.compact .score-value {
  font-size: 20px;
}

.photo-score.compact .score-max {
  font-size: 12px;
}

.photo-score.mini {
  padding: 0;
  background: transparent;
}

.photo-score.mini .overall-score {
  flex-direction: row;
  gap: 8px;
  margin: 0;
  padding: 0;
  border: none;
  align-items: center;
}

.photo-score.mini .score-circle {
  width: 36px;
  height: 36px;
}

.photo-score.mini .score-circle::before {
  inset: 4px;
}

.photo-score.mini .score-value {
  font-size: 14px;
}

.photo-score.mini .score-max {
  font-size: 10px;
  display: none;
}

.photo-score.mini .score-label {
  font-size: 12px;
}

.photo-score.mini .score-details,
.photo-score.mini .score-reason,
.photo-score.mini .score-suggestions {
  display: none;
}
</style>
