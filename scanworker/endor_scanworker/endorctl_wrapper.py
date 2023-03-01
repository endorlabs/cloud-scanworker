"""Wrapper for endorctl"""
import os
from .cmd_wrapper import CmdWrapper, CommandError


class EndorController(CmdWrapper):
    def __init__(self, namespace=None, api_token=None, api_secret=None, cmd_path=None):
        cmd_path = os.path.join(self.working_dir, 'endorctl')\
            if cmd_path is None\
            else cmd_path
        super().__init__(cmd_path=cmd_path)
        self.namespace = namespace
        self.api_token = api_token
        self.api_secret = api_secret

    @property
    def endor_env(self):
        return {
            'ENDOR_API_CREDENTIALS_KEY': self.api_token,
            'ENDOR_API_CREDENTIALS_SECRET': self.api_secret,
            'ENDOR_NAMESPACE': self.namespace
        }

    def scan(self, *args, **kwargs):
        return self._run(
            'scan', '--show-progress=false', *args,
            _env=self.endor_env,
            o='json', **kwargs)
        