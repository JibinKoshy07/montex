import requests
import logging

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram notification handler"""
    
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, text, parse_mode='HTML'):
        """Send message to Telegram"""
        logger.info(f"Sending Telegram message: {text[:50]}...")
        
        if not self.token or not self.chat_id:
            logger.warning("Telegram not configured - no token or chat_id")
            return {'success': False, 'message': 'Telegram not configured'}
        
        url = f"{self.api_url}/sendMessage"
        data = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                logger.info("Telegram message sent successfully!")
                return {'success': True, 'message': 'Message sent'}
            else:
                error_msg = result.get('description', 'Unknown error')
                logger.error(f"Telegram API error: {error_msg}")
                return {'success': False, 'message': error_msg}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def test_notification(self):
        """Send test notification"""
        message = "🔔 <b>Montex Test Notification</b>\n\nYour Telegram notifications are configured correctly!"
        return self.send_message(message)
    
    
    def send_threshold_alert(self, server_name, metric, value, threshold, extra_info=None):
        '''Send threshold exceeded alert'''
        emoji = {
            'cpu': '💻',
            'memory': '🧠',
            'storage': '💾'
        }
        
        icon = emoji.get(metric, '⚠️')
        message = f'{icon} <b>Threshold Alert</b>\n\n'
        message += f'Server: <b>{server_name}</b>\n'
        message += f'Metric: {metric.upper()}\n'
        message += f'Current: <b>{value}%</b>\n'
        message += f'Threshold: {threshold}%'
        
        if extra_info:
            message += f'\n{extra_info}'
        
        return self.send_message(message)
    
    def send_server_offline(self, server_name):
        """Send server offline notification"""
        message = f"🔴 <b>Server Offline</b>\n\n"
        message += f"Server: <b>{server_name}</b>\n"
        message += "Status: Unable to connect"
        
        return self.send_message(message)
    
    def send_server_online(self, server_name):
        """Send server back online notification"""
        message = f"🟢 <b>Server Online</b>\n\n"
        message += f"Server: <b>{server_name}</b>\n"
        message += "Status: Connection restored"
        
        return self.send_message(message)

def send_telegram_notification(token, chat_id, message):
    """Send a simple notification"""
    notifier = TelegramNotifier(token, chat_id)
    return notifier.send_message(message)