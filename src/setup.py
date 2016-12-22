""" Hermod uWorker """
from setuptools import setup

setup(
    name='Hermod uWorker',
    version='1.0',
    long_description=__doc__,
    packages=['uclient', 'uworker', 'utils'],
    entry_points={
        'console_scripts': ['uworker = uworker.uworker:main']
    },
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'ConcurrentLogHandler',
        'requests'
    ]
)
