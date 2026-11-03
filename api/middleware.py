"""Application middleware configuration."""
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.common.logger import get_logger

log = get_logger("api")


class SecureContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Inject standard security headers
        response.headers["X-Frame-Options"] = "DENY"  # Prevents Clickjacking
        response.headers["X-Content-Type-Options"] = "nosniff"  # Prevents MIME-sniffing exploits
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"  # Forces HTTPS (HSTS)
        
        # Inject telemetry headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{time.perf_counter() - started:.4f}"

        log.info("%s %s -> %s [%s]", request.method, request.url.path,
                 response.status_code, request_id)
        return response


def add_middleware(application: FastAPI) -> None:
    """Register middleware shared by every API route."""
    
    # Prevent Host Header Injection / Poisoning
    # Update allowed_hosts with your actual domains in production
    application.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["localhost", "127.0.0.1"]
    )
    
    # # Restrict Cross-Origin Resource Sharing (CORS)
    # # Never leave allow_origins=["*"] in production if your API handles private data
    # application.add_middleware(
    #     CORSMiddleware,
    #     allow_origins=["https://yourfrontend.com"], 
    #     allow_credentials=True,
    #     allow_methods=["GET", "POST", "PUT", "DELETE"],
    #     allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    # )
    
    # Enforce global SSL/TLS redirection
    # ONLY uncomment this if your Python app terminates SSL directly.
    # If you use Nginx, Cloudflare, or AWS ALB for SSL termination, leave it commented.
    # application.add_middleware(HTTPSRedirectMiddleware)

    # Load your custom logging and security header middleware last
    application.add_middleware(SecureContextMiddleware)
