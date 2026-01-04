#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API标准化和版本控制模块
API Standardization and Version Control Module

Features:
- RESTful API标准实现
- API版本控制（URL版本和Header版本）
- 标准响应格式
- 请求验证
- 错误处理标准化
- 文档生成支持
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union, Callable
from enum import Enum
from dataclasses import dataclass, field, asdict
from functools import wraps
import json
import re

try:
    from fastapi import Request, Response, HTTPException, status
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field, validator
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    BaseModel = object
    Field = lambda **kwargs: None
    validator = lambda func: func


class APIVersion(Enum):
    """API版本"""
    V1 = "v1"
    V2 = "v2"


class VersionStrategy(Enum):
    """版本策略"""
    URL = "url"
    HEADER = "header"
    QUERY = "query"


@dataclass
class APIResponse:
    """标准API响应"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class APIError:
    """API错误"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    status_code: int = 400
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class APIMetadata:
    """API元数据"""
    version: str
    endpoint: str
    method: str
    request_id: Optional[str] = None
    response_time_ms: Optional[float] = None
    rate_limit: Optional[Dict[str, int]] = None


class APIValidator:
    """API验证器"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """验证密码强度"""
        issues = []
        
        if len(password) < 8:
            issues.append("密码长度至少8个字符")
        
        if not re.search(r'[A-Z]', password):
            issues.append("密码必须包含大写字母")
        
        if not re.search(r'[a-z]', password):
            issues.append("密码必须包含小写字母")
        
        if not re.search(r'\d', password):
            issues.append("密码必须包含数字")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("密码必须包含特殊字符")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    @staticmethod
    def validate_pagination(page: int, page_size: int, max_page_size: int = 100) -> Dict[str, Any]:
        """验证分页参数"""
        if page < 1:
            return {
                "valid": False,
                "error": "页码必须大于0"
            }
        
        if page_size < 1:
            return {
                "valid": False,
                "error": "每页数量必须大于0"
            }
        
        if page_size > max_page_size:
            return {
                "valid": False,
                "error": f"每页数量不能超过{max_page_size}"
            }
        
        return {
            "valid": True,
            "page": page,
            "page_size": page_size,
            "offset": (page - 1) * page_size
        }


class APIStandardization:
    """API标准化"""
    
    def __init__(
        self,
        default_version: APIVersion = APIVersion.V1,
        version_strategy: VersionStrategy = VersionStrategy.HEADER,
        enable_request_validation: bool = True,
        enable_response_standardization: bool = True,
        max_page_size: int = 100
    ):
        self.default_version = default_version
        self.version_strategy = version_strategy
        self.enable_request_validation = enable_request_validation
        self.enable_response_standardization = enable_response_standardization
        self.max_page_size = max_page_size
        self.validator = APIValidator()
    
    def get_api_version(
        self,
        request: Optional[Request] = None,
        version_header: str = "X-API-Version",
        version_query: str = "version"
    ) -> APIVersion:
        """获取API版本"""
        if not request and FASTAPI_AVAILABLE:
            return self.default_version
        
        if self.version_strategy == VersionStrategy.HEADER:
            if request and hasattr(request, 'headers'):
                version = request.headers.get(version_header)
                if version:
                    try:
                        return APIVersion(version.lower())
                    except ValueError:
                        return self.default_version
        
        elif self.version_strategy == VersionStrategy.QUERY:
            if request and hasattr(request, 'query_params'):
                version = request.query_params.get(version_query)
                if version:
                    try:
                        return APIVersion(version.lower())
                    except ValueError:
                        return self.default_version
        
        elif self.version_strategy == VersionStrategy.URL:
            if request and hasattr(request, 'url'):
                path = str(request.url)
                if "/v2/" in path:
                    return APIVersion.V2
                elif "/v1/" in path:
                    return APIVersion.V1
        
        return self.default_version
    
    def create_response(
        self,
        success: bool,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """创建标准响应"""
        return APIResponse(
            success=success,
            message=message,
            data=data,
            error_code=error_code,
            metadata=metadata
        )
    
    def create_error_response(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ) -> APIError:
        """创建错误响应"""
        return APIError(
            error_code=error_code,
            message=message,
            details=details,
            status_code=status_code
        )
    
    def create_success_response(
        self,
        data: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ) -> APIResponse:
        """创建成功响应"""
        return APIResponse(
            success=True,
            message=message or "操作成功",
            data=data
        )
    
    def create_paginated_response(
        self,
        items: List[Any],
        total: int,
        page: int,
        page_size: int
    ) -> APIResponse:
        """创建分页响应"""
        total_pages = (total + page_size - 1) // page_size
        
        return APIResponse(
            success=True,
            data={
                "items": items,
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )
    
    def validate_pagination_params(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """验证分页参数"""
        return self.validator.validate_pagination(page, page_size, self.max_page_size)
    
    def validate_request_data(
        self,
        data: Dict[str, Any],
        required_fields: Optional[List[str]] = None,
        optional_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """验证请求数据"""
        errors = []
        
        if required_fields:
            for field in required_fields:
                if field not in data or data[field] is None:
                    errors.append(f"缺少必需字段: {field}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def standardize_endpoint_path(
        self,
        path: str,
        version: Optional[APIVersion] = None
    ) -> str:
        """标准化端点路径"""
        if version is None:
            version = self.default_version
        
        if not path.startswith("/"):
            path = "/" + path
        
        if self.version_strategy == VersionStrategy.URL:
            if not path.startswith(f"/{version.value}/"):
                path = f"/{version.value}{path}"
        else:
            path = f"/{version.value}{path}" if not path.startswith(f"/{version.value}/") else path
        
        return path
    
    def get_endpoint_info(
        self,
        request: Optional[Request] = None,
        path: Optional[str] = None,
        method: Optional[str] = None
    ) -> Dict[str, str]:
        """获取端点信息"""
        info = {
            "version": self.default_version.value,
            "path": path or "/",
            "method": method or "GET"
        }
        
        if request:
            if FASTAPI_AVAILABLE:
                info["version"] = self.get_api_version(request).value
                info["path"] = str(request.url.path) if hasattr(request, 'url') else path or "/"
                info["method"] = request.method if hasattr(request, 'method') else method or "GET"
        
        return info
    
    def extract_query_params(
        self,
        request: Optional[Request] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """提取查询参数"""
        if request and FASTAPI_AVAILABLE and hasattr(request, 'query_params'):
            return dict(request.query_params)
        elif params:
            return params
        return {}


def standardize_response(success: bool = True, message: Optional[str] = None, 
                       data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """装饰器: 标准化响应"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            if isinstance(result, dict):
                if "success" not in result:
                    result["success"] = success
                if message and "message" not in result:
                    result["message"] = message
                if data and "data" not in result:
                    result["data"] = data
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if isinstance(result, dict):
                if "success" not in result:
                    result["success"] = success
                if message and "message" not in result:
                    result["message"] = message
                if data and "data" not in result:
                    result["data"] = data
            
            return result
        
        return async_wrapper if hasattr(func, '__await__') else sync_wrapper
    return decorator


