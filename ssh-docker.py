#!/usr/bin/python3
import contextlib
import docker
import secrets
import sys
from pathlib import Path

def init_container():
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
    print(f'extraopts={testbed.name}')


def cleanup(container):
    with contextlib.closing(docker.from_env()) as client:
        testbed = client.containers.get(container)
        testbed.stop()


def get_log(container):
    with contextlib.closing(docker.from_env()) as client:
        testbed = client.containers.get(container)
        print(testbed.logs())


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'open':
        init_container()
    elif command == 'cleanup':
        cleanup(sys.argv[2])
    elif command == 'revert':
        cleanup(sys.argv[2])
        init_container()
    elif command == 'debug-failure':
        get_log(sys.argv[2])
    else:
        print(f'invalid command {command}', file=sys.stderr)
        sys.exit(1)
