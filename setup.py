import os
import subprocess
import sys
from setuptools import setup, find_packages


PACKAGENAME='firewatch'

if os.path.exists('relic'):
    sys.path.insert(1, 'relic')
    import relic.release
else:
    try:
        import relic.release
    except ImportError:
        try:
            subprocess.check_call(['git', 'clone',
                                   'https://github.com/jhunkeler/relic.git'])
            sys.path.insert(1, 'relic')
            import relic.release
        except subprocess.CalledProcessError as e:
            print(e)
            exit(1)


version = relic.release.get_info()
relic.release.write_template(version, PACKAGENAME)


setup(
    name='firewatch',
    version=version.pep386,
    author='Joseph Hunkeler',
    author_email='jhunk@stsci.edu',
    description='A utility to display the timeline of a Conda channel',
    license='BSD',
    url='https://github.com/jhunkeler/firewatch',
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
