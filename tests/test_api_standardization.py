#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API标准化和版本控制测试 - 属性55: API标准化和版本控制
API Standardization and Version Control Tests - Property 55: API Standardization and Version Control

Tests:
- 属性55: API标准化和版本控制
- 验证需求: 28.2
"""

import pytest
from hypothesis import given, settings, example, strategies as st, HealthCheck
from datetime import datetime
from typing import Dict, Any

from bilingual_tutor.web.api_standardization import (
    APIVersion,
    VersionStrategy,
    APIResponse,
    APIError,
    APIMetadata,
    APIValidator,
    APIStandardization,
    APIRouter,
    APIVersionManager,
    standardize_response,
    validate_required_fields,
    add_api_version_metadata
)


class TestAPIVersion:
    """测试API版本枚举"""
    
    def test_api_version_enum(self):
        """测试API版本枚举"""
        assert APIVersion.V1.value == "v1"
        assert APIVersion.V2.value == "v2"
    
    def test_api_version_from_string(self):
        """测试从字符串创建API版本"""
        v1 = APIVersion("v1")
        v2 = APIVersion("v2")
        assert v1 == APIVersion.V1
        assert v2 == APIVersion.V2


class TestAPIResponse:
    """测试标准API响应"""
    
    def test_success_response_creation(self):
        """测试创建成功响应"""
        response = APIResponse(
            success=True,
            message="操作成功",
            data={"key": "value"}
        )
        
        assert response.success is True
        assert response.message == "操作成功"
        assert response.data == {"key": "value"}
        assert response.timestamp is not None
    
    def test_error_response_creation(self):
        """测试创建错误响应"""
        response = APIResponse(
            success=False,
            message="操作失败",
            error_code="ERROR_001"
        )
        
        assert response.success is False
        assert response.message == "操作失败"
        assert response.error_code == "ERROR_001"
    
    def test_response_to_dict(self):
        """测试响应转换为字典"""
        response = APIResponse(
            success=True,
            message="测试",
            data={"test": "data"}
        )
        
        response_dict = response.to_dict()
        assert "success" in response_dict
        assert "message" in response_dict
        assert "data" in response_dict
        assert "timestamp" in response_dict
    
    def test_response_to_json(self):
        """测试响应转换为JSON"""
        response = APIResponse(
            success=True,
            message="测试"
        )
        
        json_str = response.to_json()
        assert '"success": true' in json_str
        assert '"message": "测试"' in json_str


class TestAPIValidator:
    """测试API验证器"""
    
    def test_validate_email_valid(self):
        """测试验证有效邮箱"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co",
            "email+tag@example.org"
        ]
        
        for email in valid_emails:
            assert APIValidator.validate_email(email) is True
    
    def test_validate_email_invalid(self):
        """测试验证无效邮箱"""
        invalid_emails = [
            "invalid",
            "@example.com",
            "test@",
            "test@domain",
            "test @example.com"
        ]
        
        for email in invalid_emails:
            assert APIValidator.validate_email(email) is False
    
    def test_validate_password_strong(self):
        """测试验证强密码"""
        strong_password = "StrongP@ssw0rd"
        result = APIValidator.validate_password(strong_password)
        
        assert result["valid"] is True
        assert len(result["issues"]) == 0
    
    def test_validate_password_weak(self):
        """测试验证弱密码"""
        weak_password = "weak"
        result = APIValidator.validate_password(weak_password)
        
        assert result["valid"] is False
        assert len(result["issues"]) > 0
    
    def test_validate_pagination_valid(self):
        """测试验证有效分页参数"""
        result = APIValidator.validate_pagination(page=1, page_size=20)
        
        assert result["valid"] is True
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["offset"] == 0
    
    def test_validate_pagination_invalid_page(self):
        """测试验证无效页码"""
        result = APIValidator.validate_pagination(page=0, page_size=20)
        
        assert result["valid"] is False
        assert "error" in result
    
    def test_validate_pagination_invalid_page_size(self):
        """测试验证无效页大小"""
        result = APIValidator.validate_pagination(page=1, page_size=0)
        
        assert result["valid"] is False
        assert "error" in result
    
    def test_validate_pagination_exceeds_max(self):
        """测试验证超过最大页大小"""
        result = APIValidator.validate_pagination(page=1, page_size=200, max_page_size=100)
        
        assert result["valid"] is False
        assert "error" in result


