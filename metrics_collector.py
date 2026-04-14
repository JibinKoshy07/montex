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
            'datapoints': int(models.get_setting('datapoints', config.Config.DEFAULT_DATAPOINTS)),
            'evaluation_minutes': int(models.get_setting('evaluation_minutes', config.Config.DEFAULT_EVALUATION_MINUTES))
        }
    
    def check_thresholds(self, server, metrics, thresholds):
        '''Check if metric exceeds threshold based on datapoint count'''
        token = models.get_setting('telegram_token')
        chat_id = models.get_setting('telegram_chat_id')
        
        if not token or not chat_id:
            return
        
        notifier = telegram_bot.TelegramNotifier(token, chat_id)
        
        # Get recent metrics for evaluation
        server_id = server['id']
        datapoints = thresholds['datapoints']
        evaluation_minutes = thresholds['evaluation_minutes']
        
        # Get metrics in the evaluation period
        recent_metrics = models.get_metrics_in_minutes(server_id, evaluation_minutes)
        
        # Count how many datapoints exceed threshold for each metric
        cpu_exceeds = sum(1 for m in recent_metrics if m['cpu_percent'] >= thresholds['cpu'])
        memory_exceeds = sum(1 for m in recent_metrics if m['memory_percent'] >= thresholds['memory'])
        storage_exceeds = sum(1 for m in recent_metrics if m['storage_percent'] >= thresholds['storage'])
        
        # Only notify if required datapoints exceed threshold
        if cpu_exceeds >= datapoints:
            notifier.send_threshold_alert(
                server['name'], 'cpu', 
                metrics['cpu_percent'], thresholds['cpu'],
                f'{cpu_exceeds}/{datapoints} datapoints in {evaluation_minutes} min'
            )
        
        if memory_exceeds >= datapoints:
            notifier.send_threshold_alert(
                server['name'], 'memory',
                metrics['memory_percent'], thresholds['memory'],
                f'{memory_exceeds}/{datapoints} datapoints in {evaluation_minutes} min'
            )
        
        if storage_exceeds >= datapoints:
            notifier.send_threshold_alert(
                server['name'], 'storage',
                metrics['storage_percent'], thresholds['storage'],
                f'{storage_exceeds}/{datapoints} datapoints in {evaluation_minutes} min'
            )
    def notify_server_offline(self, server):
        """Send server offline notification"""
        token = models.get_setting('telegram_token')
        chat_id = models.get_setting('telegram_chat_id')
        
        if token and chat_id:
            notifier = telegram_bot.TelegramNotifier(token, chat_id)
            notifier.send_server_offline(server['name'])
    
    def notify_server_online(self, server):
        """Send server online notification"""
        token = models.get_setting('telegram_token')
        chat_id = models.get_setting('telegram_chat_id')
        
        if token and chat_id:
            notifier = telegram_bot.TelegramNotifier(token, chat_id)
            notifier.send_server_online(server['name'])
    
    def start(self):
        """Start the metrics collector"""
        if not self.running:
            self.running = True
            # Collect immediately
            self.collect_all_metrics()
            # Schedule periodic collection
            self.scheduler.add_job(
                self.collect_all_metrics,
                'interval',
                seconds=config.Config.METRICS_INTERVAL,
                id='metrics_collection'
            )
            self.scheduler.start()
            logger.info("Metrics collector started")
    
    def stop(self):
        """Stop the metrics collector"""
        if self.running:
            self.scheduler.shutdown()
            self.running = False
            logger.info("Metrics collector stopped")

# Global collector instance
collector = MetricsCollector()