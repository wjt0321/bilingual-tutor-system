/**
 * Progress Visualization JavaScript
 * 进度可视化脚本
 */

class ProgressVisualization {
    constructor() {
        this.charts = new Map();
        this.progressData = null;
        this.init();
    }
    
    init() {
        this.loadProgressData();
        this.bindEvents();
    }
    
    bindEvents() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-progress');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshProgress());
        }
        
        // Time range selector
        const timeRange = document.getElementById('time-range');
        if (timeRange) {
            timeRange.addEventListener('change', (e) => this.updateTimeRange(e.target.value));
        }
    }
    
    async loadProgressData() {
        try {
            BilingualTutor.showToast('加载进度数据...', 'info', 1000);
            
            const response = await BilingualTutor.apiRequest('/api/progress/status');
            if (response.success) {
                this.progressData = response.progress;
                this.renderProgressVisualization();
                BilingualTutor.showToast('进度数据已更新', 'success');
            } else {
                throw new Error(response.message);
            }
        } catch (error) {
            BilingualTutor.showToast('加载进度数据失败', 'error');
            this.renderErrorState();
        }
    }
    
    renderProgressVisualization() {
        this.renderOverallProgress();
        this.renderLanguageProgress();
        this.renderVocabularyStats();
        this.renderLearningStreak();
        this.renderWeaknessAnalysis();
        this.renderSystemHealth();
    }
    
    renderOverallProgress() {
        const container = document.getElementById('overall-progress');
        if (!container || !this.progressData) return;
        
        const stats = this.progressData.database_stats || {};
        
        container.innerHTML = `
            <div class="progress-summary">
                <div class="summary-card">
                    <div class="summary-icon">📚</div>
                    <div class="summary-content">
                        <div class="summary-value">${stats.total_learned || 0}</div>
                        <div class="summary-label">已学词汇</div>
                    </div>
                </div>
                <div class="summary-card">
                    <div class="summary-icon">🎯</div>
                    <div class="summary-content">
                        <div class="summary-value">${Math.round((stats.mastery_rate || 0) * 100)}%</div>
                        <div class="summary-label">掌握率</div>
                    </div>
                </div>
                <div class="summary-card">
                    <div class="summary-icon">🔥</div>
                    <div class="summary-content">
                        <div class="summary-value">${stats.streak_days || 0}</div>
                        <div class="summary-label">连续天数</div>
                    </div>
                </div>
                <div class="summary-card">
                    <div class="summary-icon">⏱️</div>
                    <div class="summary-content">
                        <div class="summary-value">${BilingualTutor.formatDuration(stats.total_study_time || 0)}</div>
                        <div class="summary-label">学习时长</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderLanguageProgress() {
        this.renderLanguageCard('english', '英语', '#3b82f6');
        this.renderLanguageCard('japanese', '日语', '#ef4444');
    }
    
    renderLanguageCard(language, displayName, color) {
        const container = document.getElementById(`${language}-progress`);
        if (!container) return;
        
        const langData = this.progressData.vocabulary?.[language] || {};
        const currentLevel = language === 'english' ? 'CET-4' : 'N5';
        const targetLevel = language === 'english' ? 'CET-6' : 'N1';
        const progress = langData.level_progress || 0;
        
        container.innerHTML = `
            <div class="language-header">
                <h3>${displayName} 学习进度</h3>
                <div class="level-indicator">
                    <span class="current-level">${currentLevel}</span>
                    <span class="level-arrow">→</span>
                    <span class="target-level">${targetLevel}</span>
                </div>
            </div>
            
            <div class="progress-circle-container">
                ${this.createProgressCircle(progress, color)}
            </div>
            
            <div class="language-stats">
                <div class="stat-item">
                    <span class="stat-label">已学词汇</span>
                    <span class="stat-value">${langData.learned_words || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">掌握词汇</span>
                    <span class="stat-value">${langData.mastered_words || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">复习词汇</span>
                    <span class="stat-value">${langData.review_words || 0}</span>
                </div>
            </div>
        `;
    }
    
    createProgressCircle(progress, color) {
        const radius = 45;
        const circumference = 2 * Math.PI * radius;
        const strokeDasharray = circumference;
        const strokeDashoffset = circumference - (progress / 100) * circumference;
        
        return `
            <div class="progress-circle">
                <svg width="120" height="120">
                    <defs>
                        <linearGradient id="progressGradient-${color.replace('#', '')}" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" style="stop-color:${color};stop-opacity:1" />
                            <stop offset="100%" style="stop-color:${color}88;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <circle class="progress-circle-bg" cx="60" cy="60" r="${radius}"></circle>
                    <circle class="progress-circle-fill" 
                            cx="60" cy="60" r="${radius}"
                            stroke="url(#progressGradient-${color.replace('#', '')})"
                            stroke-dasharray="${strokeDasharray}"
                            stroke-dashoffset="${strokeDashoffset}">
                    </circle>
                </svg>
                <div class="progress-circle-text">${Math.round(progress)}%</div>
            </div>
        `;
    }
    
    renderVocabularyStats() {
        const container = document.getElementById('vocabulary-stats');
        if (!container) return;
        
        const vocabData = this.progressData.vocabulary || {};
        
        container.innerHTML = `
            <div class="vocab-overview">
                <h3>词汇统计</h3>
                <div class="vocab-charts">
                    ${this.createVocabularyChart('english', vocabData.english)}
                    ${this.createVocabularyChart('japanese', vocabData.japanese)}
                </div>
            </div>
        `;
    }
    
    createVocabularyChart(language, data) {
        if (!data) return '';
        
        const total = data.total_words || 0;
        const learned = data.learned_words || 0;
        const mastered = data.mastered_words || 0;
        const learning = learned - mastered;
        
        const masteredPercent = total > 0 ? (mastered / total) * 100 : 0;
        const learningPercent = total > 0 ? (learning / total) * 100 : 0;
        
        return `
            <div class="vocab-chart">
                <h4>${language === 'english' ? '英语' : '日语'} 词汇</h4>
                <div class="vocab-bar">
                    <div class="vocab-fill mastered" style="width: ${masteredPercent}%"></div>
                    <div class="vocab-fill learning" style="width: ${learningPercent}%"></div>
                </div>
                <div class="vocab-legend">
                    <div class="legend-item">
                        <span class="legend-color mastered"></span>
                        <span>已掌握: ${mastered}</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color learning"></span>
                        <span>学习中: ${learning}</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color unlearned"></span>
                        <span>未学习: ${total - learned}</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderLearningStreak() {
        const container = document.getElementById('learning-streak');
        if (!container) return;
        
        const streakData = this.generateStreakData(); // Mock data for now
        
        container.innerHTML = `
            <div class="streak-header">
                <h3>学习连续性</h3>
                <div class="streak-summary">
                    <span class="streak-count">${streakData.currentStreak}</span>
                    <span class="streak-label">天连续学习</span>
                </div>
            </div>
            <div class="streak-calendar">
                ${streakData.days.map(day => `
                    <div class="streak-day ${day.status} ${day.isToday ? 'today' : ''}" 
                         title="${day.date}">
                        ${day.day}
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    generateStreakData() {
        // Generate mock streak data for the last 28 days
        const days = [];
        const today = new Date();
        
        for (let i = 27; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            
            days.push({
                date: date.toLocaleDateString(),
                day: date.getDate(),
                status: Math.random() > 0.3 ? 'completed' : '',
                isToday: i === 0
            });
        }
        
        // Calculate current streak
        let currentStreak = 0;
        for (let i = days.length - 1; i >= 0; i--) {
            if (days[i].status === 'completed') {
                currentStreak++;
            } else {
                break;
            }
        }
        
        return { days, currentStreak };
    }
    
    renderWeaknessAnalysis() {
        const container = document.getElementById('weakness-analysis');
        if (!container) return;
        
        const weaknesses = this.progressData.weaknesses || {};
        
        if (Object.keys(weaknesses).length === 0) {
            container.innerHTML = `
                <div class="no-weakness">
                    <span class="icon">🎉</span>
                    <h3>表现优秀！</h3>
                    <p>目前没有发现明显的薄弱环节，继续保持！</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="weakness-header">
                <h3>薄弱环节分析</h3>
            </div>
            <div class="weakness-grid">
                ${Object.entries(weaknesses).map(([language, areas]) => `
                    <div class="weakness-card">
                        <h4>${language === 'english' ? '英语' : '日语'} 薄弱环节</h4>
                        <ul>
                            ${areas.map(area => `
                                <li>
                                    <span class="weakness-skill">${BilingualTutor.getSkillName(area.skill)}</span>
                                    <span class="weakness-severity">${this.getSeverityText(area.severity)}</span>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    getSeverityText(severity) {
        if (severity > 0.7) return '需要重点关注';
        if (severity > 0.4) return '需要加强';
        return '轻微薄弱';
    }
    
    renderSystemHealth() {
        const container = document.getElementById('system-health');
        if (!container) return;
        
        const health = this.progressData.integration_health || {};
        
        container.innerHTML = `
            <div class="health-header">
                <h3>系统状态</h3>
            </div>
            <div class="health-indicators">
                ${Object.entries(health).map(([component, status]) => `
                    <div class="health-indicator ${status}">
                        <span class="health-icon">${this.getHealthIcon(status)}</span>
                        <span class="health-label">${this.getComponentName(component)}</span>
                        <span class="health-status">${this.getStatusText(status)}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    getHealthIcon(status) {
        switch (status) {
            case 'healthy': return '✅';
            case 'degraded': return '⚠️';
            case 'unhealthy': return '❌';
            default: return '❓';
        }
    }
    
    getComponentName(component) {
        const names = {
            'core_engine': '核心引擎',
            'database': '数据库',
            'audio_system': '音频系统',
            'content_crawler': '内容爬虫'
        };
        return names[component] || component;
    }
    
    getStatusText(status) {
        const texts = {
            'healthy': '正常',
            'degraded': '降级',
            'unhealthy': '异常'
        };
        return texts[status] || '未知';
    }
    
    renderErrorState() {
        const container = document.getElementById('progress-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="error-state">
                <div class="error-icon">⚠️</div>
                <h3>加载进度数据失败</h3>
                <p>请检查网络连接或稍后重试</p>
                <button class="btn btn-primary" onclick="window.progressViz.loadProgressData()">
                    重新加载
                </button>
            </div>
        `;
    }
    
    async refreshProgress() {
        const refreshBtn = document.getElementById('refresh-progress');
        if (refreshBtn) {
            BilingualTutor.setLoadingState(refreshBtn, true, '刷新中...');
        }
        
        await this.loadProgressData();
        
        if (refreshBtn) {
            BilingualTutor.setLoadingState(refreshBtn, false);
        }
    }
    
    updateTimeRange(range) {
        // Update visualizations based on time range
        BilingualTutor.showToast(`切换到${range}视图`, 'info');
        // In a real implementation, this would reload data for the selected time range
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.body.classList.contains('progress-page')) {
        window.progressViz = new ProgressVisualization();
    }
});

// Export for global use
window.ProgressVisualization = ProgressVisualization;