# ============================================================================
# connectors/ssh_connector.py
# SSH-based CLI Connector for config backups
# ============================================================================

import paramiko
import time
import re
from models.device import Device
from models.enums import VendorType
from utils.logger import setup_logger
from utils.exceptions import DeviceConnectionError

logger = setup_logger(__name__)


def get_nokia_sros_config_sync(host: str, port: int, username: str, password: str) -> str:
    """
    Synchronous Nokia SROS config retrieval - User's proven working script
    No async/await to avoid any timing or connection issues
    """
    logger.info(f"[NOKIA SSH] Attempting connection to {host}:{port} as {username}")
    logger.debug(f"[NOKIA SSH] Host type: {type(host)}, Port type: {type(port)}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        logger.debug(f"[NOKIA SSH] Calling ssh.connect...")
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False
        )
        logger.info(f"[NOKIA SSH] Connected successfully to {host}")

        chan = ssh.invoke_shell(term='vt100', width=200, height=200)
        time.sleep(1)

        if chan.recv_ready():
            chan.recv(65535)

        # Disable pagination
        chan.send("environment more false\n")
        time.sleep(0.5)
        if chan.recv_ready():
            chan.recv(65535)

        # Request full config
        chan.send("admin show configuration\n")
        time.sleep(2)

        output = []
        last = time.time()

        while True:
            if chan.recv_ready():
                chunk = chan.recv(65535).decode(errors="ignore")
                output.append(chunk)
                last = time.time()

                # Check for SROS prompt: A:router> or similar
                if "A:" in chunk and (">" in chunk or "#" in chunk):
                    break
            else:
                # If no data for 2 seconds consider finished
                if time.time() - last > 2:
                    break
                time.sleep(0.2)

        ssh.close()

        text = "".join(output)
        text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
        text = text.replace("\r", "")

        # Skip command echo and banner
        lines = text.split("\n")
        cfg = []
        started = False
        for line in lines:
            l = line.strip()

            if not started:
                if l.startswith("#"):
                    started = True
                    cfg.append(l)
                if "admin show configuration" in l:
                    started = True
                continue

            if "A:" in l and (l.endswith(">") or l.endswith("#")):
                break

            cfg.append(l)

        return "\n".join(cfg)

    except Exception as e:
        logger.exception(f"[NOKIA SSH] Exception during SSH connection to {host}:{port}")
        ssh.close()
        raise DeviceConnectionError(f"Nokia SROS SSH failed: {str(e)}")


class SSHConnector:
    """
    SSH connector for CLI-based configuration retrieval
    """

    def __init__(self, device: Device):
        self.device = device

    def get_config_cli_sync(self) -> str:
        """
        Synchronous config retrieval - no async/await

        Returns:
            Configuration output as string
        """
        try:
            if self.device.vendor == VendorType.NOKIA_SROS:
                logger.info(f"Getting Nokia SROS config from {self.device.hostname} (sync method)")
                logger.debug(f"[DEVICE INFO] hostname={self.device.hostname}, ip={self.device.ip}, port={self.device.port}, username={self.device.username}")

                # Force SSH port to 22 (device.port is 830 for NETCONF, not SSH!)
                port = 22
                logger.debug(f"[DEVICE INFO] Using SSH port={port} (type: {type(port)})")

                config = get_nokia_sros_config_sync(
                    host=self.device.ip,
                    port=port,
                    username=self.device.username,
                    password=self.device.password
                )
                logger.info(f"Retrieved Nokia SROS config from {self.device.hostname} ({len(config)} bytes)")
                return config
            else:
                raise DeviceConnectionError(f"Vendor {self.device.vendor} not supported in sync mode")

        except Exception as e:
            logger.exception(f"Failed to get CLI config from {self.device.hostname}: {str(e)}")
            raise

    async def disconnect(self):
        """
        Disconnect from device - no-op for SSHConnector since connections
        are opened and closed within each operation
        """
        pass
