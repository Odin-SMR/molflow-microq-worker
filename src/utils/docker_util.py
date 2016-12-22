from subprocess import check_output


def in_docker():
    """Return True if this process is running inside a docker container"""
    with open('/proc/self/cgroup') as inp:
        return 'docker' in inp.read()


def docker_available():
    """Return True if this process can access the docker daemon"""
    try:
        check_output(['docker', 'info'])
        return True
    except:
        return False
