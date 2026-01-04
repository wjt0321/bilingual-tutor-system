/**
 * 双语导师系统 - 前端逻辑
 * Bilingual Tutor System - Main JavaScript
 * 
 * Enhanced with:
 * - Better error handling and user feedback
 * - Session management and auto-logout
 * - Performance optimizations
 * - Accessibility improvements
 */

// ==================== Configuration ====================

const CONFIG = {
    API_TIMEOUT: 10000, // 10 seconds
    SESSION_CHECK_INTERVAL: 300000, // 5 minutes
    TOAST_DURATION: 3000,
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000
};

// ==================== State Management ====================

const AppState = {
    isAuthenticated: false,
    currentUser: null,
    sessionTimer: null,
    retryCount: new Map(),

    setAuthenticated(user) {
        this.isAuthenticated = true;
        this.currentUser = user;
        this.startSessionMonitoring();
    },

    setUnauthenticated() {
        this.isAuthenticated = false;
        this.currentUser = null;
        this.stopSessionMonitoring();
    },

    startSessionMonitoring() {
        if (this.sessionTimer) {
            clearInterval(this.sessionTimer);
        }
        this.sessionTimer = setInterval(checkSessionStatus, CONFIG.SESSION_CHECK_INTERVAL);
    },

    stopSessionMonitoring() {
        if (this.sessionTimer) {
            clearInterval(this.sessionTimer);
            this.sessionTimer = null;
        }
    }
};

// ==================== Enhanced Utility Functions ====================

/**
 * Make API request with enhanced error handling and retry logic
 */
async function apiRequest(url, options = {}) {
    const requestId = `${url}-${Date.now()}`;
    const retryCount = AppState.retryCount.get(requestId) || 0;

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.API_TIMEOUT);

        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                ...options.headers
            },
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        const data = await response.json();

        if (!response.ok) {
            // Handle authentication errors
            if (response.status === 401) {
                // If we are not on login/register page, it's a session expiry
                if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                    handleAuthenticationError();
                    return { success: false, message: '登录已过期，请重新登录' };
                }
            }
            return { success: false, message: data.message || `请求失败 (${response.status})` };
        }

        // Clear retry count on success
        AppState.retryCount.delete(requestId);

        return data;

    } catch (error) {
        console.error('API Error:', error);

        // Handle retry logic for network errors
        if (retryCount < CONFIG.MAX_RETRIES &&
            (error.name === 'AbortError' || error.name === 'TypeError')) {

            AppState.retryCount.set(requestId, retryCount + 1);

            // Wait before retry
            await new Promise(resolve => setTimeout(resolve, CONFIG.RETRY_DELAY * (retryCount + 1)));

            return apiRequest(url, options);
        }

        // Clear retry count after max retries
        AppState.retryCount.delete(requestId);

        // Return user-friendly error message
        let message = '网络请求失败，请检查连接';

        if (error.name === 'AbortError') {
            message = '请求超时，请稍后重试';
        } else if (error.message.includes('403')) {
            message = '访问被拒绝';
        } else if (error.message.includes('404')) {
            message = '请求的资源不存在';
        } else if (error.message.includes('500')) {
            message = '服务器内部错误，请稍后重试';
        }

        return { success: false, message };
    }
}

/**
 * Enhanced toast notification with better styling and accessibility
 */
