#!/usr/bin/python3
import contextlib
import docker
import secrets
import sys
from pathlib import Path


def get_addr(net):
    for t in ('GlobalIPv6Address', 'IPAddress'):
        addr = net.get('GlobalIPv6Address')
        if addr:
            return addr
    return None


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

    if args.dockerfile is None and args.image is None:
        # No configuration, use default Dockerfile
        dockerfile = Path(sys.argv[0]).parent / 'Dockerfile'
    else:
        # If dockerfile is None the image will be used without build.
        dockerfile = Path(args.dockerfile) if args.dockerfile else None

    env = dict()
    if args.apt_proxy is not None:
        env['http_proxy'] = args.apt_proxy

    with contextlib.closing(docker.from_env()) as client:
        if dockerfile:
            image, buildlog = client.images.build(dockerfile=str(dockerfile),
                                                  path=str(dockerfile.parent),
                                                  tag=args.image,
                                                  buildargs=env,
                                                  forcerm=True)
            for l in buildlog:
                if 'stream' in l:
                    print(l['stream'], end='', file=sys.stderr)
                else:
                    print(l, file=sys.stderr)
        else:
            image = client.images.get(args.image)

        testbed = client.containers.run(
            image.id, name=f'autopkgtest-{secrets.token_hex(4)}',
            environment=env,
            detach=True, auto_remove=True)
        print(testbed.name, file=sys.stderr)

        pubkey = ssh_id.with_suffix('.pub').read_text()
        testbed.exec_run(['sh', '-c', f'echo "{pubkey}" '
                          '>>/home/test/.ssh/authorized_keys'])
        testbed.exec_run(['chown', 'test:test',
                          '/home/test/.ssh/authorized_keys'])
        if args.apt_proxy is not None:
            testbed.exec_run(['sh', '-c',
                              r'echo "Acquire::http::proxy \"'
                              f'{args.apt_proxy}'
                              r'\";" '
                              '>/etc/apt/apt.conf.d/01proxy'])

        testbed.reload()
        for net in testbed.attrs['NetworkSettings']['Networks'].values():
            host = get_addr(net)
            if host:
                break

    print('login=test')
    print(f'hostname={host}')
    print('capabilities=isolation-container,revert,revert-full-system')
    print(f'identity={ssh_id!s}')
    print(f'extraopts=--container {testbed.name} --image {image.id}')


def cleanup(args):
    with contextlib.closing(docker.from_env()) as client:
        testbed = client.containers.get(args.container)
        testbed.stop()


def revert(args):
    cleanup(args)
    # The extraopts set by the "open" command provide the image ID to
    # use, so prevent rebuild.
    args.dockerfile = None
    init_container(args)


def get_log(args):
    with contextlib.closing(docker.from_env()) as client:
        testbed = client.containers.get(args.container)
        print(testbed.logs())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Manage Docker testbed for autopkgtest-virt-ssh.')

    # All subcommands need to accept the custom parameters, even if
    # they don't use them.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--apt-proxy', metavar='URL',
                        help='Proxy to use for apt inside the running '
                        'container.')
    common.add_argument('--dockerfile',
                        help='Build this Dockerfile and use the image '
                        'as the testbed. The parent directory of the file '
                        'is used as the build context for Docker.')
    common.add_argument('--image',
                        help='If given alone: use the named image instead '
                        'of building an image. If given with --dockerfile: '
                        'tag the freshly build image with this tag.')

    # The extraopts parameters are only for commands on running
    # testbeds.
    running = argparse.ArgumentParser(add_help=False)
    running.add_argument('--container', metavar='NAME',
                         help='Name of the running testbed container')

    subparsers = parser.add_subparsers(required=True)
    open_parser = subparsers.add_parser('open', parents=[common])
    open_parser.set_defaults(func=init_container)
    cleanup_parser = subparsers.add_parser('cleanup',
                                           parents=[common, running])
    cleanup_parser.set_defaults(func=cleanup)
    revert_parser = subparsers.add_parser('revert',
                                          parents=[common, running])
    revert_parser.set_defaults(func=revert)
    debug_parser = subparsers.add_parser('debug-failure',
                                         parents=[common, running])
    debug_parser.set_defaults(func=get_log)
    args = parser.parse_args()
    args.func(args)