def validate_required_fields(required_fields: List[str]) -> Callable:
    """装饰器: 验证必需字段"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request and FASTAPI_AVAILABLE:
                if hasattr(request, 'json'):
                    try:
                        data = await request.json()
                        missing = [f for f in required_fields if f not in data]
                        if missing:
                            raise HTTPException(
                                status_code=400,
                                detail=f"缺少必需字段: {', '.join(missing)}"
                            )
                    except Exception:
                        pass
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return async_wrapper if hasattr(func, '__await__') else sync_wrapper
    return decorator


def add_api_version_metadata(version: APIVersion) -> Callable:
    """装饰器: 添加API版本元数据"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            if isinstance(result, dict):
                if "metadata" not in result:
                    result["metadata"] = {}
                result["metadata"]["api_version"] = version.value
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if isinstance(result, dict):
                if "metadata" not in result:
                    result["metadata"] = {}
                result["metadata"]["api_version"] = version.value
            
            return result
        
        return async_wrapper if hasattr(func, '__await__') else sync_wrapper
    return decorator


class APIRouter:
    """API路由器"""
    
    def __init__(
        self,
        standardization: APIStandardization,
        prefix: str = "/api"
    ):
        self.standardization = standardization
        self.prefix = prefix
        self.routes: Dict[str, Dict[str, Any]] = {}
    
    def register_route(
        self,
        path: str,
        method: str,
        handler: Callable,
        version: Optional[APIVersion] = None,
        authenticated: bool = False
    ):
        """注册路由"""
        standardized_path = self.standardization.standardize_endpoint_path(path, version)
        full_path = f"{self.prefix}{standardized_path}"
        
        self.routes[full_path] = {
            "method": method.upper(),
            "handler": handler,
            "version": version or self.standardization.default_version,
            "authenticated": authenticated,
            "original_path": path
        }
    
    def get_route(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """获取路由"""
        for route_path, route_info in self.routes.items():
            if route_info["method"] == method.upper():
                return route_info
        return None
    
    def list_routes(self) -> List[Dict[str, Any]]:
        """列出所有路由"""
        return [
            {
                "path": path,
                "method": info["method"],
                "version": info["version"].value,
                "authenticated": info["authenticated"]
            }
            for path, info in self.routes.items()
        ]


class APIVersionManager:
    """API版本管理器"""
    
    def __init__(self):
        self.versions: Dict[str, Dict[str, Any]] = {
            "v1": {
                "status": "stable",
                "deprecated": False,
                "deprecation_date": None,
                "sunset_date": None
            },
            "v2": {
                "status": "stable",
                "deprecated": False,
                "deprecation_date": None,
                "sunset_date": None
            }
        }
        self.migration_guide: Dict[str, str] = {}
    
    def get_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """获取版本信息"""
        return self.versions.get(version)
    
    def deprecate_version(
        self,
        version: str,
        deprecation_date: Optional[datetime] = None,
        sunset_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """弃用版本"""
        if version not in self.versions:
            return {
                "success": False,
                "message": f"版本 {version} 不存在"
            }
        
        self.versions[version]["deprecated"] = True
        self.versions[version]["deprecation_date"] = deprecation_date.isoformat() if deprecation_date else None
        self.versions[version]["sunset_date"] = sunset_date.isoformat() if sunset_date else None
        
        return {
            "success": True,
            "message": f"版本 {version} 已标记为弃用"
        }
    
    def set_migration_guide(self, from_version: str, to_version: str, guide: str):
        """设置迁移指南"""
        key = f"{from_version} -> {to_version}"
        self.migration_guide[key] = guide
    
    def get_migration_guide(self, from_version: str, to_version: str) -> Optional[str]:
        """获取迁移指南"""
        key = f"{from_version} -> {to_version}"
        return self.migration_guide.get(key)
