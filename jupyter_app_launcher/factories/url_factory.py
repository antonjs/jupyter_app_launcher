from subprocess import Popen, PIPE
from typing import Dict, List, Tuple, Union

from ..utils import check_url, get_free_port
from .base_factory import BaseFactory

import logging

log = logging.getLogger("jupyter_app_launcher")


class URLFactory(BaseFactory):
    def __init__(self, config: Dict, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._instances: Dict[str, Popen] = {}

    @staticmethod
    def name():
        return "local-server"

    def process(self, request: Dict, **kwargs) -> str:
        # Use values from request (already resolved on frontend)
        # Fall back to config values if not provided
        cwd = request.get("cwd", self._config.get("cwd", None))
        args = self._config.get("args", [])
        source = self._config.get("source")

        base_url, p = self.start_server(args, cwd, source)
        self._instances[request["instanceId"]] = p
        return base_url

    def terminate(self, request: Dict) -> None:
        p = self._instances.pop(request["instanceId"], None)
        if p:
            p.terminate()

    def terminate_all(self) -> None:
        for p in self._instances.values():
            p.terminate()
        self._instances = {}

    def get_instances(self) -> Dict:
        return self._instances

    def start_server(
        self, args: List[str], cwd: str, source: str
    ) -> Tuple[str, Union[None, Popen]]:
        log.info(
            f"Starting server. Args: {', '.join(args)}. "
            f"Cwd: {cwd}. Source: {source}"
        )

        port = get_free_port()
        p = None
        url_list = source.split("$PORT")
        if len(url_list) > 1:
            url_suffix = source.split("$PORT")[1]
        else:
            url_suffix = ""

        # Use absolute proxy path if configured
        use_absolute = self._config.get("absolute", False)
        proxy_prefix = "proxy/absolute" if use_absolute else "proxy"
        base_url = f"{proxy_prefix}/{port}{url_suffix}"

        if len(args) > 0:
            cmd = list()
            for arg in args:
                log.info(f"Parsing arg: {arg}")
                arg = arg.replace("$PORT", str(port))
                arg = arg.replace("$CWD", cwd)
                log.info(f"Arg is now {arg}")
                cmd.append(arg)

            log.info(f"Running command: {cmd}, cwd={cwd}")
            p = Popen(cmd, stdout=PIPE, stderr=PIPE, cwd=cwd)

        if check_url(source.replace("$PORT", str(port))):
            return base_url, p
        else:
            return None, None
