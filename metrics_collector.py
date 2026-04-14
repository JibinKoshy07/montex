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
            logger.info(f"Metrics saved: CPU={result['cpu_percent']}%, Memory={result['memory_percent']}%, Storage={result['storage_percent']}%")
            
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
        thresholds = {
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
        logger.info(f"Loaded thresholds from DB: {thresholds}")
        return thresholds
    
    def check_thresholds(self, server, metrics, thresholds):
        '''Check if metric exceeds threshold based on CloudWatch-style evaluation'''
        logger.info(f"=== Checking thresholds for server: {server['name']} ===")
        
        token = models.get_setting('telegram_token')
        chat_id = models.get_setting('telegram_chat_id')
        logger.info(f"Telegram token: {'SET' if token else 'NOT SET'}, chat_id: {'SET' if chat_id else 'NOT SET'}")
        
        if not token or not chat_id:
            logger.warning("Telegram not configured, skipping threshold check")
            return
        
        notifier = telegram_bot.TelegramNotifier(token, chat_id)
        server_id = server['id']
        
        # Evaluate each metric (CloudWatch-style: ALARM or OK)
        evaluations = {}
        
        # CPU evaluation
        cpu_datapoints = thresholds['cpu_datapoints']
        cpu_eval_minutes = thresholds['cpu_evaluation_minutes']
        recent_cpu = models.get_metrics_in_minutes(server_id, cpu_eval_minutes)
        cpu_exceeds = sum(1 for m in recent_cpu if m['cpu_percent'] >= thresholds['cpu'])
        in_alarm_cpu = cpu_exceeds >= cpu_datapoints
        evaluations['cpu'] = in_alarm_cpu
        logger.info(f"CPU: {cpu_exceeds}/{cpu_datapoints} datapoints exceed {thresholds['cpu']}% -> {'ALARM' if in_alarm_cpu else 'OK'}")
        
        # Memory evaluation
        memory_datapoints = thresholds['memory_datapoints']
        memory_eval_minutes = thresholds['memory_evaluation_minutes']
        recent_memory = models.get_metrics_in_minutes(server_id, memory_eval_minutes)
        memory_exceeds = sum(1 for m in recent_memory if m['memory_percent'] >= thresholds['memory'])
        in_alarm_memory = memory_exceeds >= memory_datapoints
        evaluations['memory'] = in_alarm_memory
        logger.info(f"Memory: {memory_exceeds}/{memory_datapoints} datapoints exceed {thresholds['memory']}% -> {'ALARM' if in_alarm_memory else 'OK'}")
        
        # Storage evaluation  
        storage_datapoints = thresholds['storage_datapoints']
        storage_eval_minutes = thresholds['storage_evaluation_minutes']
        recent_storage = models.get_metrics_in_minutes(server_id, storage_eval_minutes)
        storage_exceeds = sum(1 for m in recent_storage if m['storage_percent'] >= thresholds['storage'])
        in_alarm_storage = storage_exceeds >= storage_datapoints
        evaluations['storage'] = in_alarm_storage
        logger.info(f"Storage: {storage_exceeds}/{storage_datapoints} datapoints exceed {thresholds['storage']}% -> {'ALARM' if in_alarm_storage else 'OK'}")
        
        # Check state changes and notify only on transition (CloudWatch-style)
        for metric, in_alarm in evaluations.items():
            old_state = models.get_alarm_state(server_id, metric)
            new_state = 'ALARM' if in_alarm else 'OK'
            
            if old_state != new_state:
                logger.info(f"State change: {server['name']} {metric.upper()}: {old_state} -> {new_state}")
                # Save new state
                models.set_alarm_state(server_id, metric, new_state)
                
                if new_state == 'ALARM':
                    notifier.send_alarm_state(
                        server['name'], metric, 'ALARM',
                        thresholds[metric], metrics[f'{metric}_percent']
                    )
                else:
                    notifier.send_alarm_state(
                        server['name'], metric, 'OK',
                        thresholds[metric], metrics[f'{metric}_percent']
                    )

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

