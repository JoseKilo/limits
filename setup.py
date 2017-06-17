import os

from setuptools import setup


BASE_DIR = os.path.dirname(__file__)

with open(os.path.join(BASE_DIR, 'requirements.txt')) as requirements:
    REQUIREMENTS = requirements.read().split('\n')


setup(
    name='limits',
    packages=['limits'],
    include_package_data=True,
    install_requires=REQUIREMENTS,
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
)