class TestAPIStandardization:
    """测试API标准化"""
    
    @pytest.fixture
    def standardization(self):
        """创建API标准化实例"""
        return APIStandardization(
            default_version=APIVersion.V1,
            version_strategy=VersionStrategy.HEADER,
            enable_request_validation=True,
            enable_response_standardization=True,
            max_page_size=100
        )
    
    def test_get_default_version(self, standardization):
        """测试获取默认版本"""
        version = standardization.get_api_version()
        assert version == APIVersion.V1
    
    def test_create_success_response(self, standardization):
        """测试创建成功响应"""
        response = standardization.create_success_response(
            data={"test": "data"},
            message="操作成功"
        )
        
        assert response.success is True
        assert response.message == "操作成功"
        assert response.data == {"test": "data"}
    
    def test_create_error_response(self, standardization):
        """测试创建错误响应"""
        error = standardization.create_error_response(
            error_code="TEST_ERROR",
            message="测试错误",
            status_code=400
        )
        
        assert error.error_code == "TEST_ERROR"
        assert error.message == "测试错误"
        assert error.status_code == 400
    
    def test_create_paginated_response(self, standardization):
        """测试创建分页响应"""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = standardization.create_paginated_response(
            items=items,
            total=10,
            page=1,
            page_size=3
        )
        
        assert response.success is True
        assert response.data["items"] == items
        assert response.data["pagination"]["total"] == 10
        assert response.data["pagination"]["page"] == 1
        assert response.data["pagination"]["page_size"] == 3
        assert response.data["pagination"]["total_pages"] == 4
    
    def test_validate_pagination_params(self, standardization):
        """测试验证分页参数"""
        result = standardization.validate_pagination_params(page=2, page_size=20)
        
        assert result["valid"] is True
        assert result["page"] == 2
        assert result["page_size"] == 20
        assert result["offset"] == 20
    
    def test_validate_request_data_valid(self, standardization):
        """测试验证有效请求数据"""
        data = {"name": "test", "email": "test@example.com"}
        result = standardization.validate_request_data(
            data=data,
            required_fields=["name", "email"]
        )
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_request_data_invalid(self, standardization):
        """测试验证无效请求数据"""
        data = {"name": "test"}
        result = standardization.validate_request_data(
            data=data,
            required_fields=["name", "email"]
        )
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "email" in str(result["errors"])
    
    def test_standardize_endpoint_path(self, standardization):
        """测试标准化端点路径"""
        path = "/users"
        standardized = standardization.standardize_endpoint_path(
            path=path,
            version=APIVersion.V2
        )
        
        assert standardized == "/v2/users"
    
    def test_standardize_endpoint_path_without_leading_slash(self, standardization):
        """测试标准化没有前导斜杠的端点路径"""
        path = "users"
        standardized = standardization.standardize_endpoint_path(
            path=path,
            version=APIVersion.V2
        )
        
        assert standardized == "/v2/users"


