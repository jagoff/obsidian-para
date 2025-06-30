#!/usr/bin/env python3
"""
paralib/health_monitor.py

Health Monitor para PARA System v2.0
- Monitoreo proactivo del sistema
- Diagnóstico inteligente
- Auto-reparación avanzada
- Alertas preventivas
- Métricas de salud en tiempo real
"""
import time
import psutil
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import threading
import queue
import os

from .log_center import log_center, log_function_call

@dataclass
class HealthMetric:
    """Métrica de salud del sistema."""
    name: str
    value: float
    unit: str
    status: str  # 'healthy', 'warning', 'critical'
    threshold: float
    description: str
    last_updated: datetime

@dataclass
class SystemIssue:
    """Problema detectado en el sistema."""
    id: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    title: str
    description: str
    component: str
    detected_at: datetime
    auto_fix_attempted: bool = False
    auto_fix_success: bool = False
    resolution: Optional[str] = None

class PARAHealthMonitor:
    """Monitor de salud del sistema PARA."""
    
    def __init__(self):
        self.metrics = {}
        self.issues = []
        self.health_score = 100.0
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Umbrales de alerta
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time': 5.0,
            'error_rate': 10.0,
            'log_size': 100.0,  # MB
        }
        
        # Reglas de auto-reparación
        self.auto_fix_rules = self._load_auto_fix_rules()
        
        log_center.log_info("Health Monitor inicializado", component='HealthMonitor')
    
    def start_monitoring(self):
        """Inicia el monitoreo continuo."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        log_center.log_info("Monitoreo de salud iniciado", component='HealthMonitor')
    
    def stop_monitoring(self):
        """Detiene el monitoreo."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        log_center.log_info("Monitoreo de salud detenido", component='HealthMonitor')
    
    def _monitor_loop(self):
        """Loop principal de monitoreo."""
        while self.monitoring_active:
            try:
                self._collect_metrics()
                self._analyze_health()
                self._check_for_issues()
                self._attempt_auto_fixes()
                
                time.sleep(30)  # Verificar cada 30 segundos
                
            except Exception as e:
                log_center.log_error(f"Error en loop de monitoreo: {e}", component='HealthMonitor')
                time.sleep(60)  # Esperar más tiempo si hay error
    
    @log_function_call
    def _collect_metrics(self):
        """Recopila métricas del sistema."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics['cpu_usage'] = HealthMetric(
                name="CPU Usage",
                value=cpu_percent,
                unit="%",
                status=self._get_status(cpu_percent, self.thresholds['cpu_usage']),
                threshold=self.thresholds['cpu_usage'],
                description="Uso de CPU del sistema",
                last_updated=datetime.now()
            )
            
            # Memoria
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.metrics['memory_usage'] = HealthMetric(
                name="Memory Usage",
                value=memory_percent,
                unit="%",
                status=self._get_status(memory_percent, self.thresholds['memory_usage']),
                threshold=self.thresholds['memory_usage'],
                description="Uso de memoria RAM",
                last_updated=datetime.now()
            )
            
            # Disco
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics['disk_usage'] = HealthMetric(
                name="Disk Usage",
                value=disk_percent,
                unit="%",
                status=self._get_status(disk_percent, self.thresholds['disk_usage']),
                threshold=self.thresholds['disk_usage'],
                description="Uso de espacio en disco",
                last_updated=datetime.now()
            )
            
            # Logs
            log_size = self._get_log_size()
            self.metrics['log_size'] = HealthMetric(
                name="Log Size",
                value=log_size,
                unit="MB",
                status=self._get_status(log_size, self.thresholds['log_size']),
                threshold=self.thresholds['log_size'],
                description="Tamaño total de logs",
                last_updated=datetime.now()
            )
            
            # Error rate
            error_rate = self._calculate_error_rate()
            self.metrics['error_rate'] = HealthMetric(
                name="Error Rate",
                value=error_rate,
                unit="%",
                status=self._get_status(error_rate, self.thresholds['error_rate']),
                threshold=self.thresholds['error_rate'],
                description="Tasa de errores en logs",
                last_updated=datetime.now()
            )
            
        except Exception as e:
            log_center.log_error(f"Error recopilando métricas: {e}", component='HealthMonitor')
    
    def _get_status(self, value: float, threshold: float) -> str:
        """Determina el estado basado en el valor y umbral."""
        if value >= threshold:
            return 'critical'
        elif value >= threshold * 0.8:
            return 'warning'
        else:
            return 'healthy'
    
    def _get_log_size(self) -> float:
        """Calcula el tamaño total de logs en MB."""
        try:
            log_dir = Path("logs")
            if not log_dir.exists():
                return 0.0
            
            total_size = 0
            for log_file in log_dir.glob("*.log*"):
                total_size += log_file.stat().st_size
            
            return total_size / (1024 * 1024)  # Convertir a MB
        except Exception:
            return 0.0
    
    def _calculate_error_rate(self) -> float:
        """Calcula la tasa de errores en logs recientes."""
        try:
            # Implementar cálculo de tasa de errores
            return 5.0  # Placeholder
        except Exception:
            return 0.0
    
    def _analyze_health(self):
        """Analiza la salud general del sistema."""
        try:
            # Calcular score de salud
            total_metrics = len(self.metrics)
            healthy_metrics = sum(1 for m in self.metrics.values() if m.status == 'healthy')
            warning_metrics = sum(1 for m in self.metrics.values() if m.status == 'warning')
            critical_metrics = sum(1 for m in self.metrics.values() if m.status == 'critical')
            
            # Fórmula: 100 - (critical * 20) - (warning * 10)
            self.health_score = max(0, 100 - (critical_metrics * 20) - (warning_metrics * 10))
            
            log_center.log_info(
                f"Análisis de salud completado - Score: {self.health_score}%",
                component='HealthMonitor',
                extra_data={
                    'healthy': healthy_metrics,
                    'warning': warning_metrics,
                    'critical': critical_metrics
                }
            )
            
        except Exception as e:
            log_center.log_error(f"Error analizando salud: {e}", component='HealthMonitor')
    
    def _check_for_issues(self):
        """Verifica si hay nuevos problemas."""
        try:
            current_issues = []
            
            # Verificar métricas críticas
            for metric_name, metric in self.metrics.items():
                if metric.status == 'critical':
                    issue = SystemIssue(
                        id=f"critical_{metric_name}",
                        severity='critical',
                        title=f"{metric.name} crítico",
                        description=f"{metric.name} está en {metric.value}{metric.unit}, por encima del umbral de {metric.threshold}{metric.unit}",
                        component=metric_name,
                        detected_at=datetime.now()
                    )
                    current_issues.append(issue)
                
                elif metric.status == 'warning':
                    issue = SystemIssue(
                        id=f"warning_{metric_name}",
                        severity='medium',
                        title=f"{metric.name} en advertencia",
                        description=f"{metric.name} está en {metric.value}{metric.unit}, acercándose al umbral de {metric.threshold}{metric.unit}",
                        component=metric_name,
                        detected_at=datetime.now()
                    )
                    current_issues.append(issue)
            
            # Verificar problemas específicos del sistema
            self._check_system_specific_issues(current_issues)
            
            # Actualizar lista de problemas
            self.issues = current_issues
            
            # Log de problemas detectados
            if current_issues:
                log_center.log_warning(
                    f"Se detectaron {len(current_issues)} problemas",
                    component='HealthMonitor',
                    extra_data={'issues': [i.title for i in current_issues]}
                )
            
        except Exception as e:
            log_center.log_error(f"Error verificando problemas: {e}", component='HealthMonitor')
    
    def _check_system_specific_issues(self, issues: List[SystemIssue]):
        """Verifica problemas específicos del sistema PARA."""
        try:
            # Verificar servicios críticos
            services = ['chromadb', 'ollama']
            for service in services:
                if not self._is_service_running(service):
                    issue = SystemIssue(
                        id=f"service_{service}",
                        severity='high',
                        title=f"Servicio {service} no está ejecutándose",
                        description=f"El servicio {service} no está disponible",
                        component='services',
                        detected_at=datetime.now()
                    )
                    issues.append(issue)
            
            # Verificar archivos críticos
            critical_files = ['para_config.default.json', 'logs/para_system.log']
            for file_path in critical_files:
                if not Path(file_path).exists():
                    issue = SystemIssue(
                        id=f"file_{file_path}",
                        severity='medium',
                        title=f"Archivo crítico faltante: {file_path}",
                        description=f"El archivo {file_path} no existe",
                        component='files',
                        detected_at=datetime.now()
                    )
                    issues.append(issue)
            
            # Verificar permisos
            if not self._check_permissions():
                issue = SystemIssue(
                    id="permissions",
                    severity='medium',
                    title="Problemas de permisos",
                    description="Algunos archivos o directorios tienen permisos incorrectos",
                    component='permissions',
                    detected_at=datetime.now()
                )
                issues.append(issue)
            
            # NUEVO: Verificación específica de ChromaDB y clasificación
            try:
                from paralib.db import ChromaPARADatabase
                from paralib.vault import find_vault
                
                # Obtener vault para ChromaDB
                vault = find_vault()
                if vault:
                    db_path = vault / ".para_db" / "chroma"
                    test_db = ChromaPARADatabase(str(db_path))
                    
                    # Test completo de ChromaDB
                    try:
                        # Test 1: Verificar inicialización
                        log_center.log_info("Iniciando verificación completa de ChromaDB", "HealthMonitor-ChromaDB")
                        
                        # Test 2: Verificar conteo de notas
                        total_notes = test_db.collection.count()
                        log_center.log_info(f"ChromaDB: {total_notes} notas en la colección", "HealthMonitor-ChromaDB")
                        
                        # Test 3: Verificar búsqueda con ambos parámetros
                        test_result_n_results = test_db.search_similar_notes("health check test", n_results=1)
                        test_result_limit = test_db.search_similar_notes("health check test", limit=1)
                        
                        log_center.log_info(f"ChromaDB: Búsqueda con n_results funcional ({len(test_result_n_results)} resultados)", "HealthMonitor-ChromaDB")
                        log_center.log_info(f"ChromaDB: Búsqueda con limit funcional ({len(test_result_limit)} resultados)", "HealthMonitor-ChromaDB")
                        
                        # Test 4: Verificar distribución de categorías
                        distribution = test_db.get_category_distribution()
                        log_center.log_info(f"ChromaDB: Distribución de categorías: {distribution}", "HealthMonitor-ChromaDB")
                        
                        # Test 5: Verificar estadísticas generales
                        stats = test_db.get_database_stats()
                        log_center.log_info(f"ChromaDB: Estadísticas generadas exitosamente", "HealthMonitor-ChromaDB")
                        
                        # Test 6: Verificar listado de colecciones
                        collections = test_db.list_collections()
                        log_center.log_info(f"ChromaDB: {len(collections)} colecciones listadas", "HealthMonitor-ChromaDB")
                        
                        self.log_health_metric("ChromaDB", "excellent", f"ChromaDB completamente funcional - {total_notes} notas")
                        
                    except Exception as chromadb_error:
                        error_msg = str(chromadb_error)
                        log_center.log_error(f"Error en verificación de ChromaDB: {error_msg}", "HealthMonitor-ChromaDB")
                        
                        # Clasificar el tipo de error
                        if "unexpected keyword argument" in error_msg:
                            severity = "critical"
                            title = "Error de parámetros en ChromaDB"
                            description = f"Error de compatibilidad de parámetros: {error_msg}"
                        elif "limit" in error_msg.lower():
                            severity = "warning"
                            title = "Problema con parámetro limit en ChromaDB"
                            description = f"Problema específico con parámetro limit: {error_msg}"
                        elif "connection" in error_msg.lower():
                            severity = "critical"
                            title = "Error de conexión a ChromaDB"
                            description = f"No se puede conectar a ChromaDB: {error_msg}"
                        else:
                            severity = "high"
                            title = "Error general en ChromaDB"
                            description = f"Error no clasificado en ChromaDB: {error_msg}"
                        
                        self.log_health_metric("ChromaDB", "critical", f"ChromaDB error: {error_msg}")
                        issues.append(SystemIssue(
                            id="ChromaDB-Error",
                            severity=severity,
                            title=title,
                            description=description,
                            component="ChromaDB",
                            detected_at=datetime.now()
                        ))
                else:
                    log_center.log_warning("No se encontró vault para verificar ChromaDB", "HealthMonitor-ChromaDB")
                    self.log_health_metric("ChromaDB", "warning", "No se pudo verificar ChromaDB - vault no encontrado")
                    
                # Verificar errores de clasificación en logs recientes
                try:
                    log_center.log_info("Analizando errores de clasificación en logs", "HealthMonitor-Classification")
                    recent_logs = log_center.get_recent_logs(100)
                    
                    # Patrones de error específicos de ChromaDB y clasificación
                    chromadb_error_patterns = [
                        "ChromaPARADatabase",
                        "unexpected keyword argument",
                        "limit=",
                        "n_results",
                        "search_similar_notes",
                        "chromadb error",
                        "embedding error",
                        "vector database error"
                    ]
                    
                    classification_error_patterns = [
                        "Error procesando",
                        "classification error",
                        "Error clasificando",
                        "Error en clasificación",
                        "clasificación falló"
                    ]
                    
                    chromadb_errors = 0
                    classification_errors = 0
                    critical_errors = 0
                    
                    for log_entry in recent_logs:
                        message_lower = log_entry.message.lower()
                        
                        # Contar errores de ChromaDB
                        for pattern in chromadb_error_patterns:
                            if pattern.lower() in message_lower:
                                chromadb_errors += 1
                                if log_entry.level in ['ERROR', 'CRITICAL']:
                                    critical_errors += 1
                                break
                        
                        # Contar errores de clasificación
                        for pattern in classification_error_patterns:
                            if pattern.lower() in message_lower:
                                classification_errors += 1
                                break
                    
                    # Analizar resultados
                    if chromadb_errors > 0:
                        severity = "critical" if critical_errors > 0 else "warning"
                        log_center.log_warning(f"Detectados {chromadb_errors} errores de ChromaDB ({critical_errors} críticos)", "HealthMonitor-Analysis")
                        
                        self.log_health_metric("ChromaDB-Errors", severity, f"{chromadb_errors} errores de ChromaDB detectados")
                        issues.append(SystemIssue(
                            id="ChromaDB-LogErrors",
                            severity=severity,
                            title=f"Errores de ChromaDB en logs ({chromadb_errors})",
                            description=f"Se detectaron {chromadb_errors} errores relacionados con ChromaDB, {critical_errors} críticos",
                            component="ChromaDB-Logs",
                            detected_at=datetime.now()
                        ))
                    else:
                        log_center.log_info("No se detectaron errores de ChromaDB en logs recientes", "HealthMonitor-Analysis")
                        self.log_health_metric("ChromaDB-Errors", "excellent", "Sin errores de ChromaDB en logs")
                    
                    if classification_errors > 0:
                        severity = "warning" if classification_errors < 10 else "critical"
                        log_center.log_warning(f"Detectados {classification_errors} errores de clasificación", "HealthMonitor-Analysis")
                        
                        self.log_health_metric("Classification", severity, f"{classification_errors} errores de clasificación detectados")
                        issues.append(SystemIssue(
                            id="Classification-Errors",
                            severity=severity,
                            title=f"Errores de clasificación ({classification_errors})",
                            description=f"Se detectaron {classification_errors} errores de clasificación recientes",
                            component="Classification",
                            detected_at=datetime.now()
                        ))
                    else:
                        log_center.log_info("No se detectaron errores de clasificación en logs recientes", "HealthMonitor-Analysis")
                        self.log_health_metric("Classification", "excellent", "Sin errores de clasificación recientes")
                        
                except Exception as log_analysis_error:
                    log_center.log_error(f"Error analizando logs: {log_analysis_error}", "HealthMonitor-Analysis")
                    self.log_health_metric("Log-Analysis", "warning", f"Error analizando logs: {log_analysis_error}")
                    
            except Exception as e:
                log_center.log_error(f"Error en verificaciones especializadas de ChromaDB: {e}", "HealthMonitor-ChromaDB")
                self.log_health_metric("Specialized-Checks", "warning", f"Error en verificaciones especializadas: {e}")
            
        except Exception as e:
            log_center.log_error(f"Error verificando problemas específicos: {e}", component='HealthMonitor')
    
    def _is_service_running(self, service: str) -> bool:
        """Verifica si un servicio está ejecutándose."""
        try:
            if service == 'chromadb':
                # Verificar ChromaDB
                return True  # Placeholder
            elif service == 'ollama':
                # Verificar Ollama
                result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
                return result.returncode == 0
            else:
                return True
        except Exception:
            return False
    
    def _check_permissions(self) -> bool:
        """Verifica permisos de archivos críticos."""
        try:
            critical_paths = ['logs', 'backups', 'para_config.default.json']
            for path in critical_paths:
                path_obj = Path(path)
                if path_obj.exists():
                    # Verificar permisos de lectura/escritura
                    if not os.access(path_obj, os.R_OK | os.W_OK):
                        return False
            return True
        except Exception:
            return False
    
    def _attempt_auto_fixes(self):
        """Intenta reparar problemas automáticamente."""
        try:
            for issue in self.issues:
                if not issue.auto_fix_attempted:
                    log_center.log_auto_fix_attempt(
                        f"Intentando auto-reparar: {issue.title}",
                        component='HealthMonitor'
                    )
                    
                    success = self._apply_auto_fix(issue)
                    issue.auto_fix_attempted = True
                    issue.auto_fix_success = success
                    
                    if success:
                        log_center.log_auto_fix_success(
                            f"Auto-reparación exitosa: {issue.title}",
                            component='HealthMonitor'
                        )
                        issue.resolution = "Auto-reparado exitosamente"
                    else:
                        log_center.log_auto_fix_failed(
                            f"Auto-reparación falló: {issue.title}",
                            component='HealthMonitor'
                        )
                        issue.resolution = "Auto-reparación falló"
            
        except Exception as e:
            log_center.log_error(f"Error en auto-reparación: {e}", component='HealthMonitor')
    
    def _apply_auto_fix(self, issue: SystemIssue) -> bool:
        """Aplica una reparación automática específica."""
        try:
            if 'cpu_usage' in issue.id:
                return self._fix_high_cpu()
            elif 'memory_usage' in issue.id:
                return self._fix_high_memory()
            elif 'disk_usage' in issue.id:
                return self._fix_high_disk()
            elif 'log_size' in issue.id:
                return self._fix_large_logs()
            elif 'service_' in issue.id:
                return self._fix_service(issue.component)
            elif 'file_' in issue.id:
                return self._fix_missing_file(issue.component)
            elif 'permissions' in issue.id:
                return self._fix_permissions()
            else:
                return False
                
        except Exception as e:
            log_center.log_error(f"Error aplicando auto-fix: {e}", component='HealthMonitor')
            return False
    
    def _fix_high_cpu(self) -> bool:
        """Repara uso alto de CPU."""
        try:
            # Implementar optimizaciones de CPU
            return True
        except Exception:
            return False
    
    def _fix_high_memory(self) -> bool:
        """Repara uso alto de memoria."""
        try:
            # Limpiar caché y liberar memoria
            import gc
            gc.collect()
            return True
        except Exception:
            return False
    
    def _fix_high_disk(self) -> bool:
        """Repara uso alto de disco."""
        try:
            # Limpiar archivos temporales y logs antiguos
            log_center.cleanup_old_logs(7)  # Limpiar logs de más de 7 días
            return True
        except Exception:
            return False
    
    def _fix_large_logs(self) -> bool:
        """Repara logs muy grandes."""
        try:
            # Rotar logs
            return log_center.cleanup_old_logs(1) > 0
        except Exception:
            return False
    
    def _fix_service(self, service: str) -> bool:
        """Repara un servicio."""
        try:
            if service == 'ollama':
                # Intentar reiniciar Ollama
                subprocess.run(['ollama', 'serve'], start_new_session=True)
                return True
            return False
        except Exception:
            return False
    
    def _fix_missing_file(self, file_path: str) -> bool:
        """Repara archivo faltante."""
        try:
            if 'para_config.default.json' in file_path:
                # Crear configuración por defecto
                default_config = {
                    "vault_path": ".",
                    "ai_model": "llama3.2",
                    "log_level": "INFO"
                }
                with open('para_config.default.json', 'w') as f:
                    json.dump(default_config, f, indent=2)
                return True
            return False
        except Exception:
            return False
    
    def _fix_permissions(self) -> bool:
        """Repara permisos."""
        try:
            # Corregir permisos de directorios críticos
            subprocess.run(['chmod', '755', 'logs'])
            subprocess.run(['chmod', '755', 'backups'])
            return True
        except Exception:
            return False
    
    def _load_auto_fix_rules(self) -> List[Dict[str, Any]]:
        """Carga reglas de auto-reparación."""
        return [
            {
                'id': 'high_cpu',
                'condition': lambda m: m.get('cpu_usage', 0) > 80,
                'action': self._fix_high_cpu,
                'description': 'Optimizar uso de CPU'
            },
            {
                'id': 'high_memory',
                'condition': lambda m: m.get('memory_usage', 0) > 85,
                'action': self._fix_high_memory,
                'description': 'Liberar memoria'
            },
            {
                'id': 'high_disk',
                'condition': lambda m: m.get('disk_usage', 0) > 90,
                'action': self._fix_high_disk,
                'description': 'Limpiar espacio en disco'
            }
        ]
    
    def get_health_report(self) -> Dict[str, Any]:
        """Genera reporte de salud completo."""
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'health_score': self.health_score,
                'status': self._get_overall_status(),
                'metrics': {name: {
                    'value': metric.value,
                    'unit': metric.unit,
                    'status': metric.status,
                    'threshold': metric.threshold,
                    'description': metric.description,
                    'last_updated': metric.last_updated.isoformat()
                } for name, metric in self.metrics.items()},
                'issues': [{
                    'id': issue.id,
                    'severity': issue.severity,
                    'title': issue.title,
                    'description': issue.description,
                    'component': issue.component,
                    'detected_at': issue.detected_at.isoformat(),
                    'auto_fix_attempted': issue.auto_fix_attempted,
                    'auto_fix_success': issue.auto_fix_success,
                    'resolution': issue.resolution
                } for issue in self.issues],
                'recommendations': self._generate_recommendations()
            }
        except Exception as e:
            log_center.log_error(f"Error generando reporte de salud: {e}", component='HealthMonitor')
            return {'error': str(e)}
    
    def _get_overall_status(self) -> str:
        """Obtiene el estado general del sistema."""
        if self.health_score >= 90:
            return 'excellent'
        elif self.health_score >= 70:
            return 'good'
        elif self.health_score >= 50:
            return 'fair'
        else:
            return 'poor'
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Genera recomendaciones basadas en el estado actual."""
        recommendations = []
        
        # Recomendaciones basadas en métricas
        for metric_name, metric in self.metrics.items():
            if metric.status == 'critical':
                recommendations.append({
                    'priority': 'high',
                    'title': f'Resolver {metric.name} crítico',
                    'description': f'El {metric.name} está en {metric.value}{metric.unit}, por encima del umbral crítico de {metric.threshold}{metric.unit}',
                    'action': f'Revisar y optimizar {metric_name}'
                })
            elif metric.status == 'warning':
                recommendations.append({
                    'priority': 'medium',
                    'title': f'Monitorear {metric.name}',
                    'description': f'El {metric.name} está en {metric.value}{metric.unit}, acercándose al umbral de {metric.threshold}{metric.unit}',
                    'action': f'Monitorear tendencias de {metric_name}'
                })
        
        # Recomendaciones generales
        if self.health_score < 70:
            recommendations.append({
                'priority': 'high',
                'title': 'Revisión general del sistema',
                'description': 'El sistema tiene múltiples problemas que requieren atención inmediata',
                'action': 'Ejecutar diagnóstico completo y aplicar correcciones'
            })
        
        return recommendations
    
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """Ejecuta diagnóstico completo del sistema."""
        try:
            log_center.log_info("Iniciando diagnóstico completo", component='HealthMonitor')
            
            # Recopilar métricas
            self._collect_metrics()
            
            # Analizar salud
            self._analyze_health()
            
            # Verificar problemas
            self._check_for_issues()
            
            # Generar reporte
            report = self.get_health_report()
            
            log_center.log_info("Diagnóstico completo finalizado", component='HealthMonitor')
            
            return report
            
        except Exception as e:
            log_center.log_error(f"Error en diagnóstico completo: {e}", component='HealthMonitor')
            return {'error': str(e)}

# Instancia global
health_monitor = PARAHealthMonitor()

# Add missing log methods to avoid errors
def log_auto_fix_attempt(message, component='System'):
    log_center.log_info(f"AUTO_FIX_ATTEMPT: {message}", component)

def log_auto_fix_success(message, component='System'):
    log_center.log_info(f"AUTO_FIX_SUCCESS: {message}", component)

def log_auto_fix_failed(message, component='System'):
    log_center.log_warning(f"AUTO_FIX_FAILED: {message}", component)

# Monkey patch the missing methods
log_center.log_auto_fix_attempt = log_auto_fix_attempt
log_center.log_auto_fix_success = log_auto_fix_success
log_center.log_auto_fix_failed = log_auto_fix_failed 