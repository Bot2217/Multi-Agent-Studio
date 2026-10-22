"""
Local network device control via SSH (and simple connectivity checks).
Requires paramiko or system ssh client.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RemoteDevice:
    name: str
    host: str
    user: str = "root"
    port: int = 22
    key_path: Optional[str] = None
    password: Optional[str] = None  # prefer key_path


@dataclass
class RemoteManager:
    devices: dict[str, RemoteDevice] = field(default_factory=dict)

    def add_device(self, device: RemoteDevice) -> str:
        self.devices[device.name] = device
        return f"Added device: {device.name} ({device.user}@{device.host}:{device.port})"

    def list_devices(self) -> str:
        if not self.devices:
            return "No remote devices configured"
        lines = []
        for d in self.devices.values():
            lines.append(f"- {d.name}: {d.user}@{d.host}:{d.port}")
        return "\n".join(lines)

    def ping(self, name: str) -> str:
        d = self.devices.get(name)
        if not d:
            return f"Unknown device: {name}"
        # Cross-platform-ish ping
        import platform
        count_flag = "-n" if platform.system() == "Windows" else "-c"
        try:
            r = subprocess.run(
                ["ping", count_flag, "2", d.host],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return r.stdout or r.stderr or f"ping exit {r.returncode}"
        except Exception as e:
            return f"Ping failed: {e}"

    def run_ssh(self, name: str, command: str, timeout: int = 60) -> str:
        d = self.devices.get(name)
        if not d:
            return f"Unknown device: {name}. Known: {list(self.devices.keys())}"

        # Prefer system ssh (available on most systems)
        if shutil.which("ssh"):
            ssh_cmd = [
                "ssh",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ConnectTimeout=10",
                "-p", str(d.port),
            ]
            if d.key_path:
                ssh_cmd.extend(["-i", d.key_path])
            ssh_cmd.append(f"{d.user}@{d.host}")
            ssh_cmd.append(command)
            try:
                r = subprocess.run(
                    ssh_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                out = (r.stdout or "") + (r.stderr or "")
                return out + f"\n[exit {r.returncode}]"
            except subprocess.TimeoutExpired:
                return f"SSH timed out after {timeout}s"
            except Exception as e:
                return f"SSH error: {e}"

        # Fallback: paramiko if installed
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            kwargs = {
                "hostname": d.host,
                "port": d.port,
                "username": d.user,
                "timeout": 10,
            }
            if d.key_path:
                kwargs["key_filename"] = d.key_path
            elif d.password:
                kwargs["password"] = d.password
            client.connect(**kwargs)
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode() + stderr.read().decode()
            client.close()
            return out
        except ImportError:
            return "Neither system `ssh` nor `paramiko` available. Install openssh-client or pip install paramiko"
        except Exception as e:
            return f"SSH (paramiko) error: {e}"
