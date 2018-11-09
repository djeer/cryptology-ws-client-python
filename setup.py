import sys
import os

from setuptools import setup

if sys.version_info < (3, 6):
    raise ImportError('cryptology-ws-client-python only supports python3.6 and newer')

base_dir = os.path.dirname(__file__)


with open(os.path.join(base_dir, "README.rst")) as f:
    long_description = f.read()
setup(
    name='cryptology-ws-client',
    version='1.1.5',
    description='Cryptology webscoket client',
    long_description=long_description,
    author='Cryptology',
    author_email='s.prikazchikov@cryptology.com',
    packages=['cryptology'],
    python_requires='>= 3.6',
    install_requires=[
        'aiodns',
        'aiohttp >= 2.3.6',
        'cchardet',
    ],
    extras_require={
        'devel': ['pytz',
                  'pytest-aiohttp'
                  ]
    },
    url='https://github.com/CryptologyExchange/cryptology-ws-client-python',
    long_description_content_type='text/x-rst'
)
