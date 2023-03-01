"""GitHub Wrapper Module"""

import os
from .cmd_wrapper import CmdWrapper, CommandError


class GitHubController(CmdWrapper):
    def __init__(self, username, oauth_token=None, domain='github.com', namespace=None, cmd_path=None):
        cmd_path = os.path.join(self.working_dir, 'gh')\
            if cmd_path is None\
            else cmd_path

        super().__init__(cmd_path=cmd_path)        
        self.username = username
        self.domain = domain
        self.namespace = self.username\
            if namespace is None\
            else namespace
        self.oauth_token = os.getenv("GH_TOKEN", None) if oauth_token is None else oauth_token
    
    @property
    def gh_env(self):
        env = {}
        if self.domain != 'github.com':
            env['GH_HOST'] = self.domain
            env['GH_ENTERPRISE_TOKEN'] = self.oauth_token
        else:
            env['GH_TOKEN'] = self.oauth_token
        env['GH_PROMPT_DISABLED'] = "1"
        env['NO_COLOR'] = "1"
        return env

    def list_repos(self, *args, fields=[], **kwargs):
        for default_field in ['name', 'nameWithOwner', 'url']:
            if default_field not in fields:
                fields.append(default_field)
        output = self._run(
            'repo', 'list', self.namespace, *args, '--json', ','.join(fields),
            _env=self.gh_env,
            **kwargs)
        return output

    def clone(self, repo):
        repopath = repo if '/' in repo else f'{self.namespace}/{repo}'
        space, repo = repopath.split('/',2)
        output = self._run('repo', 'clone', repopath, _env=self.gh_env)
        return {
            'output': output,
            'namespace': space,
            'repo': repo,
        }

