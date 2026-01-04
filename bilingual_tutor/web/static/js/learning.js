/**
 * Enhanced Learning Activity JavaScript
 * 增强的学习活动交互脚本
 */

class LearningActivityManager {
    constructor() {
        this.currentActivity = null;
        this.activityResults = new Map();
        this.audioManager = new AudioManager();
        this.progressTracker = new ProgressTracker();
        this.init();
    }

    init() {
        this.bindEvents();
        // Removed redundant loadActivityData to avoid conflict with learn.html
        // this.loadActivityData();
    }

    bindEvents() {
        // Activity completion events
        document.addEventListener('click', (e) => {
            if (e.target.matches('.complete-activity-btn')) {
                this.completeActivity(e.target.dataset.activityId);
            }

            if (e.target.matches('.audio-control')) {
                this.audioManager.toggleAudio(e.target.dataset.word, e.target.dataset.language);
            }

            if (e.target.matches('.mastery-btn')) {
                this.updateMasteryLevel(e.target.dataset.itemId, e.target.dataset.level);
            }
        });

        // Progress visualization updates
        document.addEventListener('progress-update', (e) => {
            this.progressTracker.updateProgress(e.detail);
        });
    }

    async loadActivityData() {
        try {
            const response = await BilingualTutor.apiRequest('/api/learning/plan');
            if (response.success) {
                // The HTML already has its own rendering logic, 
                // but we keep this as a secondary data sync if needed.
                // this.renderActivities(response.plan.activities);
                this.updateTimeAllocation(response.plan);
            }
        } catch (error) {
            console.error('LearningActivityManager load error:', error);
            // BilingualTutor.showToast('加载学习活动失败', 'error');
        }
    }

    updateTimeAllocation(plan) {
        // Placeholder to prevent TypeError, can be used for summary stats
        console.log('Time allocation updated:', plan.total_time);
    }