function showToast(message, type = 'info', duration = CONFIG.TOAST_DURATION) {
    // Remove existing toasts of the same type
    const existingToasts = document.querySelectorAll(`.toast-${type}`);
    existingToasts.forEach(toast => toast.remove());

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');

    // Add icon based on type
    const icons = {
        info: 'ℹ️',
        success: '✅',
        warning: '⚠️',
        error: '❌'
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()" aria-label="关闭通知">×</button>
    `;

    // Add to body
    document.body.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // Auto-remove after delay
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);

    return toast;
}

/**
 * Enhanced loading state management
 */
function setLoadingState(element, isLoading, loadingText = '加载中...') {
    if (!element) return;

    if (isLoading) {
        element.disabled = true;
        element.dataset.originalText = element.textContent;
        element.innerHTML = `<span class="loading-spinner"></span> ${loadingText}`;
        element.classList.add('loading');
    } else {
        element.disabled = false;
        element.textContent = element.dataset.originalText || element.textContent;
        element.classList.remove('loading');
        delete element.dataset.originalText;
    }
}

/**
 * Debounce function for performance optimization
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Format time duration with better localization
 */
function formatDuration(minutes) {
    if (minutes < 60) {
        return `${minutes} 分钟`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours} 小时 ${mins} 分钟` : `${hours} 小时`;
}

/**
 * Format percentage with proper rounding
 */
function formatPercent(value, decimals = 0) {
    return (value * 100).toFixed(decimals) + '%';
}

/**
 * Get activity type display name with fallback
 */
function getActivityTypeName(type) {
    const typeMap = {
        'vocabulary': '词汇学习',
        'grammar': '语法学习',
        'reading': '阅读理解',
        'listening': '听力训练',
        'speaking': '口语练习',
        'writing': '写作练习',
        'review': '复习巩固'
    };
    return typeMap[type] || type;
}

/**
 * Get skill display name with fallback
 */
function getSkillName(skill) {
    const skillMap = {
        'vocabulary': '词汇',
        'grammar': '语法',
        'reading': '阅读',
        'listening': '听力',
        'speaking': '口语',
        'writing': '写作',
        'pronunciation': '发音',
        'comprehension': '理解'
    };
    return skillMap[skill] || skill;
}

// ==================== Enhanced Authentication ====================

/**
 * Check session status
 */
async function checkSessionStatus() {
    try {
        const data = await apiRequest('/api/auth/status');

        if (data.authenticated) {
            AppState.setAuthenticated(data.user_id);
        } else {
            AppState.setUnauthenticated();
            if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                showToast('登录已过期，请重新登录', 'warning');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            }
        }
    } catch (error) {
        console.error('Session check failed:', error);
    }
}

/**
 * Handle authentication errors
 */
function handleAuthenticationError() {
    AppState.setUnauthenticated();
    showToast('登录已过期，请重新登录', 'error');
    setTimeout(() => {
        window.location.href = '/login';
    }, 2000);
}

/**
 * Enhanced logout with confirmation
 */
async function logout(skipConfirmation = false) {
    if (!skipConfirmation && !confirm('确定要退出登录吗？')) {
        return;
    }

    try {
        await apiRequest('/api/auth/logout', { method: 'POST' });
        AppState.setUnauthenticated();
        showToast('已成功退出登录', 'success');
        setTimeout(() => {
            window.location.href = '/login';
        }, 1000);
    } catch (error) {
        console.error('Logout failed:', error);
        // Force logout even if API call fails
        AppState.setUnauthenticated();
        window.location.href = '/login';
    }
}

// ==================== Enhanced Navigation ====================

/**
 * Navigate to page with loading state
 */
function navigateTo(page, showLoading = true) {
    if (showLoading) {
        document.body.classList.add('page-loading');
    }
    window.location.href = page;
}

// ==================== Enhanced Data Loading ====================

/**
 * Load user profile with caching
 */
async function loadUserProfile(useCache = true) {
    const cacheKey = 'user_profile';
    const cacheTime = 5 * 60 * 1000; // 5 minutes

    if (useCache) {
        const cached = sessionStorage.getItem(cacheKey);
        if (cached) {
            const { data, timestamp } = JSON.parse(cached);
            if (Date.now() - timestamp < cacheTime) {
                return data;
            }
        }
    }

    const response = await apiRequest('/api/user/profile');
    if (response.success) {
        // Cache the result
        sessionStorage.setItem(cacheKey, JSON.stringify({
            data: response.profile,
            timestamp: Date.now()
        }));
        return response.profile;
    }
    return null;
}

/**
 * Load learning plan with error handling
 */
async function loadLearningPlan() {
    try {
        const data = await apiRequest('/api/learning/plan');
        if (data.success) {
            return data.plan;
        } else {
            showToast(data.message || '获取学习计划失败', 'error');
        }
    } catch (error) {
        showToast('获取学习计划失败，请刷新页面重试', 'error');
    }
    return null;
}

/**
 * Load progress data with error handling
 */
async function loadProgress() {
    try {
        const data = await apiRequest('/api/progress/status');
        if (data.success) {
            return data.progress;
        } else {
            showToast(data.message || '获取进度数据失败', 'error');
        }
    } catch (error) {
        showToast('获取进度数据失败，请刷新页面重试', 'error');
    }
    return null;
}

