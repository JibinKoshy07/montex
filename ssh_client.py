import paramiko
import socket
import time
import config

class SSHClient:
    """SSH client for connecting to remote servers"""
    
    def __init__(self, hostname, port, username, auth_type, password=None, key=None, timeout=None):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.auth_type = auth_type
        self.password = password
        self.key = key
        self.timeout = timeout or config.Config.SSH_TIMEOUT
        self.client = None
        self.connected = False
    
    def connect(self):
        """Establish SSH connection"""
        self.client = paramiko.SSHClient()
        # Use RejectPolicy for security - don't auto-add unknown host keys
        # This prevents MITM attacks. Known hosts should be added to known_hosts manually
        self.client.set_missing_host_key_policy(paramiko.RejectPolicy())
        
        try:
            if self.auth_type == 'password':
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=self.timeout,
                    allow_agent=False,
                    look_for_keys=False
                )
            else:
                # Key-based auth
                if self.key:
                    key_obj = paramiko.RSAKey.from_private_key(self.key)
                else:
                    # Use default key
                    key_obj = None
                
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    pkey=key_obj,
                    timeout=self.timeout,
                    allow_agent=True,
                    look_for_keys=True
                )
            
            self.connected = True
            return True
            
        except paramiko.AuthenticationException:
            raise Exception("Authentication failed - invalid credentials")
        except paramiko.SSHException as e:
            raise Exception(f"SSH connection error: {str(e)}")
        except socket.timeout:
            raise Exception("Connection timeout")
        except socket.gaierror:
            raise Exception(f"Cannot resolve hostname: {self.hostname}")
        except Exception as e:
            raise Exception(f"Connection failed: {str(e)}")
    
    def execute(self, command):
        """Execute command and return output"""
        if not self.connected or not self.client:
            raise Exception("Not connected")
        
        stdin, stdout, stderr = self.client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        return {
            'exit_code': exit_code,
            'stdout': output,
            'stderr': error,
            'success': exit_code == 0
        }
    
    def close(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self.connected = False

def test_connection(hostname, port, username, auth_type, password=None, key=None):
    """Test SSH connection"""
    client = SSHClient(hostname, port, username, auth_type, password, key)
    try:
        client.connect()
        result = client.execute('echo "Connection test successful"')
        client.close()
        return {'success': True, 'message': result['stdout'].strip()}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def get_system_metrics(hostname, port, username, auth_type, password=None, key=None):
    """Get system metrics from remote server"""
    client = SSHClient(hostname, port, username, auth_type, password, key)
    
    try:
        client.connect()
        
        # Get CPU usage
        cpu_cmd = "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'"
        cpu_result = client.execute(cpu_cmd)
        
        # Get memory info
        mem_cmd = "free -b | grep Mem"
        mem_result = client.execute(mem_cmd)
        
        # Get disk usage
        disk_cmd = "df -B1 / | tail -1"
        disk_result = client.execute(disk_cmd)
        
        client.close()
        
        # Parse CPU
        cpu_percent = 0.0
        if cpu_result['success'] and cpu_result['stdout'].strip():
            try:
                cpu_percent = float(cpu_result['stdout'].strip())
            except ValueError:
                pass
        
        # Parse memory
        memory_used = 0
        memory_total = 0
        memory_percent = 0.0
        
        if mem_result['success'] and mem_result['stdout'].strip():
            parts = mem_result['stdout'].split()
            if len(parts) >= 3:
                memory_total = int(parts[1])
                memory_used = int(parts[2])
                if memory_total > 0:
                    memory_percent = (memory_used / memory_total) * 100
        
        # Parse disk
        storage_used = 0
        storage_total = 0
        storage_percent = 0.0
        
        if disk_result['success'] and disk_result['stdout'].strip():
            lines = disk_result['stdout'].strip().split('\n')
            if len(lines) > 0:
                parts = lines[-1].split()
                if len(parts) >= 4:
                    storage_total = int(parts[1])
                    storage_used = int(parts[2])
                    if storage_total > 0:
                        storage_percent = (storage_used / storage_total) * 100
        
        return {
            'success': True,
            'cpu_percent': round(cpu_percent, 1),
            'memory_percent': round(memory_percent, 1),
            'memory_used': memory_used,
            'memory_total': memory_total,
            'storage_percent': round(storage_percent, 1),
            'storage_used': storage_used,
            'storage_total': storage_total
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }