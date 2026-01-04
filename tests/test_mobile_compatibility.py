import pytest
from hypothesis import given, strategies as st, settings
from typing import Dict, List, Tuple
import re


class TestMobileCompatibility:
    def _get_base_template_content(self):
        try:
            with open('bilingual_tutor/web/templates/base.html', 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ''
    
    def _get_css_content(self):
        try:
            with open('bilingual_tutor/web/static/css/style.css', 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ''
    
    def _get_js_content(self):
        try:
            with open('bilingual_tutor/web/static/js/mobile.js', 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ''
    
    def test_viewport_meta_tag_exists(self):
        html = self._get_base_template_content()
        
        assert 'name="viewport"' in html
        assert 'width=device-width' in html
        assert 'initial-scale=1.0' in html
    
    @given(st.integers(min_value=320, max_value=414), st.integers(min_value=568, max_value=896))
    def test_responsive_breakpoints_small(self, width: int, height: int):
        viewport_sizes = [
            (320, 568),
            (375, 667),
            (414, 896)
        ]
        
        for vw, vh in viewport_sizes:
            assert self._is_breakpoint_valid(vw, vh)
    
    @given(st.integers(min_value=768, max_value=1024), st.integers(min_value=768, max_value=1366))
    def test_responsive_breakpoints_medium(self, width: int, height: int):
        viewport_sizes = [
            (768, 1024),
            (834, 1194),
            (1024, 1366)
        ]
        
        for vw, vh in viewport_sizes:
            assert self._is_breakpoint_valid(vw, vh)
    
    @given(st.integers(min_value=1025, max_value=1920), st.integers(min_value=768, max_value=1080))
    def test_responsive_breakpoints_large(self, width: int, height: int):
        viewport_sizes = [
            (1024, 768),
            (1280, 720),
            (1366, 768),
            (1440, 900),
            (1920, 1080)
        ]
        
        for vw, vh in viewport_sizes:
            assert self._is_breakpoint_valid(vw, vh)
    
    def _is_breakpoint_valid(self, width: int, height: int) -> bool:
        css_content = str(self._get_css_content())
        
        media_queries = [
            '@media' in css_content,
            'max-width' in css_content,
            '480px' in css_content,
            '768px' in css_content,
            '1024px' in css_content
        ]
        
        return all(media_queries)
    
    @given(st.integers(min_value=320, max_value=1920))
    def test_touch_target_sizes(self, viewport_width: int):
        min_touch_size = 44
        
        css_content = self._get_css_content()
        
        button_styles = re.findall(r'(button|\.btn-primary|\.btn-secondary)\s*\{([^}]+)\}', css_content)
        
        for selector, styles in button_styles:
            if 'min-height' in styles:
                height_match = re.search(r'min-height:\s*(\d+)(px|rem)', styles)
                if height_match:
                    size_value = int(height_match.group(1))
                    unit = height_match.group(2)
                    
                    if unit == 'px':
                        assert size_value >= min_touch_size, f"{selector} touch target too small"
                    elif unit == 'rem':
                        assert size_value >= 2.75, f"{selector} touch target too small in rem"
    
    def test_mobile_specific_breakpoint_480(self):
        css_content = self._get_css_content()
        
        assert '@media (max-width: 480px)' in css_content
        
        styles_at_480 = re.search(r'@media\s*\(max-width:\s*480px\)\s*\{(.+?)@media', css_content, re.DOTALL)
        if styles_at_480:
            mobile_styles = styles_at_480.group(1)
        else:
            mobile_styles = css_content[css_content.find('@media (max-width: 480px)'):]
            mobile_styles = mobile_styles[:mobile_styles.find('@media')] if '@media' in mobile_styles else mobile_styles
        
        assert '.navbar' in mobile_styles
        assert '.welcome-section' in mobile_styles
        assert '.btn-primary' in mobile_styles
    
    def test_tablet_specific_breakpoint_768(self):
        css_content = self._get_css_content()
        
        assert '@media (max-width: 768px)' in css_content
        
        styles_at_768 = re.search(r'@media\s*\(max-width:\s*768px\)\s*\{(.+?)@media', css_content, re.DOTALL)
        if styles_at_768:
            tablet_styles = styles_at_768.group(1)
        else:
            tablet_styles = css_content[css_content.find('@media (max-width: 768px)'):]
            tablet_styles = tablet_styles[:tablet_styles.find('@media')] if '@media' in tablet_styles else tablet_styles
        
        assert '.navbar' in tablet_styles
        assert '.nav-link' in tablet_styles
        assert '.welcome-section' in tablet_styles
    
    def test_laptop_specific_breakpoint_1024(self):
        css_content = self._get_css_content()
        
        assert '@media (max-width: 1024px)' in css_content
        
        styles_at_1024 = re.search(r'@media\s*\(max-width:\s*1024px\)\s*\{(.+?)@media', css_content, re.DOTALL)
        if styles_at_1024:
            laptop_styles = styles_at_1024.group(1)
        else:
            laptop_styles = css_content[css_content.find('@media (max-width: 1024px)'):]
            laptop_styles = laptop_styles[:laptop_styles.find('@media')] if '@media' in laptop_styles else laptop_styles
        
        assert '.auth-container' in laptop_styles
        assert '.level-overview' in laptop_styles
        assert '.activities-section' in laptop_styles
    
    def test_orientation_handling(self):
        css_content = self._get_css_content()
        js_content = self._get_js_content()
        
        assert 'orientationchange' in js_content
        assert '.landscape-mode' in css_content
    
    @given(st.sampled_from(['Android', 'iOS', 'Desktop']))
    def test_device_detection(self, device_type: str):
        js_content = self._get_js_content()
        
        assert 'isMobileDevice' in js_content
        assert 'setupDeviceDetection' in js_content
        
        if device_type == 'Android':
            assert 'android-device' in self._get_css_content()
        elif device_type == 'iOS':
            assert 'ios-device' in self._get_css_content()
    
    @given(st.sampled_from(['safe-area-inset-top', 'safe-area-inset-bottom']))
    def test_safe_area_support(self, safe_area: str):
        css_content = self._get_css_content()
        
        assert 'env(' in css_content
        assert safe_area in css_content
        
        safe_area_classes = [
            '.safe-area-top',
            '.safe-area-bottom'
        ]
        
        assert any(cls in css_content for cls in safe_area_classes)
    
    @given(st.sampled_from(['touchstart', 'touchmove', 'touchend', 'touchcancel']))
    def test_touch_event_handling(self, event_name: str):
        js_content = self._get_js_content()
        
        assert f"'{event_name}'" in js_content or f'"{event_name}"' in js_content
        assert 'handleTouchStart' in js_content
        assert 'handleTouchMove' in js_content
        assert 'handleTouchEnd' in js_content
    
    @given(st.integers(min_value=0, max_value=100))
    def test_gesture_recognition(self, swipe_distance: int):
        js_content = self._get_js_content()
        
        assert 'handleSwipe' in js_content
        assert 'minSwipeDistance' in js_content
        assert 'touchStartX' in js_content
        assert 'touchEndX' in js_content
        
        if swipe_distance > 50:
            assert 'triggerSwipeAction' in js_content
    
    @given(st.sampled_from(['left', 'right', 'up', 'down']))
    def test_swipe_directions(self, direction: str):
        js_content = self._get_js_content()
        
        assert f"'{direction}'" in js_content or f'"{direction}"' in js_content
        
        if direction in ['left', 'right']:
            assert 'navigateNext' in js_content or 'navigatePrevious' in js_content
    
    def test_service_worker_registration(self):
        html_content = self._get_base_template_content()
        js_content = self._get_js_content()
        
        assert "'serviceWorker'" in html_content or '"serviceWorker"' in html_content
        assert 'register' in html_content
        assert 'sw.js' in html_content
    
    def test_offline_support(self):
        html_content = self._get_base_template_content()
        js_content = self._get_js_content()
        
        assert 'offline' in js_content.lower()
        assert 'handleOnline' in js_content
        assert 'handleOffline' in js_content
        assert 'isOnline' in js_content
    
    def test_pwa_manifest_requirements(self):
        html_content = self._get_base_template_content()
        
        pwa_meta_tags = [
            'apple-mobile-web-app-capable',
            'theme-color',
            'mobile-web-app-capable',
            'format-detection'
        ]
        
        for meta_tag in pwa_meta_tags:
            assert meta_tag in html_content
    
    @given(st.integers(min_value=10, max_value=200))
    def test_font_scaling(self, base_size: int):
        css_content = self._get_css_content()
        
        assert 'font-size' in css_content
        assert 'rem' in css_content
        
        root_styles = re.search(r':root\s*\{([^}]+)\}', css_content)
        if root_styles:
            assert '--space-md' in root_styles.group(1)
    
    @given(st.sampled_from(['input', 'select', 'textarea', 'button']))
    def test_form_element_sizing(self, element_type: str):
        css_content = self._get_css_content()
        
        element_selectors = [
            f'.form-group {element_type}',
            f'{element_type}',
            'button',
            '.btn-primary',
            '.btn-secondary'
        ]
        
        for selector in element_selectors:
            selector_pattern = re.escape(selector)
            element_styles = re.findall(rf'{selector_pattern}\s*\{{([^}}]+)\}}', css_content, re.DOTALL)
            
            for styles in element_styles:
                if 'min-height' in styles or 'height' in styles:
                    height_match = re.search(r'(min-)?height:\s*(\d+)(px|rem)', styles)
                    if height_match:
                        size_value = int(height_match.group(2))
                        unit = height_match.group(3)
                        
                        if unit == 'px':
                            assert size_value >= 44, f"{selector} element too small"
    
    @given(st.sampled_from(['reduced-motion', 'high-contrast']))
    def test_accessibility_preferences(self, preference: str):
        css_content = self._get_css_content()
        
        if preference == 'reduced-motion':
            assert 'prefers-reduced-motion' in css_content
            assert 'transition-duration: 0.01ms' in css_content
        elif preference == 'high-contrast':
            assert 'prefers-contrast: high' in css_content
    
    def test_loading_states(self):
        css_content = self._get_css_content()
        
        assert '.loading' in css_content or '.loading-skeleton' in css_content
        
        if '.loading-skeleton' in css_content:
            assert 'loading-shimmer' in css_content
    
    @given(st.integers(min_value=0, max_value=5))
    def test_error_states(self, error_count: int):
        css_content = self._get_css_content()
        
        assert '.error' in css_content or '.form-error' in css_content
        
        error_elements = [
            '.error',
            '.form-error',
            '.error-page',
            '.error-icon'
        ]
        
        assert any(el in css_content for el in error_elements)
    
    @given(st.integers(min_value=100, max_value=5000))
    def test_responsive_spacing(self, viewport_width: int):
        css_content = self._get_css_content()
        
        css_variables = re.search(r':root\s*\{([^}]+)\}', css_content)
        if css_variables:
            variables = css_variables.group(1)
            
            spacing_vars = ['--space-xs', '--space-sm', '--space-md', '--space-lg', '--space-xl']
            assert all(var in variables for var in spacing_vars)
    
    def test_scroll_optimization(self):
        js_content = self._get_js_content()
        
        assert 'setupScrollOptimization' in js_content
        assert 'smooth' in js_content
        assert 'setupScrollToTop' in js_content
    
    def test_performance_monitoring(self):
        js_content = self._get_js_content()
        
        assert 'setupPerformanceMonitoring' in js_content
        assert 'PerformanceObserver' in js_content
        assert 'load' in js_content
    
    @given(st.sampled_from(['vibrate', 'touch', 'keyboard']))
    def test_haptic_feedback(self, feedback_type: str):
        js_content = self._get_js_content()
        
        if feedback_type == 'vibrate':
            assert 'hapticFeedback' in js_content
            assert 'vibrate' in js_content
    
    def test_adaptive_ui(self):
        js_content = self._get_js_content()
        
        assert 'setupAdaptiveUI' in js_content
        assert 'setupResponsiveTypography' in js_content
        assert 'setupResponsiveSpacing' in js_content


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