    renderActivities(activities) {
        const container = document.getElementById('activities-container');
        if (!container) return;

        container.innerHTML = activities.map((activity, index) => `
            <div class="activity-card interactive-card" data-activity-id="${activity.id}">
                <div class="activity-header">
                    <div class="activity-number">${index + 1}</div>
                    <div class="activity-info">
                        <div class="activity-type ${activity.language}">${BilingualTutor.getActivityTypeName(activity.type)}</div>
                        <div class="activity-title">${activity.title}</div>
                        <div class="activity-duration">⏱️ ${BilingualTutor.formatDuration(activity.duration)}</div>
                    </div>
                    <div class="activity-status pending">待完成</div>
                </div>
                <div class="activity-content">
                    ${this.renderActivityContent(activity)}
                </div>
                <div class="activity-actions">
                    <button class="btn btn-primary complete-activity-btn" data-activity-id="${activity.id}">
                        完成学习
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderActivityContent(activity) {
        // Enhanced content rendering with audio support
        let content = activity.content;

        // Add audio controls for vocabulary activities
        if (activity.type === 'vocabulary') {
            content = this.addAudioControls(content, activity.language);
        }

        // Add progress tracking elements
        content += this.renderProgressElements(activity);

        return content;
    }

    addAudioControls(content, language) {
        // Simple implementation - in production, this would parse vocabulary items
        return content.replace(/\*\*(\d+\.\s+[^*]+)\*\*/g, (match, word) => {
            const cleanWord = word.replace(/^\d+\.\s+/, '').trim();
            return `${match} <button class="audio-control" data-word="${cleanWord}" data-language="${language}" title="播放发音">🔊</button>`;
        });
    }

    renderProgressElements(activity) {
        return `
            <div class="progress-elements">
                <div class="mastery-controls">
                    <span>掌握程度：</span>
                    ${[1, 2, 3, 4, 5].map(level => `
                        <button class="mastery-btn mastery-level-${level}" 
                                data-item-id="${activity.id}" 
                                data-level="${level}"
                                title="掌握级别 ${level}">
                            ${level}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
    }

    async completeActivity(activityId) {
        const button = document.querySelector(`[data-activity-id="${activityId}"] .complete-activity-btn`);
        BilingualTutor.setLoadingState(button, true, '完成中...');

        try {
            const responses = this.collectActivityResponses(activityId);
            const response = await BilingualTutor.apiRequest(`/api/learning/execute/${activityId}`, {
                method: 'POST',
                body: JSON.stringify({ responses })
            });

            if (response.success) {
                this.handleActivityCompletion(activityId, response.result);
                BilingualTutor.showToast('学习活动完成！', 'success');
            } else {
                BilingualTutor.showToast(response.message || '完成活动失败', 'error');
            }
        } catch (error) {
            BilingualTutor.showToast('完成活动失败，请重试', 'error');
        } finally {
            BilingualTutor.setLoadingState(button, false);
        }
    }

    collectActivityResponses(activityId) {
        const activityCard = document.querySelector(`[data-activity-id="${activityId}"]`);
        const responses = {};

        // Collect mastery level selections
        const masteryButtons = activityCard.querySelectorAll('.mastery-btn.selected');
        masteryButtons.forEach(btn => {
            responses[`mastery_${btn.dataset.itemId}`] = btn.dataset.level;
        });

        // Collect other form inputs
        const inputs = activityCard.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            responses[input.name] = input.value;
        });

        return responses;
    }

    handleActivityCompletion(activityId, result) {
        const activityCard = document.querySelector(`[data-activity-id="${activityId}"]`);
        const statusElement = activityCard.querySelector('.activity-status');

        // Update status
        statusElement.textContent = '已完成';
        statusElement.className = 'activity-status completed';

        // Store result
        this.activityResults.set(activityId, result);

        // Show result feedback
        this.showActivityResult(activityCard, result);

        // Update progress
        this.progressTracker.recordActivity(activityId, result);

        // Trigger progress update event
        document.dispatchEvent(new CustomEvent('progress-update', {
            detail: { activityId, result }
        }));
    }

    showActivityResult(activityCard, result) {
        const resultHtml = `
            <div class="activity-result">
                <div class="result-score">
                    <span class="score-label">得分：</span>
                    <span class="score-value">${Math.round(result.score * 100)}%</span>
                </div>
                <div class="result-feedback">
                    ${result.feedback}
                </div>
                ${result.next_review_date ? `
                    <div class="next-review">
                        <span>下次复习：${new Date(result.next_review_date).toLocaleDateString()}</span>
                    </div>
                ` : ''}
            </div>
        `;

        const actionsElement = activityCard.querySelector('.activity-actions');
        actionsElement.innerHTML = resultHtml;
    }

    updateMasteryLevel(itemId, level) {
        // Update visual state
        const masteryButtons = document.querySelectorAll(`[data-item-id="${itemId}"]`);
        masteryButtons.forEach(btn => {
            btn.classList.remove('selected');
            if (btn.dataset.level <= level) {
                btn.classList.add('selected');
            }
        });
    }
}

class AudioManager {
    constructor() {
        this.audioCache = new Map();
        this.currentAudio = null;
    }

    async toggleAudio(word, language) {
        try {
            const audioData = await this.getAudioData(word, language);
            if (audioData && audioData.audio_available) {
                await this.playAudio(audioData.audio_path);
            } else {
                BilingualTutor.showToast('该词汇暂无发音', 'warning');
            }
        } catch (error) {
            BilingualTutor.showToast('播放发音失败', 'error');
        }
    }

    async getAudioData(word, language) {
        const cacheKey = `${word}_${language}`;

        if (this.audioCache.has(cacheKey)) {
            return this.audioCache.get(cacheKey);
        }

        // In a real implementation, this would call the audio API
        // For now, return mock data
        const audioData = {
            word,
            language,
            audio_available: Math.random() > 0.3, // 70% chance of having audio
            audio_path: `/audio/${language}/${word}.mp3`
        };

        this.audioCache.set(cacheKey, audioData);
        return audioData;
    }

    async playAudio(audioPath) {
        if (this.currentAudio) {
            this.currentAudio.pause();
        }

        this.currentAudio = new Audio(audioPath);

        return new Promise((resolve, reject) => {
            this.currentAudio.onended = resolve;
            this.currentAudio.onerror = reject;
            this.currentAudio.play().catch(reject);
        });
    }
}

class ProgressTracker {
    constructor() {
        this.sessionProgress = {
            activitiesCompleted: 0,
            totalActivities: 0,
            totalScore: 0,
            timeSpent: 0
        };
    }

    recordActivity(activityId, result) {
        this.sessionProgress.activitiesCompleted++;
        this.sessionProgress.totalScore += result.score;
        this.sessionProgress.timeSpent += result.time_spent;

        this.updateProgressDisplay();
    }

    updateProgressDisplay() {
        const progressElements = {
            completed: document.getElementById('activities-completed'),
            score: document.getElementById('average-score'),
            time: document.getElementById('time-spent')
        };

        if (progressElements.completed) {
            progressElements.completed.textContent =
                `${this.sessionProgress.activitiesCompleted}/${this.sessionProgress.totalActivities}`;
        }

        if (progressElements.score && this.sessionProgress.activitiesCompleted > 0) {
            const avgScore = this.sessionProgress.totalScore / this.sessionProgress.activitiesCompleted;
            progressElements.score.textContent = `${Math.round(avgScore * 100)}%`;
        }

        if (progressElements.time) {
            progressElements.time.textContent = BilingualTutor.formatDuration(this.sessionProgress.timeSpent);
        }

        // Update progress bars
        if (this.sessionProgress.totalActivities > 0) {
            const completionPercent = (this.sessionProgress.activitiesCompleted / this.sessionProgress.totalActivities) * 100;
            BilingualTutor.updateProgressBar('session-progress', completionPercent);
        }
    }

    updateProgress(data) {
        // Handle external progress updates
        if (data.totalActivities) {
            this.sessionProgress.totalActivities = data.totalActivities;
        }

        this.updateProgressDisplay();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.body.classList.contains('learn-page')) {
        window.learningManager = new LearningActivityManager();
    }
});

// Export for global use
window.LearningActivityManager = LearningActivityManager;
window.AudioManager = AudioManager;
window.ProgressTracker = ProgressTracker;