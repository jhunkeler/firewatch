import os
import pkgutil
import sys
from setuptools import setup, find_packages
from subprocess import check_call, CalledProcessError


PACKAGENAME='firewatch'

if not pkgutil.find_loader('relic'):
    relic_local = os.path.exists('relic')
    relic_submodule = (relic_local and
                       os.path.exists('.gitmodules') and
                       not os.listdir('relic'))
    try:
        if relic_submodule:
            check_call(['git', 'submodule', 'update', '--init', '--recursive'])
        elif not relic_local:
            check_call(['git', 'clone', 'https://github.com/spacetelescope/relic.git'])

        sys.path.insert(1, 'relic')
    except CalledProcessError as e:
        print(e)
        exit(1)

import relic.release

version = relic.release.get_info()
relic.release.write_template(version, PACKAGENAME)


setup(
    name='firewatch',
    version=version.pep386,
    author='Joseph Hunkeler',
    author_email='jhunk@stsci.edu',
    description='A utility to display the timeline of a Conda channel',
    license='BSD',
    url='https://github.com/astroconda/firewatch',
    classifiers=[
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    install_requires=[
        'requests',
    ],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'firewatch=firewatch.firewatch:main'
        ],
    },
)
