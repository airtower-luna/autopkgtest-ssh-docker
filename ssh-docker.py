#!/usr/bin/python3
import contextlib
import docker
import secrets
import sys
from pathlib import Path

def init_container(args):
    """Set up a docker container to run tests in, output its details in
    the format that autopkgtest-virt-ssh expects.
    """
    ssh_id = None
    for p in ['~/.ssh/id_ed25519', '~/.ssh/id_ecdsa', '~/.ssh/id_rsa']:
        p = Path(p).expanduser()
        if p.is_file():
            ssh_id = p
            break
    if ssh_id is None:
        raise ValueError('No usable SSH ID found!')

    with contextlib.closing(docker.from_env()) as client:
        image, buildlog = client.images.build(path=str(Path(sys.argv[0]).parent))
        for l in buildlog:
            if 'stream' in l:
                print(l['stream'], end='', file=sys.stderr)
            else:
                print(l, file=sys.stderr)

        testbed = client.containers.run(
            image.id, name=f'autopkgtest-{secrets.token_hex(4)}',
            detach=True, auto_remove=True)
        print(testbed.name, file=sys.stderr)

        pubkey = ssh_id.with_suffix('.pub').read_text()
        testbed.exec_run(['sh', '-c', f'echo "{pubkey}" '
                          '>>/home/test/.ssh/authorized_keys'])
        testbed.exec_run(['chown', 'test:test',
                          '/home/test/.ssh/authorized_keys'])

        testbed.reload()
        host = testbed.attrs['NetworkSettings']['Networks']['bridge']['IPAddress']

    print('login=test')
    print(f'hostname={host}')
    print('capabilities=isolation-container,revert,revert-full-system')
    print(f'identity={ssh_id!s}')
    print(f'extraopts=--container {testbed.name}')


def cleanup(args):
    with contextlib.closing(docker.from_env()) as client:
        testbed = client.containers.get(args.container)
        testbed.stop()


def revert(args):
    init_container(args)
    cleanup(args)


def get_log(args):
    with contextlib.closing(docker.from_env()) as client:
        testbed = client.containers.get(args.container)
        print(testbed.logs())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Manage Docker testbed for autopkgtest-virt-ssh.')
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--container', metavar='NAME',
                        help='the running testbed container')
    subparsers = parser.add_subparsers(required=True)
    open_parser = subparsers.add_parser('open', parents=[common])
    open_parser.set_defaults(func=init_container)
    cleanup_parser = subparsers.add_parser('cleanup', parents=[common])
    cleanup_parser.set_defaults(func=cleanup)
    revert_parser = subparsers.add_parser('revert', parents=[common])
    revert_parser.set_defaults(func=revert)
    debug_parser = subparsers.add_parser('debug-failure', parents=[common])
    debug_parser.set_defaults(func=get_log)
    args = parser.parse_args()
    args.func(args)
