def in_docker():
    """Return True if this process is running inside a docker container"""
    with open('/proc/self/cgroup') as inp:
        return 'docker' in inp.read()
