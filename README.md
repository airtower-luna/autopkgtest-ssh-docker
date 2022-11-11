# Docker testbed for autopkgtest using the SSH virt driver

Use this if you want to use a local Docker service to automatically
run testbeds for
[autopkgtest](https://salsa.debian.org/ci-team/autopkgtest).

Unfortunately autopkgtest doesn't have native support for Docker. But
it has a generic SSH "virtualization" driver: Connect to any host over
SSH, and run tests there. And it lets you tell that SSH driver to call
a custom script to initialize the testbed and provide the SSH
configuration to connect to it.

[`ssh-docker.py`](./ssh-docker.py) in this repository is such a
script, and sets up a Docker container as the testbed for you.

## Deprecation notice :warning:

Autopkgtest has gained built-in support for Docker and Podman, so this
tool is no longer needed. See:
[`autopkgtest-virt-docker`](https://manpages.debian.org/testing/autopkgtest/autopkgtest-virt-docker.1.en.html)

## Usage

Call `autopkgtest` as usual with the `ssh` virt driver, and pass the
`ssh-docker.py` script using the `-s` option:

```sh
autopkgtest my_deb_package/ -- ssh -s autopkgtest-ssh-docker/ssh-docker.py
```

With this command `ssh-docker.py` will:

* Build the included [`Dockerfile`](./Dockerfile).
* Start the resulting image. The init script inside the container runs
  `apt-get update` to ensure `autopkgtest` has fresh repository
  information.
* Install your local SSH public key into the `test` user's
  `~/.ssh/authorized_keys` file.
* Provide the SSH virt driver with the required configuration data.

The container is deleted when `autopkgtest` cleans up or reverts the
testbed, revert then provides a fresh container from the same image.

## Options

You can specify additional options for the script after another `--`,
for example:

```sh
autopkgtest my_deb_package/ -- ssh -s autopkgtest-ssh-docker/ssh-docker.py -- --image my-buildenv:latest
```

Available options are:

* `--apt-proxy URL`: Proxy to use for apt inside the container. If
  `autopkgtest` needs to install the same dependencies in many testbed
  instances a local caching proxy (e.g. `apt-cacher-ng`) can speed up
  things a lot.

* `--dockerfile DOCKERFILE`: Build this Dockerfile and use the image
  as the testbed. The parent directory of the file is used as the
  build context for Docker. Use this if the included Dockerfile
  doesn't suit your needs, e.g. if you need a different distribution,
  or you want to pre-install additional packages.

* `--image IMAGE`: If given alone: use the named image instead of
  building an image. If given with`--dockerfile`: tag the freshly
  build image with this tag. This behavior is similar to the [`image`
  option](https://docs.docker.com/compose/compose-file/#image) in a
  `docker-compose.yml` file.

You can also run
```sh
./ssh-docker.py open -h
```
to get the list of supported options directly from the script.