class TestProperty55APIStandardization:
    """属性55: API标准化和版本控制"""
    
    @pytest.fixture
    def standardization(self):
        """创建API标准化实例"""
        return APIStandardization(
            default_version=APIVersion.V1,
            version_strategy=VersionStrategy.HEADER,
            enable_request_validation=True,
            enable_response_standardization=True,
            max_page_size=100
        )
    
    @given(st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=50))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_55_pagination_calculation(self, standardization, items):
        """
        属性55: API标准化和版本控制
        
        验证需求: 28.2
        
        属性: 分页响应中的总页数计算必须准确
        """
        total = sum(items)
        page = 1
        page_size = 20
        expected_total_pages = (total + page_size - 1) // page_size
        
        response = standardization.create_paginated_response(
            items=[{"id": i} for i in items],
            total=total,
            page=page,
            page_size=page_size
        )
        
        actual_total_pages = response.data["pagination"]["total_pages"]
        assert actual_total_pages == expected_total_pages
    
    @given(st.integers(min_value=1, max_value=1000), st.integers(min_value=1, max_value=100))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_55_pagination_offset_calculation(self, standardization, page, page_size):
        """
        属性55: API标准化和版本控制
        
        验证需求: 28.2
        
        属性: 分页偏移量计算必须准确
        """
        result = standardization.validate_pagination_params(page=page, page_size=page_size)
        
        if result["valid"]:
            expected_offset = (page - 1) * page_size
            assert result["offset"] == expected_offset
    
    @given(st.integers(min_value=1, max_value=100), st.integers(min_value=1, max_value=100))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_55_pagination_boundary_checks(self, standardization, total, page_size):
        """
        属性55: API标准化和版本控制
        
        验证需求: 28.2
        
        属性: 分页边界检查必须正确
        """
        response = standardization.create_paginated_response(
            items=[{"id": i} for i in range(page_size)],
            total=total,
            page=1,
            page_size=page_size
        )
        
        pagination = response.data["pagination"]
        total_pages = (total + page_size - 1) // page_size
        
        assert pagination["has_next"] == (total_pages > 1)
        assert pagination["has_prev"] is False
    
    @given(st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=50))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_55_response_structure_consistency(self, standardization, numbers):
        """
        属性55: API标准化和版本控制
        
        验证需求: 28.2
        
        属性: 所有响应必须包含一致的结构
        """
        response = standardization.create_success_response(
            data={"numbers": numbers},
            message="测试"
        )
        
        assert hasattr(response, "success")
        assert hasattr(response, "message")
        assert hasattr(response, "data")
        assert hasattr(response, "timestamp")
        
        response_dict = response.to_dict()
        assert "success" in response_dict
        assert "message" in response_dict
        assert "data" in response_dict
        assert "timestamp" in response_dict
    
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_55_total_pages_integer(self, standardization, total):
        """
        属性55: API标准化和版本控制
        
        验证需求: 28.2
        
        属性: 总页数必须为整数
        """
        page_size = 20
        response = standardization.create_paginated_response(
            items=[],
            total=total,
            page=1,
            page_size=page_size
        )
        
        total_pages = response.data["pagination"]["total_pages"]
        assert isinstance(total_pages, int)
        assert total_pages > 0
    
    @given(st.lists(st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"), min_size=1, max_size=10))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_55_required_field_validation(self, standardization, field_names):
        """
        属性55: API标准化和版本控制
        
        验证需求: 28.2
        
        属性: 必需字段验证必须准确
        """
        data = {name: f"value_{i}" for i, name in enumerate(field_names)}
        result = standardization.validate_request_data(
            data=data,
            required_fields=field_names
        )
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    @given(st.lists(st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"), min_size=1, max_size=10))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])   
    def test_property_55_missing_field_detection(self, standardization, field_names):
        """
        属性55: API标准化和版本控制
        
        验证需求: 28.2
        
        属性: 缺失字段检测必须准确
        """
        unique_field_names = list(set(field_names))
        if len(unique_field_names) > 1:
            partial_fields = unique_field_names[:-1]
            data = {name: f"value_{i}" for i, name in enumerate(partial_fields)}
            result = standardization.validate_request_data(
                data=data,
                required_fields=unique_field_names
            )
            
            assert result["valid"] is False
            assert len(result["errors"]) > 0
            assert unique_field_names[-1] in str(result["errors"])
    
    @given(st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=50))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_55_data_integrity_in_response(self, standardization, numbers):
        """
        属性55: API标准化和版本控制
        
        验证需求: 28.2
        
        属性: 响应中的数据必须保持完整性
        """
        original_data = {"numbers": numbers}
        response = standardization.create_success_response(data=original_data)
        
        assert response.data == original_data
    
    @given(st.integers(min_value=1, max_value=1000), st.integers(min_value=1, max_value=50))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_55_edge_case_single_page(self, standardization, total, page_size):
        """
        属性55: API标准化和版本控制
        
        验证需求: 28.2
        
        属性: 单页情况下的分页必须正确
        """
        if total <= page_size:
            response = standardization.create_paginated_response(
                items=[],
                total=total,
                page=1,
                page_size=page_size
            )
            
            pagination = response.data["pagination"]
            assert pagination["has_next"] is False
            assert pagination["has_prev"] is False
            assert pagination["total_pages"] == 1


class TestAPIRouter:
    """测试API路由器"""
    
    @pytest.fixture
    def router(self):
        """创建API路由器"""
        standardization = APIStandardization()
        return APIRouter(standardization=standardization, prefix="/api")
    
    def test_register_route(self, router):
        """测试注册路由"""
        def handler():
            return {"data": "test"}
        
        router.register_route(
            path="/test",
            method="GET",
            handler=handler,
            version=APIVersion.V1
        )
        
        assert len(router.routes) > 0
    
    def test_list_routes(self, router):
        """测试列出所有路由"""
        def handler():
            return {"data": "test"}
        
        router.register_route(
            path="/test1",
            method="GET",
            handler=handler,
            version=APIVersion.V1
        )
        
        router.register_route(
            path="/test2",
            method="POST",
            handler=handler,
            version=APIVersion.V2
        )
        
        routes = router.list_routes()
        assert len(routes) == 2


class TestAPIVersionManager:
    """测试API版本管理器"""
    
    @pytest.fixture
    def version_manager(self):
        """创建API版本管理器"""
        return APIVersionManager()
    
    def test_get_version_info(self, version_manager):
        """测试获取版本信息"""
        info = version_manager.get_version_info("v1")
        
        assert info is not None
        assert "status" in info
        assert "deprecated" in info
    
    def test_deprecate_version(self, version_manager):
        """测试弃用版本"""
        result = version_manager.deprecate_version("v1")
        
        assert result["success"] is True
        assert version_manager.versions["v1"]["deprecated"] is True
    
    def test_set_migration_guide(self, version_manager):
        """测试设置迁移指南"""
        guide = "从v1迁移到v2的指南"
        version_manager.set_migration_guide("v1", "v2", guide)
        
        retrieved_guide = version_manager.get_migration_guide("v1", "v2")
        assert retrieved_guide == guide
    
    def test_get_nonexistent_migration_guide(self, version_manager):
        """测试获取不存在的迁移指南"""
        guide = version_manager.get_migration_guide("v1", "v3")
        assert guide is None


class TestDecorators:
    """测试装饰器"""
    
    @given(st.booleans(), st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_standardize_response_decorator(self, success, message):
        """测试标准化响应装饰器"""
        @standardize_response(success=success, message=message)
        def test_function():
            return {"data": "test"}
        
        result = test_function()
        
        assert result["success"] == success
        if message:
            assert result["message"] == message
    
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_add_api_version_metadata_decorator(self, version_value):
        """测试添加API版本元数据装饰器"""
        try:
            version = APIVersion(version_value)
            
            @add_api_version_metadata(version)
            def test_function():
                return {"data": "test"}
            
            result = test_function()
            
            assert "metadata" in result
            assert result["metadata"]["api_version"] == version.value
        except ValueError:
            pass