// ==================== Enhanced UI Updates ====================

/**
 * Update progress bar with animation
 */
function updateProgressBar(elementId, percent, animate = true) {
    const element = document.getElementById(elementId);
    if (element) {
        const targetWidth = Math.min(Math.max(percent, 0), 100);

        if (animate) {
            element.style.transition = 'width 0.5s ease-in-out';
        }

        element.style.width = targetWidth + '%';
        element.setAttribute('aria-valuenow', targetWidth);
    }
}

/**
 * Update text content safely with fallback
 */
function setText(elementId, text, fallback = '--') {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text || fallback;
    }
}

/**
 * Update HTML content safely
 */
function setHTML(elementId, html, fallback = '') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = html || fallback;
    }
}

// ==================== Enhanced Event Listeners ====================

// Enhanced keyboard shortcuts
document.addEventListener('keydown', function (e) {
    // Skip if user is typing in an input field
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
    }

    // Ctrl+H - Go to home
    if (e.ctrlKey && e.key === 'h') {
        e.preventDefault();
        navigateTo('/');
    }

    // Ctrl+L - Go to learn
    if (e.ctrlKey && e.key === 'l') {
        e.preventDefault();
        navigateTo('/learn');
    }

    // Ctrl+P - Go to progress
    if (e.ctrlKey && e.key === 'p') {
        e.preventDefault();
        navigateTo('/progress');
    }

    // Ctrl+S - Go to settings
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        navigateTo('/settings');
    }

    // Escape - Close modals/toasts
    if (e.key === 'Escape') {
        const toasts = document.querySelectorAll('.toast');
        toasts.forEach(toast => toast.remove());
    }
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible' && AppState.isAuthenticated) {
        // Check session when page becomes visible
        checkSessionStatus();
    }
});

// Handle online/offline status
window.addEventListener('online', function () {
    showToast('网络连接已恢复', 'success');
});

window.addEventListener('offline', function () {
    showToast('网络连接已断开', 'warning');
});

// ==================== Enhanced Toast Styles ====================

// Inject enhanced toast styles
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    .toast {
        position: fixed;
        bottom: 20px;
        right: 20px;
        min-width: 300px;
        max-width: 500px;
        padding: 16px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        opacity: 0;
        transform: translateY(20px) translateX(20px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 9999;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .toast.show {
        opacity: 1;
        transform: translateY(0) translateX(0);
    }
    
    .toast-icon {
        font-size: 18px;
        flex-shrink: 0;
    }
    
    .toast-message {
        flex: 1;
        line-height: 1.4;
    }
    
    .toast-close {
        background: none;
        border: none;
        color: white;
        font-size: 20px;
        cursor: pointer;
        padding: 0;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: background-color 0.2s;
        flex-shrink: 0;
    }
    
    .toast-close:hover {
        background-color: rgba(255, 255, 255, 0.2);
    }
    
    .toast-info {
        background: linear-gradient(135deg, #3b82f6, #6366f1);
    }
    
    .toast-success {
        background: linear-gradient(135deg, #10b981, #059669);
    }
    
    .toast-warning {
        background: linear-gradient(135deg, #f59e0b, #d97706);
    }
    
    .toast-error {
        background: linear-gradient(135deg, #ef4444, #dc2626);
    }
    
    .loading-spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top-color: white;
        animation: spin 1s ease-in-out infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    .loading {
        opacity: 0.7;
        cursor: not-allowed;
    }
    
    .page-loading {
        cursor: wait;
    }
    
    .page-loading * {
        pointer-events: none;
    }
`;
document.head.appendChild(toastStyles);

// ==================== Initialize ====================

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    // Check initial authentication status
    checkSessionStatus();

    console.log('双语导师系统前端已加载 | Bilingual Tutor System Frontend Loaded');
    console.log('Enhanced features: Session management, Error handling, Performance optimization');
});

// Export functions for global use
window.BilingualTutor = {
    apiRequest,
    showToast,
    setLoadingState,
    formatDuration,
    formatPercent,
    getActivityTypeName,
    getSkillName,
    logout,
    navigateTo,
    loadUserProfile,
    loadLearningPlan,
    loadProgress,
    updateProgressBar,
    setText,
    setHTML,
    debounce
};
