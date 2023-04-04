import sys, os
import argparse
import json
import shutil
import signal

from enum import IntEnum
from pathlib import Path
from urllib.error import HTTPError, URLError

from endor_aws_secrets import AWSSecret
from endor_scanworker.gh_wrapper import GitHubController
from endor_scanworker.endorctl_wrapper import EndorController
from endor_scanworker.cmd_wrapper import CommandError
from endor_scanworker import fetchtools

class ERROR(IntEnum):
    AWS_ERROR = 125
    INTERRUPTED = 126
    GENERIC_FATAL = 127


# if __name__ != '__main__':
#     print("This is meant to be run as a command-line script; forcing exit", file=sys.stderr)
#     sys.exit(ERROR.GENERIC_FATAL)


def stderr(*args, **kwargs):
    print(''.join(args), file=sys.stderr, **kwargs)


def process_args():
    parser = argparse.ArgumentParser(
        description='Scans all your supported GitHub Repos'
    )

    languages = ['java', 'rust', 'javascript', 'python', 'go']

    parser.add_argument('--aws-secret-name')
    parser.add_argument('--aws-secret-tag', default='EndorLabs_SecretName')
    # parser.add_argument('--github_token')
    # parser.add_argument('--endor_secret')
    parser.add_argument('--lang', action='append', choices=languages)
    parser.add_argument('--gh', type=Path, default='./gh')
    parser.add_argument('--endorctl', type=Path, default='./endorctl')
    parser.add_argument('--results', type=Path)
    
    # hidden configs
    parser.add_argument('--debug', action='store_true', default=os.getenv('ENDOR_DEBUG', False), help=argparse.SUPPRESS)
    parser.add_argument('--scm', default='github', help=argparse.SUPPRESS)


    args = parser.parse_args()
    args.lang = languages if args.lang is None else args.lang
    args.gh = os.path.abspath(args.gh)
    args.endorctl = os.path.abspath(args.endorctl)
    if args.results is not None and not args.results.is_dir():
        raise FileNotFoundError(f"'{args.results}' is not a directory")
    if args.debug:
        os.environ['ENDOR_DEBUG'] = '1'

    return args


def _main():
    config = process_args()
    # from pprint import pprint,pformat
    # stderr(pformat(config))

    if config.aws_secret_name is None:
        try:
            stderr("No secret tag found, trying to fetch")
            config.aws_secret_name = AWSSecret.fetch_tag(config.aws_secret_tag)
            stderr(f"Will get secret named {config.aws_secret_name}")
        except HTTPError as err:
            stderr(f"FATAL: Could not fetch tag data: {err.returncode} {err.reason}")
            if config.debug:
                raise(err)
            sys.exit(ERROR.AWS_ERROR)
        except URLError as err:
            stderr(f"FATAL: Could not fetch tag data: {err.reason}")
            if config.debug:
                raise(err)
            sys.exit(ERROR.AWS_ERROR)
    secrets = AWSSecret(config.aws_secret_name, region=AWSSecret.get_region())

    # Fetch tools if not found
    if not Path(config.gh).is_file():
        stderr(f"Fetching gh as {config.gh}")
        fetchtools.fetch_gh(write_dir=Path(config.gh).parent)
        config.gh = os.path.join(Path(config.gh).parent, 'gh')
    if not Path(config.endorctl).is_file():
        stderr(f"Fetching endorctl as {config.endorctl}")
        fetchtools.fetch_endorctl(write_dir=Path(config.endorctl).parent)
        config.endorctl = os.path.join(Path(config.endorctl).parent, 'endorctl')

    gh = GitHubController(
        username=secrets.github.id, 
        oauth_token=secrets.github.secret_key, 
        domain=secrets.github.domain, 
        namespace=secrets.github.namespace,
        cmd_path=config.gh)

    ec = EndorController(
        namespace=secrets.endor.namespace,
        api_token=secrets.endor.id,
        api_secret=secrets.endor.secret_key)
    
    # Get list of items from github
    repo_list = []
    for lang in config.lang:
        try:
            stderr(f'Listing repos contaning {lang}')
            result = json.loads(gh.list_repos(language=lang).stdout)
            repo_list.extend(result)
        except CommandError as e:
            stderr(e.stderr, e.stdout)
            sys.exit(e.returncode)

    # TODO store list in SQLite DB for management
    # TODO thread out clone + scan processes separately
    # SCAN projects
    seen_project = {}
    interrupted = False
    for project in repo_list:
        if project['url'] in seen_project:
            sdterr(f"Skipping {project['nameWithOwner']} because I've already seen it")
            continue

        scan_options = {}
        if config.scm == 'github':
            scan_options['enable'] = 'github,git,analytics'

        seen_project[project['url']] = True
        try:
            stderr(f"Clone {project['nameWithOwner']}")
            gh.clone(project['nameWithOwner'])
            stderr(f"-> SCANNING {project['name']}")
            results = ec.scan(path=project['name'], **scan_options)

            file_base = f"{project['nameWithOwner'].replace('/','_')}"
        
            if config.results is not None:
                results_file = os.path.join(config.results, f"{file_base}.json")
                stderr(f"-> Writing '{results_file}'")
                with open(results_file, 'w') as jsonfile:
                    jsonfile.write(results.stdout)

            if config.debug:
                log_file = f"{file_base}.log"
                stderr(f"-> Writing '{log_file}'")
                with open(log_file, 'w') as logfile:
                    logfile.write(results.stderr)
                    logfile.write(results.stdout)

        except CommandError as err:
            stderr(f"Returned {err.returncode} from {err.cmd} while scanning {project['nameWithOwner']}")
        except KeyboardInterrupt:
            stderr(">>> Interrupt requested, stopping application")
            interrupted = True

        # Cleanup checked out repo
        if os.path.exists(project['name']):
            stderr(f"Removing '{project['name']}'")
            shutil.rmtree(project['name'])

        if interrupted:
            sys.exit(ERROR.INTERRUPTED)
        

def main():
    try:
        _main()
    except Exception as err:
        if os.getenv('ENDOR_DEBUG', False):
            raise(err)
        else:
            stderr(f"FATAL: {err}")
        
        sys.exit(ERROR.GENERIC_FATAL)
