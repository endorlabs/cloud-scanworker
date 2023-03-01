"""Fetch command line tools `gh` and `endorctl`"""
import os, sys, stat
import json
import tarfile
from urllib.request import urlopen, urlretrieve, urlcleanup, HTTPError

def c_log(*msgs, file=sys.stderr, **kwargs):
    print(''.join(msgs), file=file, **kwargs)


def get_arch():
    arch = os.uname().machine
    archmap = {
        'arm64': 'arm64',
        'armhf': 'armv6',
        'armv6': 'armv6',
        'i386': '386',
        'x32': '386',
        'ia64': '386',
        'any-i386': '386',
        'amd64': 'amd64',
        'any-amd64': 'amd64',
        'x86_64': 'amd64'
    }

    if arch not in archmap:
        raise RuntimeError(f"Machine value '{arch}' not supported; contact maintainer if this is a surprise")

    c_log(f"Arch '{arch}' is category '{archmap[arch]}'")
    return archmap[arch]


def get_os():
    osname = os.uname().sysname
    osmap = {
        'Linux': 'linux',
        'Darwin': 'macOS'
    }

    if osname not in osmap:
        raise RuntimeError(f"OS Name '{osname}' not supported; contact maintainer if this is a surprise")
    
    c_log(f"OS '{osname}' is category '{osmap[osname]}")
    return osmap[osname]


def fetch_exe(url, write_dir, unpack_member=None, filename=None):
    c_log(f"Fetching '{url}'")
    tmpfile, headers = urlretrieve(url)
    
    if unpack_member is not None:
        filename = os.path.basename(unpack_member) if filename is None else filename
        with tarfile.open(tmpfile, 'r:gz') as archive:
            fstream = archive.extractfile(unpack_member)
            with open(os.path.join(write_dir, filename), 'wb') as exefile:
                exefile.write(fstream.read())
    else:
        filename = 'fetched_file' if filename is None else filename
        os.rename(tmpfile, os.path.join(write_dir, filename))
    
    os.chmod(os.path.join(write_dir, filename), stat.S_IRWXU | stat.S_IROTH | stat.S_IXOTH)


def fetch_gh(write_dir='.', version='2.23.0', osname=None, archname=None):
    osname = get_os() if osname is None else osname
    archname = get_arch() if archname is None else archname

    dl_fname = f"gh_{version}_{osname}_{archname}"
    try:
        c_log(f"GET {dl_fname}.tar.gz")
        fetch_exe(
            f"https://github.com/cli/cli/releases/download/v{version}/{dl_fname}.tar.gz",
            write_dir=write_dir,
            unpack_member=f'{dl_fname}/bin/gh')
    except HTTPError as e:
        if e.code == 404 and osname == 'macOS' and archname == 'arm64':
            # retry to fetch the amd64 version because that works just fine
            c_log(f"Didn't find a version for macOS on M1/M2; falling back to amd64")
            return fetch_gh(write_dir, version, osname, 'amd64')
        else:
            raise(e)

        
def fetch_endorctl(write_dir='.', version=None, osname=None, archname=None, api_root='api.endorlabs.com'):
    osname = get_os().lower() if osname is None else osname
    archname = get_arch().lower() if archname is None else archname

    if version is None:
        with urlopen(f'https://{api_root}/meta/version') as r:
            response = r.read()
        verdata = json.loads(response)
        from pprint import pprint
        pprint(verdata)
        version = verdata['Service']['Version']
    
    dl_fname=f"endorctl_{version}_{osname}_{archname}"
    c_log(f"GET {dl_fname} {version}")
    fetch_exe(
        f"https://storage.googleapis.com/endorlabs/{version}/binaries/{dl_fname}",
        write_dir=write_dir,
        filename='endorctl')
