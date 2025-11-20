"""
WPH Pharmacy SMART - System Monitoring Module
Provides health checks, system metrics, and alerting capabilities
"""
import os
import sys
import time
import platform
from datetime import datetime
from typing import Dict, Any, Optional

# Try importing psutil (optional dependency)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not installed. Install via: pip install psutil")

# Import db connection
try:
    from db import get_conn
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class SystemMonitor:
    """Monitor system health and performance"""
    
    def __init__(self):
        self.start_time = time.time()
        
    def get_uptime_seconds(self) -> float:
        """Get service uptime in seconds"""
        return time.time() - self.start_time
    
    def check_database(self) -> Dict[str, Any]:
        """Check PostgreSQL database connectivity and basic stats"""
        if not DB_AVAILABLE:
            return {"status": "unavailable", "error": "db module not imported"}
        
        try:
            conn = get_conn()
            cursor = conn.cursor()
            
            # Test query
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            # Get database size
            db_name = os.getenv("WPH_DB_NAME", "wph_ai")
            cursor.execute(f"SELECT pg_database_size('{db_name}');")
            size_bytes = cursor.fetchone()[0]
            size_mb = round(size_bytes / (1024 * 1024), 2)
            
            # Check connection count
            cursor.execute("SELECT count(*) FROM pg_stat_activity;")
            connections = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return {
                "status": "healthy",
                "version": version.split(",")[0],
                "size_mb": size_mb,
                "connections": connections
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage statistics"""
        if not PSUTIL_AVAILABLE:
            return {"status": "unavailable", "error": "psutil not installed"}
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            return {
                "percent": round(cpu_percent, 1),
                "count": cpu_count,
                "status": "healthy" if cpu_percent < 80 else "warning"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        if not PSUTIL_AVAILABLE:
            return {"status": "unavailable", "error": "psutil not installed"}
        
        try:
            mem = psutil.virtual_memory()
            
            return {
                "total_mb": round(mem.total / (1024 * 1024), 0),
                "available_mb": round(mem.available / (1024 * 1024), 0),
                "used_mb": round(mem.used / (1024 * 1024), 0),
                "percent": round(mem.percent, 1),
                "status": "healthy" if mem.percent < 85 else "warning"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage for main drive"""
        if not PSUTIL_AVAILABLE:
            return {"status": "unavailable", "error": "psutil not installed"}
        
        try:
            disk = psutil.disk_usage('C:\\')
            
            return {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "percent": round(disk.percent, 1),
                "status": "healthy" if disk.percent < 80 else "warning"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_full_health(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        db = self.check_database()
        cpu = self.get_cpu_usage()
        memory = self.get_memory_usage()
        disk = self.get_disk_usage()
        
        # Overall status
        all_healthy = all([
            db.get("status") == "healthy",
            cpu.get("status") in ["healthy", "warning", "unavailable"],
            memory.get("status") in ["healthy", "warning", "unavailable"],
            disk.get("status") in ["healthy", "warning", "unavailable"]
        ])
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy" if all_healthy else "degraded",
            "uptime_seconds": round(self.get_uptime_seconds(), 0),
            "system": {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": platform.python_version()
            },
            "database": db,
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "features": {
                "psutil": PSUTIL_AVAILABLE,
                "db": DB_AVAILABLE
            }
        }
    
    def check_critical_issues(self) -> Optional[list]:
        """Check for critical issues that require immediate attention"""
        health = self.get_full_health()
        issues = []
        
        # Database down
        if health["database"].get("status") == "unhealthy":
            issues.append({
                "severity": "critical",
                "component": "database",
                "message": f"Database unhealthy: {health['database'].get('error', 'Unknown')}"
            })
        
        # High CPU
        if health["cpu"].get("percent", 0) > 90:
            issues.append({
                "severity": "warning",
                "component": "cpu",
                "message": f"CPU usage critical: {health['cpu']['percent']}%"
            })
        
        # High memory
        if health["memory"].get("percent", 0) > 90:
            issues.append({
                "severity": "warning",
                "component": "memory",
                "message": f"Memory usage critical: {health['memory']['percent']}%"
            })
        
        # High disk
        if health["disk"].get("percent", 0) > 85:
            issues.append({
                "severity": "warning",
                "component": "disk",
                "message": f"Disk usage high: {health['disk']['percent']}%"
            })
        
        return issues if issues else None


# Global monitor instance
monitor = SystemMonitor()


def send_telegram_alert(message: str, severity: str = "warning"):
    """Send alert to Telegram bot (if configured)"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print(f"[ALERT] {severity.upper()}: {message}")
        return False
    
    try:
        import requests
        
        emoji = "🚨" if severity == "critical" else "⚠️"
        text = f"{emoji} **WPH Pharmacy Alert**\n\n{message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10)
        
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
        return False


if __name__ == "__main__":
    # Test monitoring
    mon = SystemMonitor()
    health = mon.get_full_health()
    
    print("=== WPH System Health Check ===")
    print(f"Overall Status: {health['overall_status'].upper()}")
    print(f"Uptime: {health['uptime_seconds']}s")
    print(f"\nDatabase: {health['database']['status']}")
    print(f"CPU: {health['cpu'].get('percent', 'N/A')}")
    print(f"Memory: {health['memory'].get('percent', 'N/A')}")
    print(f"Disk: {health['disk'].get('percent', 'N/A')}")
    
    issues = mon.check_critical_issues()
    if issues:
        print(f"\n⚠️  Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - [{issue['severity']}] {issue['component']}: {issue['message']}")
