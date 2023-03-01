import subprocess
import os
import os.path as path


class CommandError(subprocess.CalledProcessError):
    pass


class CmdWrapper(object):
    def __init__(self, cmd_path=None):
        self.cmd_path = cmd_path
        self._last_output = None
        
        ## sanity checks
        if not path.exists(self.cmd_path):
            raise FileNotFoundError(f"'{self.cmd_path}' does not exist")
    
    @property
    def working_dir(self):
        return path.abspath(os.curdir)
    
    def _run(self, *args, _env={}, **kwargs):
        cmd = self.cmd_path
        args = list(args)
        if _env is None:
            _env = {}

        runenv = os.environ.copy()
        for k in _env.keys():
            # print(f"SET: {k}='{_env[k]}'")
            runenv[k] = _env[k]

        ## map kwargs to switches with args
        for key in kwargs.keys():
            if len(key) == 1:
                args.append(f'-{key}')
            else:
                argname = key.replace('_', '-')
                args.append(f'--{argname}')
            args.append(kwargs[key])

        try:
            output = subprocess.run([cmd] + list(args), env=runenv, capture_output=True, check=True)
            output.stdout = output.stdout.decode('utf8')
            output.stderr = output.stderr.decode('utf8')
            self._last_output = output
            return output
        except subprocess.CalledProcessError as err:
            self._last_output = CommandError(
                err.returncode, err.cmd,
                output=err.output.decode('utf8'), stderr=err.stderr.decode('utf8'))
            raise self._last_output