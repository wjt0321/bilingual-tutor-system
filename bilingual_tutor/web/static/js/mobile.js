class MobileOptimizer {
    constructor() {
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchEndX = 0;
        this.touchEndY = 0;
        this.minSwipeDistance = 50;
        this.maxSwipeTime = 300;
        this.touchStartTime = 0;
        this.offlineCache = new Map();
        this.isOnline = navigator.onLine;
        this.serviceWorkerRegistered = false;
        
        this.init();
    }

    init() {
        this.setupTouchEvents();
        this.setupOfflineSupport();
        this.setupViewportOptimization();
        this.setupScrollOptimization();
        this.setupClickOptimization();
        this.setupPerformanceMonitoring();
        this.setupGestureShortcuts();
        this.setupAdaptiveUI();
    }

    setupTouchEvents() {
        document.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
        document.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
        document.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: true });
        document.addEventListener('touchcancel', (e) => this.handleTouchCancel(e), { passive: true });
    }

    handleTouchStart(e) {
        if (e.touches.length === 1) {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
            this.touchStartTime = Date.now();
        }
        
        const target = e.target.closest('[data-touch-action]');
        if (target) {
            target.classList.add('touch-active');
            this.hapticFeedback('light');
        }
    }

    handleTouchMove(e) {
        const target = e.target.closest('[data-prevent-scroll]');
        if (target && e.touches.length === 1) {
            const deltaX = e.touches[0].clientX - this.touchStartX;
            const deltaY = e.touches[0].clientY - this.touchStartY;
            
            if (Math.abs(deltaX) > Math.abs(deltaY)) {
                e.preventDefault();
            }
        }

        if (e.touches.length === 1) {
            const deltaX = e.touches[0].clientX - this.touchStartX;
            const deltaY = e.touches[0].clientY - this.touchStartY;
            
            if (Math.abs(deltaX) > 10) {
                this.updateSwipeIndicator(deltaX);
            }
        }
    }

    handleTouchEnd(e) {
        this.touchEndX = e.changedTouches[0].clientX;
        this.touchEndY = e.changedTouches[0].clientY;
        const touchDuration = Date.now() - this.touchStartTime;

        document.querySelectorAll('.touch-active').forEach(el => {
            el.classList.remove('touch-active');
        });

        this.handleSwipe(touchDuration);
        this.handleTap(touchDuration);
        this.handleLongPress(touchDuration);
        
        this.clearSwipeIndicator();
    }

    handleTouchCancel(e) {
        document.querySelectorAll('.touch-active').forEach(el => {
            el.classList.remove('touch-active');
        });
    }

    handleSwipe(duration) {
        if (duration > this.maxSwipeTime) return;

        const deltaX = this.touchEndX - this.touchStartX;
        const deltaY = this.touchEndY - this.touchStartY;

        if (Math.abs(deltaX) < this.minSwipeDistance && Math.abs(deltaY) < this.minSwipeDistance) {
            return;
        }

        const direction = Math.abs(deltaX) > Math.abs(deltaY) 
            ? (deltaX > 0 ? 'right' : 'left')
            : (deltaY > 0 ? 'down' : 'up');

        this.triggerSwipeAction(direction);
    }

    handleTap(duration) {
        if (duration > 300) return;
        
        const deltaX = Math.abs(this.touchEndX - this.touchStartX);
        const deltaY = Math.abs(this.touchEndY - this.touchStartY);
        
        if (deltaX < 10 && deltaY < 10) {
            this.hapticFeedback('light');
        }
    }

    handleLongPress(duration) {
        if (duration > 500 && duration < 1000) {
            const target = document.elementFromPoint(this.touchStartX, this.touchStartY);
            if (target && target.closest('[data-long-press]')) {
                this.hapticFeedback('heavy');
                this.triggerLongPressAction(target);
            }
        }
    }

    triggerSwipeAction(direction) {
        const event = new CustomEvent('mobile-swipe', {
            detail: { direction },
            bubbles: true
        });
        document.dispatchEvent(event);

        switch (direction) {
            case 'left':
                this.navigateNext();
                break;
            case 'right':
                this.navigatePrevious();
                break;
            case 'up':
                this.showQuickActions();
                break;
            case 'down':
                this.hideQuickActions();
                break;
        }
    }

    triggerLongPressAction(target) {
        const action = target.closest('[data-long-press]').dataset.longPress;
        const event = new CustomEvent('mobile-long-press', {
            detail: { action, target },
            bubbles: true
        });
        document.dispatchEvent(event);
    }

    updateSwipeIndicator(deltaX) {
        let indicator = document.getElementById('swipe-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'swipe-indicator';
            indicator.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 100px;
                height: 4px;
                background: linear-gradient(90deg, rgba(59, 130, 246, 0.5), rgba(99, 102, 241, 0.5));
                border-radius: 2px;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.2s;
                z-index: 9999;
            `;
            document.body.appendChild(indicator);
        }
        
        const opacity = Math.min(Math.abs(deltaX) / 100, 0.8);
        indicator.style.opacity = opacity;
        indicator.style.transform = `translate(-50%, -50%) translateX(${deltaX / 5}px)`;
    }

    clearSwipeIndicator() {
        const indicator = document.getElementById('swipe-indicator');
        if (indicator) {
            indicator.style.opacity = '0';
            setTimeout(() => indicator.remove(), 200);
        }
    }

    navigateNext() {
        const nextBtn = document.querySelector('[data-navigation="next"]');
        if (nextBtn) {
            nextBtn.click();
            this.showToast('下一页');
        }
    }

    navigatePrevious() {
        const prevBtn = document.querySelector('[data-navigation="previous"]');
        if (prevBtn) {
            prevBtn.click();
            this.showToast('上一页');
        }
    }

    showQuickActions() {
        const quickActions = document.getElementById('quick-actions-panel');
        if (quickActions) {
            quickActions.classList.add('visible');
        }
    }

    hideQuickActions() {
        const quickActions = document.getElementById('quick-actions-panel');
        if (quickActions) {
            quickActions.classList.remove('visible');
        }
    }

    setupOfflineSupport() {
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        if ('serviceWorker' in navigator) {
            this.registerServiceWorker();
        }
        
        this.cacheCriticalResources();
        this.setupIndexedDB();
    }

    handleOnline() {
        this.isOnline = true;
        this.hideOfflineBanner();
        this.syncOfflineData();
        this.showToast('已连接网络', 'success');
        
        document.body.classList.remove('offline-mode');
    }

    handleOffline() {
        this.isOnline = false;
        this.showOfflineBanner();
        this.showToast('离线模式', 'warning');
        
        document.body.classList.add('offline-mode');
    }

    showOfflineBanner() {
        let banner = document.getElementById('offline-banner');
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'offline-banner';
            banner.className = 'offline-banner';
            banner.innerHTML = `
                <div class="offline-content">
                    <span class="offline-icon">⚠️</span>
                    <span class="offline-message">离线模式 - 部分功能受限</span>
                </div>
            `;
            banner.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: linear-gradient(135deg, #f59e0b, #d97706);
                color: white;
                padding: 12px 20px;
                text-align: center;
                z-index: 10000;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                transform: translateY(-100%);
                transition: transform 0.3s ease;
            `;
            document.body.appendChild(banner);
        }
        
        setTimeout(() => banner.style.transform = 'translateY(0)', 100);
    }

    hideOfflineBanner() {
        const banner = document.getElementById('offline-banner');
        if (banner) {
            banner.style.transform = 'translateY(-100%)';
            setTimeout(() => banner.remove(), 300);
        }
    }

    async registerServiceWorker() {
        try {
            const registration = await navigator.serviceWorker.register('/static/js/sw.js');
            this.serviceWorkerRegistered = true;
            console.log('Service Worker registered:', registration);
        } catch (error) {
            console.log('Service Worker registration failed:', error);
        }
    }

    cacheCriticalResources() {
        const criticalResources = [
            '/static/css/style.css',
            '/static/js/main.js',
            '/static/js/learning.js',
            '/static/js/progress.js',
            '/static/js/mobile.js'
        ];
        
        criticalResources.forEach(url => {
            this.offlineCache.set(url, false);
        });
    }

    async setupIndexedDB() {
        try {
            const request = indexedDB.open('BilingualTutorDB', 1);
            
            request.onerror = () => console.log('IndexedDB error');
            
            request.onsuccess = (event) => {
                this.db = event.target.result;
                console.log('IndexedDB initialized');
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                if (!db.objectStoreNames.contains('offline_data')) {
                    db.createObjectStore('offline_data', { keyPath: 'id' });
                }
                
                if (!db.objectStoreNames.contains('sync_queue')) {
                    const syncStore = db.createObjectStore('sync_queue', { keyPath: 'id', autoIncrement: true });
                    syncStore.createIndex('timestamp', 'timestamp', { unique: false });
                }
            };
        } catch (error) {
            console.log('IndexedDB setup failed:', error);
        }
    }

    async saveOfflineData(key, data) {
        if (!this.db) return;
        
        try {
            const transaction = this.db.transaction(['offline_data'], 'readwrite');
            const store = transaction.objectStore('offline_data');
            await store.put({ id: key, data, timestamp: Date.now() });
        } catch (error) {
            console.log('Failed to save offline data:', error);
        }
    }

    async getOfflineData(key) {
        if (!this.db) return null;
        
        try {
            const transaction = this.db.transaction(['offline_data'], 'readonly');
            const store = transaction.objectStore('offline_data');
            const result = await store.get(key);
            return result ? result.data : null;
        } catch (error) {
            console.log('Failed to get offline data:', error);
            return null;
        }
    }

    async syncOfflineData() {
        if (!this.isOnline || !this.db) return;
        
        try {
            const transaction = this.db.transaction(['sync_queue'], 'readwrite');
            const store = transaction.objectStore('sync_queue');
            const request = store.getAll();
            
            request.onsuccess = async (event) => {
                const items = event.target.result;
                
                for (const item of items) {
                    try {
                        await this.syncItem(item);
                        await store.delete(item.id);
                    } catch (error) {
                        console.log('Sync failed for item:', item);
                    }
                }
                
                if (items.length > 0) {
                    this.showToast(`已同步 ${items.length} 条数据`, 'success');
                }
            };
        } catch (error) {
            console.log('Sync failed:', error);
        }
    }

    async syncItem(item) {
        const response = await fetch(item.endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(item.data)
        });
        
        if (!response.ok) {
            throw new Error('Sync failed');
        }
    }

    setupViewportOptimization() {
        this.setupDynamicViewport();
        this.setupSafeAreaInsets();
        this.setupOrientationChange();
    }

    setupDynamicViewport() {
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
            const updateViewport = () => {
                const isLandscape = window.innerWidth > window.innerHeight;
                const density = window.devicePixelRatio || 1;
                
                let content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
                
                if (isLandscape) {
                    content = 'width=device-width, initial-scale=1.0, maximum-scale=1.5, user-scalable=yes';
                }
                
                viewport.setAttribute('content', content);
            };
            
            updateViewport();
            window.addEventListener('resize', updateViewport);
            window.addEventListener('orientationchange', updateViewport);
        }
    }

    setupSafeAreaInsets() {
        const style = document.createElement('style');
        style.textContent = `
            @supports (padding: max(0px)) {
                .safe-area-top {
                    padding-top: max(var(--space-md), env(safe-area-inset-top));
                }
                .safe-area-bottom {
                    padding-bottom: max(var(--space-md), env(safe-area-inset-bottom));
                }
                .safe-area-left {
                    padding-left: max(var(--space-md), env(safe-area-inset-left));
                }
                .safe-area-right {
                    padding-right: max(var(--space-md), env(safe-area-inset-right));
                }
            }
        `;
        document.head.appendChild(style);
    }

    setupOrientationChange() {
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                window.scrollTo(0, 0);
                this.adjustLayoutForOrientation();
            }, 100);
        });
    }

    adjustLayoutForOrientation() {
        const isLandscape = window.innerWidth > window.innerHeight;
        document.body.classList.toggle('landscape-mode', isLandscape);
        document.body.classList.toggle('portrait-mode', !isLandscape);
    }

    setupScrollOptimization() {
        this.setupSmoothScroll();
        this.setupInfiniteScroll();
        this.setupScrollToTop();
    }

    setupSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    }

    setupInfiniteScroll() {
        const loadMoreThreshold = 200;
        let isLoading = false;

        window.addEventListener('scroll', () => {
            if (isLoading) return;

            const scrollTop = window.pageYOffset;
            const windowHeight = window.innerHeight;
            const documentHeight = document.documentElement.scrollHeight;

            if (scrollTop + windowHeight >= documentHeight - loadMoreThreshold) {
                isLoading = true;
                this.loadMoreContent().finally(() => {
                    isLoading = false;
                });
            }
        });
    }

    async loadMoreContent() {
        const event = new CustomEvent('load-more-content');
        document.dispatchEvent(event);
    }

    setupScrollToTop() {
        let scrollBtn = document.getElementById('scroll-to-top');
        
        if (!scrollBtn) {
            scrollBtn = document.createElement('button');
            scrollBtn.id = 'scroll-to-top';
            scrollBtn.className = 'scroll-to-top';
            scrollBtn.innerHTML = '↑';
            scrollBtn.setAttribute('aria-label', '返回顶部');
            scrollBtn.style.cssText = `
                position: fixed;
                bottom: 80px;
                right: 20px;
                width: 44px;
                height: 44px;
                border-radius: 50%;
                background: linear-gradient(135deg, #3b82f6, #6366f1);
                color: white;
                border: none;
                font-size: 20px;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                z-index: 999;
                display: flex;
                align-items: center;
                justify-content: center;
            `;
            
            scrollBtn.addEventListener('click', () => {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
            
            document.body.appendChild(scrollBtn);
        }

        window.addEventListener('scroll', () => {
            const scrollTop = window.pageYOffset;
            const showThreshold = 300;
            
            if (scrollTop > showThreshold) {
                scrollBtn.style.opacity = '1';
                scrollBtn.style.visibility = 'visible';
            } else {
                scrollBtn.style.opacity = '0';
                scrollBtn.style.visibility = 'hidden';
            }
        });
    }

    setupClickOptimization() {
        this.setupFastClick();
        this.setupButtonFeedback();
        this.setupActiveStates();
    }

    setupFastClick() {
        document.addEventListener('click', (e) => {
            const target = e.target.closest('button, a, .clickable');
            if (target) {
                target.classList.add('clicked');
                setTimeout(() => target.classList.remove('clicked'), 200);
            }
        });
    }

    setupButtonFeedback() {
        const buttons = document.querySelectorAll('button, .btn-primary, .btn-secondary');
        buttons.forEach(btn => {
            btn.addEventListener('touchstart', () => {
                btn.classList.add('touch-pressed');
            });
            
            btn.addEventListener('touchend', () => {
                btn.classList.remove('touch-pressed');
            });
        });
    }

    setupActiveStates() {
        const activeElements = document.querySelectorAll('[data-active]');
        activeElements.forEach(el => {
            el.addEventListener('touchstart', () => {
                el.classList.add('touch-active');
            });
            
            el.addEventListener('touchend', () => {
                el.classList.remove('touch-active');
            });
        });
    }

    setupPerformanceMonitoring() {
        this.setupPageLoadMetrics();
        this.setupCoreWebVitals();
        this.setupPerformanceBudget();
    }

    setupPageLoadMetrics() {
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                entries.forEach(entry => {
                    console.log(`${entry.name}: ${entry.duration}ms`);
                });
            });
            
            observer.observe({ entryTypes: ['measure', 'navigation'] });
        }
        
        window.addEventListener('load', () => {
            const perfData = window.performance.timing;
            const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
            const domReadyTime = perfData.domContentLoadedEventEnd - perfData.navigationStart;
            
            console.log('Page Load Time:', pageLoadTime);
            console.log('DOM Ready Time:', domReadyTime);
        });
    }

    setupCoreWebVitals() {
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                list.getEntries().forEach(entry => {
                    if (entry.name === 'LCP') {
                        console.log('Largest Contentful Paint:', entry.startTime);
                    } else if (entry.name === 'FID') {
                        console.log('First Input Delay:', entry.processingStart - entry.startTime);
                    } else if (entry.name === 'CLS') {
                        console.log('Cumulative Layout Shift:', entry.value);
                    }
                });
            });
            
            observer.observe({ entryTypes: ['largest-contentful-paint', 'first-input', 'layout-shift'] });
        }
    }

    setupPerformanceBudget() {
        const budget = {
            js: 200 * 1024,
            css: 50 * 1024,
            images: 500 * 1024
        };
        
        window.addEventListener('load', () => {
            const resources = performance.getEntriesByType('resource');
            
            resources.forEach(resource => {
                const size = resource.transferSize || resource.encodedBodySize || 0;
                
                if (resource.name.endsWith('.js') && size > budget.js) {
                    console.warn(`Large JS file: ${resource.name} (${(size / 1024).toFixed(2)}KB)`);
                }
                
                if (resource.name.endsWith('.css') && size > budget.css) {
                    console.warn(`Large CSS file: ${resource.name} (${(size / 1024).toFixed(2)}KB)`);
                }
                
                if (['.png', '.jpg', '.jpeg', '.webp'].some(ext => resource.name.endsWith(ext)) && size > budget.images) {
                    console.warn(`Large image: ${resource.name} (${(size / 1024).toFixed(2)}KB)`);
                }
            });
        });
    }

    setupGestureShortcuts() {
        this.setupPinchToZoom();
        this.setupDoubleTap();
        this.setupThreeFingerSwipe();
    }

    setupPinchToZoom() {
        let initialDistance = 0;
        
        document.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                initialDistance = this.getTouchDistance(e.touches[0], e.touches[1]);
            }
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2) {
                const currentDistance = this.getTouchDistance(e.touches[0], e.touches[1]);
                const scale = currentDistance / initialDistance;
                
                const target = e.target.closest('[data-zoomable]');
                if (target) {
                    target.style.transform = `scale(${scale})`;
                }
            }
        }, { passive: true });
    }

    getTouchDistance(touch1, touch2) {
        const dx = touch2.clientX - touch1.clientX;
        const dy = touch2.clientY - touch1.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    setupDoubleTap() {
        let lastTap = 0;
        const tapTimeout = 300;
        
        document.addEventListener('touchend', (e) => {
            const currentTime = Date.now();
            const tapLength = currentTime - lastTap;
            
            if (tapLength < tapTimeout && tapLength > 0) {
                this.triggerDoubleTap(e);
            }
            
            lastTap = currentTime;
        });
    }

    triggerDoubleTap(e) {
        const target = e.target.closest('[data-double-tap]');
        if (target) {
            const action = target.dataset.doubleTap;
            this.hapticFeedback('medium');
            
            const event = new CustomEvent('mobile-double-tap', {
                detail: { action, target },
                bubbles: true
            });
            document.dispatchEvent(event);
        }
    }

    setupThreeFingerSwipe() {
        document.addEventListener('touchstart', (e) => {
            if (e.touches.length === 3) {
                this.handleThreeFingerGesture(e);
            }
        }, { passive: true });
    }

    handleThreeFingerGesture(e) {
        const startX = e.touches[0].clientX;
        let endX = startX;
        
        const moveHandler = (moveEvent) => {
            if (moveEvent.touches.length === 3) {
                endX = moveEvent.touches[0].clientX;
            }
        };
        
        const endHandler = () => {
            const deltaX = endX - startX;
            
            if (Math.abs(deltaX) > 100) {
                if (deltaX > 0) {
                    this.navigateBack();
                } else {
                    this.navigateForward();
                }
            }
            
            document.removeEventListener('touchmove', moveHandler);
            document.removeEventListener('touchend', endHandler);
        };
        
        document.addEventListener('touchmove', moveHandler, { passive: true });
        document.addEventListener('touchend', endHandler);
    }

    navigateBack() {
        const backBtn = document.querySelector('[data-navigation="back"]');
        if (backBtn) {
            backBtn.click();
        } else {
            window.history.back();
        }
    }

    navigateForward() {
        const forwardBtn = document.querySelector('[data-navigation="forward"]');
        if (forwardBtn) {
            forwardBtn.click();
        } else {
            window.history.forward();
        }
    }

    setupAdaptiveUI() {
        this.setupResponsiveTypography();
        this.setupResponsiveSpacing();
        this.setupDeviceDetection();
    }

    setupResponsiveTypography() {
        const updateFontSize = () => {
            const width = window.innerWidth;
            const baseSize = Math.max(14, Math.min(18, width / 80));
            document.documentElement.style.fontSize = `${baseSize}px`;
        };
        
        updateFontSize();
        window.addEventListener('resize', updateFontSize);
    }

    setupResponsiveSpacing() () {
        const updateSpacing = () => {
            const width = window.innerWidth;
            const multiplier = width < 768 ? 0.8 : width < 1024 ? 0.9 : 1;
            
            document.documentElement.style.setProperty('--space-xs', `${0.25 * multiplier}rem`);
            document.documentElement.style.setProperty('--space-sm', `${0.5 * multiplier}rem`);
            document.documentElement.style.setProperty('--space-md', `${1 * multiplier}rem`);
            document.documentElement.style.setProperty('--space-lg', `${1.5 * multiplier}rem`);
            document.documentElement.style.setProperty('--space-xl', `${2 * multiplier}rem`);
        };
        
        updateSpacing();
        window.addEventListener('resize', updateSpacing);
    }

    setupDeviceDetection() {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        const isAndroid = /Android/i.test(navigator.userAgent);
        
        document.body.classList.toggle('mobile-device', isMobile);
        document.body.classList.toggle('ios-device', isIOS);
        document.body.classList.toggle('android-device', isAndroid);
        
        if (isIOS) {
            document.body.classList.add('safe-area-top');
            document.body.classList.add('safe-area-bottom');
        }
    }

    hapticFeedback(type = 'light') {
        if ('vibrate' in navigator) {
            switch (type) {
                case 'light':
                    navigator.vibrate(10);
                    break;
                case 'medium':
                    navigator.vibrate(25);
                    break;
                case 'heavy':
                    navigator.vibrate(50);
                    break;
                case 'success':
                    navigator.vibrate([10, 50, 10]);
                    break;
                case 'error':
                    navigator.vibrate([50, 50, 50]);
                    break;
            }
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: ${type === 'success' ? '#10b981' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10001;
            font-size: 14px;
            font-weight: 500;
            opacity: 0;
            transition: all 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.transform = 'translateX(-50%) translateY(0)';
            toast.style.opacity = '1';
        }, 100);
        
        setTimeout(() => {
            toast.style.transform = 'translateX(-50%) translateY(100px)';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    getViewportWidth() {
        return Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
    }

    getViewportHeight() {
        return Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
    }
}

const mobileOptimizer = new MobileOptimizer();

export default mobileOptimizer;
