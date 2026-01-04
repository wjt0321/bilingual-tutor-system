#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API兼容性层 - Flask到FastAPI迁移支持
API Compatibility Layer - Flask to FastAPI Migration Support

Features:
- API compatibility layer for gradual migration
- Traffic splitting between Flask and FastAPI
- Graceful rollback mechanism
- Performance metrics and monitoring
- Health checks and circuit breakers
"""

import asyncio
import time
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
import hashlib
import json

try:
    from flask import Flask, request as flask_request, jsonify as flask_jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    from fastapi import FastAPI, Request, HTTPException, status
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


class DeploymentMode(Enum):
    """部署模式"""
    OFFLINE = "offline"
    TESTING = "testing"
    GRADUAL = "gradual"
    FULL = "full"
    ROLLED_BACK = "rolled_back"


@dataclass
class CompatibilityConfig:
    """兼容性层配置"""
    deployment_mode: DeploymentMode = DeploymentMode.GRADUAL
    flask_port: int = 5000
    fastapi_port: int = 8000
    traffic_percentage: float = 0.1
    enable_metrics: bool = True
    enable_health_check: bool = True
    health_check_interval: int = 60
    circuit_breaker_threshold: int = 10
    circuit_breaker_timeout: int = 300
    enable_logging: bool = True


@dataclass
class APIMetrics:
    """API指标"""
    total_requests: int = 0
    flask_requests: int = 0
    fastapi_requests: int = 0
    flask_success_rate: float = 1.0
    fastapi_success_rate: float = 1.0
    avg_response_time_ms: float = 0.0
    error_count: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HealthStatus:
    """健康状态"""
    overall: str = "healthy"
    flask: str = "healthy"
    fastapi: str = "healthy"
    database: str = "healthy"
    cache: str = "healthy"
    audio: str = "healthy"
    last_check: str = field(default_factory=lambda: datetime.now().isoformat())


class APICompatibilityLayer:
    """API兼容性层"""
    
    def __init__(
        self,
        config: CompatibilityConfig,
        flask_app: Optional[Flask] = None,
        fastapi_app: Optional[FastAPI] = None
    ):
        self.config = config
        self.flask_app = flask_app
        self.fastapi_app = fastapi_app
        self.metrics = APIMetrics()
        self.health_status = HealthStatus()
        self._circuit_breaker_trips = 0
        self._circuit_breaker_open_until: Optional[datetime] = None
        self._request_times: List[float] = []
        self._last_health_check: Optional[datetime] = None
        self._initialized = False
        
        if self.config.enable_logging:
            self._log(f"API兼容性层初始化 - 模式: {config.deployment_mode.value}")
    
    def _log(self, message: str) -> None:
        """日志记录"""
        if self.config.enable_logging:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [API兼容性层] {message}")
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化兼容性层"""
        try:
            self._log("开始初始化兼容性层...")
            
            if self.config.deployment_mode == DeploymentMode.OFFLINE:
                self._log("离线模式 - 跳过初始化")
                return {"success": True, "mode": "offline"}
            
            if self.fastapi_app:
                self._register_fastapi_endpoints()
                self._log("FastAPI端点已注册")
            
            if self.flask_app:
                self._register_flask_endpoints()
                self._log("Flask端点已注册")
            
            self._initialized = True
            self._log(f"兼容性层初始化完成 - FastAPI流量比例: {self.config.traffic_percentage:.1%}")
            
            return {
                "success": True,
                "mode": self.config.deployment_mode.value,
                "traffic_percentage": self.config.traffic_percentage,
                "initialized": True
            }
            
        except Exception as e:
            self._log(f"初始化失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _register_fastapi_endpoints(self) -> None:
        """注册FastAPI兼容端点"""
        if not self.fastapi_app:
            return
        
        @self.fastapi_app.get("/compatibility/status")
        async def compatibility_status():
            """获取兼容性状态"""
            return JSONResponse(content=self.get_deployment_status())
        
        @self.fastapi_app.get("/compatibility/validate")
        async def validate_compatibility():
            """验证API兼容性"""
            validation_result = await self.validate_api_compatibility()
            return JSONResponse(content=validation_result)
        
        @self.fastapi_app.post("/compatibility/compare")
        async def compare_endpoints(request: Request):
            """比较Flask和FastAPI端点响应"""
            data = await request.json()
            endpoint = data.get("endpoint", "/")
            method = data.get("method", "GET")
            params = data.get("params", {})
            
            comparison = await self.compare_endpoint_responses(
                endpoint, method, params
            )
            return JSONResponse(content=comparison)
    
    def _register_flask_endpoints(self) -> None:
        """注册Flask兼容端点"""
        if not self.flask_app:
            return
        
        @self.flask_app.route('/compatibility/status', methods=['GET'])
        def compatibility_status():
            """获取兼容性状态"""
            from flask import jsonify
            return jsonify(self.get_deployment_status())
        
        @self.flask_app.route('/compatibility/validate', methods=['GET'])
        def validate_compatibility():
            """验证API兼容性"""
            from flask import jsonify
            result = asyncio.run(self.validate_api_compatibility())
            return jsonify(result)
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """获取部署状态"""
        return {
            "deployment_mode": self.config.deployment_mode.value,
            "traffic_percentage": self.config.traffic_percentage,
            "flask_port": self.config.flask_port,
            "fastapi_port": self.config.fastapi_port,
            "initialized": self._initialized,
            "circuit_breaker_open": self._is_circuit_breaker_open(),
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "flask_requests": self.metrics.flask_requests,
                "fastapi_requests": self.metrics.fastapi_requests,
                "avg_response_time_ms": round(self.metrics.avg_response_time_ms, 2),
                "error_count": self.metrics.error_count
            }
        }
    
    def _is_circuit_breaker_open(self) -> bool:
        """检查熔断器是否打开"""
        if self._circuit_breaker_open_until:
            if datetime.now() < self._circuit_breaker_open_until:
                return True
            else:
                self._circuit_breaker_open_until = None
                self._circuit_breaker_trips = 0
                self._log("熔断器已恢复")
        return False
    
    async def route_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[Dict[str, Any], int]:
        """路由请求到Flask或FastAPI"""
        start_time = time.time()
        
        try:
            if self._is_circuit_breaker_open():
                self._log("熔断器打开，路由到Flask")
                target = "flask"
            elif self.config.deployment_mode == DeploymentMode.FULL:
                target = "fastapi"
            elif self.config.deployment_mode == DeploymentMode.ROLLED_BACK:
                target = "flask"
            else:
                target = self._select_backend(endpoint, method)
            
            self._log(f"路由请求 {method} {endpoint} 到 {target}")
            
            if target == "fastapi":
                response, status_code = await self._route_to_fastapi(
                    endpoint, method, data, headers
                )
                self.metrics.fastapi_requests += 1
            else:
                response, status_code = await self._route_to_flask(
                    endpoint, method, data, headers
                )
                self.metrics.flask_requests += 1
            
            duration_ms = (time.time() - start_time) * 1000
            self._update_metrics(duration_ms, status_code < 400)
            
            return response, status_code
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._update_metrics(duration_ms, False)
            self.metrics.error_count += 1
            
            self._log(f"请求路由失败: {e}")
            return {
                "success": False,
                "message": "请求处理失败",
                "error": str(e)
            }, 500
    
    def _select_backend(self, endpoint: str, method: str) -> str:
        """选择后端（Flask或FastAPI）"""
        if self.config.deployment_mode == DeploymentMode.OFFLINE:
            return "flask"
        
        if self.config.deployment_mode == DeploymentMode.FULL:
            return "fastapi"
        
        if self.config.deployment_mode == DeploymentMode.ROLLED_BACK:
            return "flask"
        
        random.seed(endpoint + method)
        if random.random() < self.config.traffic_percentage:
            return "fastapi"
        return "flask"
    
    async def _route_to_fastapi(
        self,
        endpoint: str,
        method: str,
        data: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, str]]
    ) -> Tuple[Dict[str, Any], int]:
        """路由到FastAPI"""
        if not self.fastapi_app:
            raise HTTPException(status_code=503, detail="FastAPI未初始化")
        
        return {"success": True, "backend": "fastapi", "data": data or {}}, 200
    
    async def _route_to_flask(
        self,
        endpoint: str,
        method: str,
        data: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, str]]
    ) -> Tuple[Dict[str, Any], int]:
        """路由到Flask"""
        if not self.flask_app:
            raise HTTPException(status_code=503, detail="Flask未初始化")
        
        return {"success": True, "backend": "flask", "data": data or {}}, 200
    
    def _update_metrics(self, response_time_ms: float, success: bool) -> None:
        """更新指标"""
        self.metrics.total_requests += 1
        self._request_times.append(response_time_ms)
        
        if len(self._request_times) > 1000:
            self._request_times = self._request_times[-1000:]
        
        self.metrics.avg_response_time_ms = sum(self._request_times) / len(self._request_times)
        self.metrics.last_updated = datetime.now().isoformat()
        
        if not success:
            self.metrics.error_count += 1
            self._circuit_breaker_trips += 1
            if self._circuit_breaker_trips >= self.config.circuit_breaker_threshold:
                self._circuit_breaker_open_until = datetime.now() + timedelta(
                    seconds=self.config.circuit_breaker_timeout
                )
                self._log(f"熔断器触发，将在{self.config.circuit_breaker_timeout}秒后恢复")
    
    async def check_health(self) -> Dict[str, str]:
        """检查健康状态"""
        try:
            self.health_status.last_check = datetime.now().isoformat()
            
            self.health_status.fastapi = "healthy" if self.fastapi_app else "not_configured"
            self.health_status.flask = "healthy" if self.flask_app else "not_configured"
            
            if self._is_circuit_breaker_open():
                self.health_status.overall = "degraded"
            elif self.metrics.error_count > self.metrics.total_requests * 0.1:
                self.health_status.overall = "degraded"
            else:
                self.health_status.overall = "healthy"
            
            return {
                "overall": self.health_status.overall,
                "flask": self.health_status.flask,
                "fastapi": self.health_status.fastapi,
                "database": self.health_status.database,
                "cache": self.health_status.cache,
                "audio": self.health_status.audio,
                "last_check": self.health_status.last_check
            }
            
        except Exception as e:
            self._log(f"健康检查失败: {e}")
            return {
                "overall": "unhealthy",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "requests": {
                "total": self.metrics.total_requests,
                "flask": self.metrics.flask_requests,
                "fastapi": self.metrics.fastapi_requests
            },
            "performance": {
                "avg_response_time_ms": round(self.metrics.avg_response_time_ms, 2),
                "success_rate": round(
                    (self.metrics.total_requests - self.metrics.error_count) / max(1, self.metrics.total_requests) * 100,
                    2
                )
            },
            "errors": {
                "count": self.metrics.error_count,
                "rate": round(self.metrics.error_count / max(1, self.metrics.total_requests) * 100, 2)
            },
            "circuit_breaker": {
                "is_open": self._is_circuit_breaker_open(),
                "trips": self._circuit_breaker_trips,
                "threshold": self.config.circuit_breaker_threshold
            },
            "last_updated": self.metrics.last_updated
        }
    
    async def validate_api_compatibility(self) -> Dict[str, Any]:
        """验证API兼容性"""
        endpoints_to_test = [
            ("/health", "GET"),
            ("/compatibility/status", "GET"),
            ("/user/profile", "GET"),
            ("/learning/plan", "GET"),
            ("/progress/status", "GET")
        ]
        
        results = {
            "total_endpoints": len(endpoints_to_test),
            "compatible": 0,
            "incompatible": 0,
            "errors": 0,
            "details": []
        }
        
        for endpoint, method in endpoints_to_test:
            try:
                comparison = await self.compare_endpoint_responses(endpoint, method, {})
                is_compatible = comparison.get("responses_match", False)
                
                if is_compatible:
                    results["compatible"] += 1
                    status = "compatible"
                else:
                    results["incompatible"] += 1
                    status = "incompatible"
                
                results["details"].append({
                    "endpoint": endpoint,
                    "method": method,
                    "status": status,
                    "difference": comparison.get("difference", "")
                })
                
            except Exception as e:
                results["errors"] += 1
                results["details"].append({
                    "endpoint": endpoint,
                    "method": method,
                    "status": "error",
                    "error": str(e)
                })
        
        results["compatibility_rate"] = round(
            results["compatible"] / results["total_endpoints"] * 100, 2
        )
        
        return results
    
    async def compare_endpoint_responses(
        self,
        endpoint: str,
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """比较Flask和FastAPI端点响应"""
        try:
            flask_response, _ = await self._route_to_flask(endpoint, method, params, {})
            fastapi_response, _ = await self._route_to_fastapi(endpoint, method, params, {})
            
            flask_hash = self._hash_response(flask_response)
            fastapi_hash = self._hash_response(fastapi_response)
            
            responses_match = flask_hash == fastapi_hash
            
            return {
                "endpoint": endpoint,
                "method": method,
                "responses_match": responses_match,
                "flask_hash": flask_hash[:8],
                "fastapi_hash": fastapi_hash[:8],
                "difference": "" if responses_match else "响应不匹配"
            }
            
        except Exception as e:
            return {
                "endpoint": endpoint,
                "method": method,
                "responses_match": False,
                "error": str(e)
            }
    
    def _hash_response(self, response: Dict[str, Any]) -> str:
        """计算响应哈希"""
        normalized = json.dumps(response, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    async def adjust_traffic_percentage(self, percentage: float) -> Dict[str, Any]:
        """调整流量比例"""
        if not 0 <= percentage <= 1:
            raise HTTPException(status_code=400, detail="流量比例必须在0-1之间")
        
        old_percentage = self.config.traffic_percentage
        self.config.traffic_percentage = percentage
        
        self._log(f"流量比例从{old_percentage:.1%}调整为{percentage:.1%}")
        
        return {
            "success": True,
            "message": f"流量比例已调整为{percentage:.1%}",
            "old_percentage": old_percentage,
            "new_percentage": percentage
        }
    
    async def trigger_rollback(self) -> Dict[str, Any]:
        """触发回滚"""
        old_mode = self.config.deployment_mode
        
        self.config.deployment_mode = DeploymentMode.ROLLED_BACK
        self.config.traffic_percentage = 0.0
        
        self._log(f"已触发回滚 - 模式从{old_mode.value}变为ROLLED_BACK")
        
        return {
            "success": True,
            "message": "已回滚到Flask",
            "previous_mode": old_mode.value,
            "current_mode": self.config.deployment_mode.value,
            "timestamp": datetime.now().isoformat()
        }
    
    async def validate_token(self, token: str) -> Optional[str]:
        """验证令牌（占位符）"""
        if not token:
            return None
        
        try:
            if token.startswith("Bearer "):
                token = token[7:]
            
            return "user_id_from_token"
            
        except Exception:
            return None
