#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
双语导师系统 - FastAPI Web应用
Bilingual Tutor System - FastAPI Web Application

Features:
- Flask to FastAPI migration support with compatibility layer
- Async processing and performance optimization
- Graceful deployment with rollback mechanism
- API versioning and standardization
"""

import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bilingual_tutor.storage.database import LearningDatabase
from bilingual_tutor.core.system_integrator import SystemIntegrator
from bilingual_tutor.web.api_compatibility import (
    APICompatibilityLayer,
    CompatibilityConfig,
    DeploymentMode
)

security = HTTPBearer(auto_error=False)

system_integrator: Optional[SystemIntegrator] = None
learning_db: Optional[LearningDatabase] = None
compatibility_layer: Optional[APICompatibilityLayer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global system_integrator, learning_db, compatibility_layer
    
    print("\n" + "=" * 60)
    print("        双语导师系统 FastAPI 服务启动")
    print("        Bilingual Tutor System FastAPI Server")
    print("=" * 60)
    
    try:
        system_integrator = SystemIntegrator()
        learning_db = system_integrator.learning_db
        
        compatibility_config = CompatibilityConfig(
            deployment_mode=DeploymentMode.GRADUAL,
            flask_port=5000,
            fastapi_port=8000,
            traffic_percentage=0.1,
            enable_metrics=True,
            enable_health_check=True
        )
        
        compatibility_layer = APICompatibilityLayer(
            config=compatibility_config,
            flask_app=None,
            fastapi_app=app
        )
        
        await compatibility_layer.initialize()
        
        print("\n📊 数据库状态:")
        print(f"   英语词汇: {learning_db.get_vocabulary_count('english')} 个")
        print(f"   日语词汇: {learning_db.get_vocabulary_count('japanese')} 个")
        
        audio_stats = system_integrator.pronunciation_manager.get_pronunciation_statistics()
        print("🔊 音频系统状态:")
        print(f"   音频文件: {audio_stats.get('summary', {}).get('total_stored_files', 0)} 个")
        
        print("✅ 系统初始化完成")
        print("=" * 60 + "\n")
        
        yield
        
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        raise
    finally:
        print("\n🛑 正在关闭系统...")
        if system_integrator:
            system_integrator.close()
        print("✅ 系统已安全关闭")


app = FastAPI(
    title="双语导师系统 API",
    description="Bilingual Tutor System - Modern Learning Platform API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:3000", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    components: Dict[str, str]


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health check endpoint"""
    if compatibility_layer:
        health_status = await compatibility_layer.check_health()
    else:
        health_status = {
            "overall": "unknown",
            "database": "unknown",
            "cache": "unknown",
            "audio": "unknown"
        }
    
    return HealthResponse(
        status="healthy" if health_status.get("overall") == "healthy" else "degraded",
        version="2.0.0",
        timestamp=datetime.now().isoformat(),
        components=health_status
    )


@app.get("/metrics", tags=["System"])
async def get_metrics():
    """Get system metrics for monitoring"""
    if not compatibility_layer:
        raise HTTPException(status_code=503, detail="Compatibility layer not initialized")
    
    metrics = await compatibility_layer.get_metrics()
    return metrics


@app.get("/deployment/status", tags=["System"])
async def get_deployment_status():
    """Get current deployment status"""
    if not compatibility_layer:
        raise HTTPException(status_code=503, detail="Compatibility layer not initialized")
    
    status = compatibility_layer.get_deployment_status()
    return status


@app.post("/deployment/adjust-traffic", tags=["System"])
async def adjust_traffic(percentage: float = Field(..., ge=0, le=1)):
    """Adjust traffic split between Flask and FastAPI"""
    if not compatibility_layer:
        raise HTTPException(status_code=503, detail="Compatibility layer not initialized")
    
    result = await compatibility_layer.adjust_traffic_percentage(percentage)
    return result


@app.post("/deployment/rollback", tags=["System"])
async def trigger_rollback():
    """Trigger immediate rollback to Flask"""
    if not compatibility_layer:
        raise HTTPException(status_code=503, detail="Compatibility layer not initialized")
    
    result = await compatibility_layer.trigger_rollback()
    return result


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": f"HTTP_{exc.status_code}"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "error_code": "INTERNAL_ERROR",
            "details": {"type": type(exc).__name__}
        }
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Get current user from credentials (placeholder)"""
    if credentials and compatibility_layer:
        user_id = await compatibility_layer.validate_token(credentials.credentials)
        return user_id
    return None


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("        双语导师系统 FastAPI 服务")
    print("        Bilingual Tutor System FastAPI Server")
    print("=" * 60)
    print("\n  访问地址:")
    print("  - API文档: http://localhost:8000/docs")
    print("  - ReDoc文档: http://localhost:8000/redoc")
    print("  - 健康检查: http://localhost:8000/health")
    print("\n  按 Ctrl+C 停止服务器")
    print("=" * 60 + "\n")
    
    uvicorn.run(
        "bilingual_tutor.web.fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
