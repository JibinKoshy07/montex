import logging
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler
import models
import ssh_client
import telegram_bot
import encryptor
import config

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Background metrics collector"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.running = False
        self.previous_online_status = {}
    
    def collect_metrics_for_server(self, server):
        """Collect metrics for a single server"""
        server_id = server['id']
        
        # Decrypt credentials
        password = None
        key = None
        
        if server['auth_type'] == 'password' and server.get('password_encrypted'):
            password = encryptor.decrypt(server['password_encrypted'])
        elif server['auth_type'] == 'key' and server.get('key_encrypted'):
            key = encryptor.decrypt(server['key_encrypted'])
        
        # Get metrics
        result = ssh_client.get_system_metrics(
            hostname=server['hostname'],
            port=server['port'],
            username=server['username'],
            auth_type=server['auth_type'],
            password=password,
            key=key
        )
        
        if result['success']:
            # Get thresholds
            thresholds = self.get_thresholds()
            
            # Save metrics
            models.save_metrics(
                server_id=server_id,
                cpu_percent=result['cpu_percent'],
                memory_percent=result['memory_percent'],
                memory_used=result['memory_used'],
                memory_total=result['memory_total'],
                storage_percent=result['storage_percent'],
                storage_used=result['storage_used'],
                storage_total=result['storage_total'],
                is_online=1
            )
            
            # Check thresholds
            self.check_thresholds(server, result, thresholds)
            
            # Check if server came back online
            if server_id in self.previous_online_status and not self.previous_online_status[server_id]:
                self.notify_server_online(server)
            
            self.previous_online_status[server_id] = True
            
        else:
            # Server offline
            models.save_metrics(
                server_id=server_id,
                cpu_percent=0,
                memory_percent=0,
                memory_used=0,
                memory_total=0,
                storage_percent=0,
                storage_used=0,
                storage_total=0,
                is_online=0
            )
            
            # Check if server went offline
            if server_id in self.previous_online_status and self.previous_online_status[server_id]:
                self.notify_server_offline(server)
            
            self.previous_online_status[server_id] = False
            
            logger.error(f"Failed to collect metrics for {server['name']}: {result.get('error', 'Unknown error')}")
    
    def collect_all_metrics(self):
        """Collect metrics for all servers"""
        servers = models.get_all_servers()
        
        for server in servers:
            if server.get('is_active'):
                try:
                    self.collect_metrics_for_server(server)
                except Exception as e:
                    logger.error(f"Error collecting metrics for {server['name']}: {e}")
        
        # Cleanup old metrics
        models.cleanup_old_metrics(config.Config.METRICS_RETENTION_HOURS)
        
    def get_thresholds(self):
        '''Get current thresholds from settings'''
        return {
            'cpu': int(models.get_setting('cpu_threshold', config.Config.DEFAULT_CPU_THRESHOLD)),
            'memory': int(models.get_setting('memory_threshold', config.Config.DEFAULT_MEMORY_THRESHOLD)),
            'storage': int(models.get_setting('storage_threshold', config.Config.DEFAULT_STORAGE_THRESHOLD)),
            # CPU evaluation settings
            'cpu_datapoints': int(models.get_setting('cpu_datapoints', config.Config.DEFAULT_CPU_DATAPOINTS)),
            'cpu_evaluation_minutes': int(models.get_setting('cpu_evaluation_minutes', config.Config.DEFAULT_CPU_EVALUATION_MINUTES)),
            # Memory evaluation settings
            'memory_datapoints': int(models.get_setting('memory_datapoints', config.Config.DEFAULT_MEMORY_DATAPOINTS)),
            'memory_evaluation_minutes': int(models.get_setting('memory_evaluation_minutes', config.Config.DEFAULT_MEMORY_EVALUATION_MINUTES)),
            # Storage evaluation settings
            'storage_datapoints': int(models.get_setting('storage_datapoints', config.Config.DEFAULT_STORAGE_DATAPOINTS)),
            'storage_evaluation_minutes': int(models.get_setting('storage_evaluation_minutes', config.Config.DEFAULT_STORAGE_EVALUATION_MINUTES)),
        }
    
    def check_thresholds(self, server, metrics, thresholds):
        '''Check if metric exceeds threshold based on datapoint count'''
        logger.info(f"=== Checking thresholds for server: {server['name']} ===")
        
        token = models.get_setting('telegram_token')
        chat_id = models.get_setting('telegram_chat_id')
        logger.info(f"Telegram token: {'SET' if token else 'NOT SET'}, chat_id: {'SET' if chat_id else 'NOT SET'}")
        
        if not token or not chat_id:
            logger.warning("Telegram not configured, skipping threshold check")
            return
        
        notifier = telegram_bot.TelegramNotifier(token, chat_id)
        
        # Get recent metrics for CPU evaluation
        server_id = server['id']
        cpu_datapoints = thresholds['cpu_datapoints']
        cpu_eval_minutes = thresholds['cpu_evaluation_minutes']
        recent_cpu = models.get_metrics_in_minutes(server_id, cpu_eval_minutes)
        cpu_exceeds = sum(1 for m in recent_cpu if m['cpu_percent'] >= thresholds['cpu'])
        logger.info(f"CPU: {len(recent_cpu)} datapoints in {cpu_eval_minutes} min, threshold={thresholds['cpu']}%")
        
        if cpu_exceeds >= cpu_datapoints:
            logger.info(f"CPU alert triggered: {cpu_exceeds}/{cpu_datapoints} exceeded {thresholds['cpu']}%")
            notifier.send_threshold_alert(
                server['name'], 'cpu', 
                metrics['cpu_percent'], thresholds['cpu'],
                f'{cpu_exceeds}/{cpu_datapoints} datapoints in {cpu_eval_minutes} min'
            )
        
        # Memory evaluation
        memory_datapoints = thresholds['memory_datapoints']
        memory_eval_minutes = thresholds['memory_evaluation_minutes']
        recent_memory = models.get_metrics_in_minutes(server_id, memory_eval_minutes)
        memory_exceeds = sum(1 for m in recent_memory if m['memory_percent'] >= thresholds['memory'])
        logger.info(f"Memory: {len(recent_memory)} datapoints in {memory_eval_minutes} min, threshold={thresholds['memory']}%")
        
        if memory_exceeds >= memory_datapoints:
            logger.info(f"Memory alert triggered: {memory_exceeds}/{memory_datapoints} exceeded {thresholds['memory']}%")
            notifier.send_threshold_alert(
                server['name'], 'memory',
                metrics['memory_percent'], thresholds['memory'],
                f'{memory_exceeds}/{memory_datapoints} datapoints in {memory_eval_minutes} min'
            )
        
        # Storage evaluation
        storage_datapoints = thresholds['storage_datapoints']
        storage_eval_minutes = thresholds['storage_evaluation_minutes']
        recent_storage = models.get_metrics_in_minutes(server_id, storage_eval_minutes)
        storage_exceeds = sum(1 for m in recent_storage if m['storage_percent'] >= thresholds['storage'])
        logger.info(f"Storage: {len(recent_storage)} datapoints in {storage_eval_minutes} min, threshold={thresholds['storage']}%")
        
        if storage_exceeds >= storage_datapoints:
            logger.info(f"Storage alert triggered: {storage_exceeds}/{storage_datapoints} exceeded {thresholds['storage']}%")
            notifier.send_threshold_alert(
                server['name'], 'storage',
                metrics['storage_percent'], thresholds['storage'],
                f'{storage_exceeds}/{storage_datapoints} datapoints in {storage_eval_minutes} min'
            )

# Global collector instance
collector = MetricsCollector()

