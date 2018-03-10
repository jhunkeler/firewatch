import errno
import json
import platform as PLATFORM
import requests
import sys
import time
from datetime import datetime, timedelta


conda_channel_pool = [
    f'https://repo.continuum.io/pkgs/main',
    # f'https://repo.continuum.io/pkgs/free',  # deprecated: conda<4.3.30
]

time_units = dict(
    s=1,  # second
    m=60,  # minute
    h=3600,  # hour
    d=86400,  # day
    w=604800,  # week
    M=2.628e+6,  # month
    y=3.154e+7,  # year
    D=3.154e+8,  # decade
    c=3.154e+9,  # century
)

system_map = dict(
    Linux='linux',
    Darwin='osx',
    Windows='win'
)

machine_map = dict(
    i386='32',
    x86_64='64'
)


def extract_channel_platform(url):
    """Returns last two elements in URL: (channel/platform-arch)
    """
    parts = [x for x in url.split('/')]
    result = '/'.join(parts[-2:])
    return result


def convert_human_timespan(t):
    """Convert timespan to seconds to generate datetime.timedelta objects
    """
    value, unit = int(t[:-1]), t[-1]
    if unit not in time_units.keys():
        raise ValueError(f'Invalid time unit: "{unit}" (expected: ['
                         f'{"|".join([x for x in time_units.keys()])}])')
    return value * time_units[unit]


def get_packages(channels):
    packages = list()
    for channel in channels:
        repodata = f'{channel}/repodata.json'
        data = dict(
            packages=list(),
            channel=extract_channel_platform(channel),
        )

        try:
            with requests.get(repodata) as r:
                r.raise_for_status()
                data['packages'] = json.loads(r.text)['packages']
                packages.append(data)

        except requests.exceptions.RequestException as e:
            print(f'Error {e.response.status_code}/{e.response.reason}:'
                  f' {channel}', file=sys.stderr)
        except Exception as e:
            print(e)

    return packages


def get_timestamps(data, brute_force=False):
    """ Extract and convert package timestamps to datetime objects
    """
    rt_fmt = '%a, %d %b %Y %H:%M:%S %Z'

    for base in data:
        for pkg_name, pkg_info in base['packages'].items():
            result = dict()
            result['name'] = pkg_name
            result['channel'] = base['channel']

            timestamp = datetime(1970, 1, 1)
            # Continuum used 'date' for tracking some time ago
            if 'date' in pkg_info:
                date_str = [int(x) for x in pkg_info['date'].split('-')]
                timestamp = datetime(*date_str)

            # Newer packages use 'timestamp', but depending on the direction
            # of the wind, the unix epoch is stored in microseconds rather
            # than seconds. So adjust for former case...
            elif 'timestamp' in pkg_info:
                timestamp = datetime.fromtimestamp(pkg_info['timestamp'] // 1000)
                if timestamp < datetime(2000, 1, 1):
                    timestamp = datetime.fromtimestamp(pkg_info['timestamp'])

            # Scan remote server for 'last-modified' timestamp
            # Don't do this unless you own the server you're spamming.
            elif brute_force:
                url = f'{result["channel"]}/{pkg_name}'
                try:
                    modified = requests.head(url).headers['last-modified']
                except requests.exceptions.RequestException as e:
                    print(f'Error {e.response.status_code}/{e.response.reason}:'
                          f' {result["channel"]}', file=sys.stderr)
                    continue
                except Exception as e:
                    print(e)
                    continue

                timestamp = datetime.strptime(modified, rt_fmt)

            result['timestamp'] = timestamp
            yield result


def noarch_channel(channel, platform):
    channel = channel.replace(f'{platform}', 'noarch')
    return channel


def convert_channel(channel, platform, noarch=False):
    # Strip trailing slash
    if channel.endswith('/'):
        channel = channel[:-1]

    # Sanitize URL by stripping out part we will adjust dynamically
    if f'/{platform}' in channel:
        pos = channel.find(f'/{platform}')
        channel = channel[:pos]

    if '://' not in channel:
        channel = f'https://conda.anaconda.org/{channel}/{platform}'
    else:
        channel = f'{channel}/{platform}'

    if noarch:
        channel = noarch_channel(channel, platform)

    return channel


def get_platform():
    """Generate a conda compatible platform-arch string
    """
    system = PLATFORM.system()
    machine = PLATFORM.machine()

    result = None
    try:
        result = '-'.join([system_map[system], machine_map[machine]])
    except KeyError:
        print(f'Unknown platform/arch combination: {system}/{machine}',
              file=sys.stderr)

    return result


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--benchmark', action='store_true',
                        help='Display total time to parse and sort channel data')

    parser.add_argument('--brute-force', action='store_true',
                        help='Derive timestamps from HTTP header: "last-modified"')

    parser.add_argument('--channel', '-c', default=conda_channel_pool,
                        action='append', dest='channels', help='Conda channel')

    parser.add_argument('--order', '-o', default='asc', help='[asc|dsc]')

    parser.add_argument('--platform', '-p', default=[get_platform()],
                        action='append', dest='platforms',
                        help=f'[{"|".join(system_map.values())}]'
                             f'-[{"|".join(machine_map.values())}]')

    parser.add_argument('--time-span', '-t', default='1c',
                        help=f'i[{"|".join([x for x in time_units.keys()])}]'
                        ' (120s, 12h, 1d, 2w, 3m, 4y)')

    args = parser.parse_args()

    order = False  # Ascending
    if args.order != 'asc':
        order = True  # Descending

    if args.benchmark:
        timer_start = time.time()

    channels = list()
    for platform in set(args.platforms):
        channels.extend([convert_channel(x, platform) for x in args.channels])
        channels.extend([convert_channel(x, platform, noarch=True)
                        for x in args.channels])
        channels = sorted(set(channels))

    today = datetime.now()
    span_delta = today - timedelta(seconds=convert_human_timespan(args.time_span))
    packages = get_packages(channels)
    timestamps = sorted(list(get_timestamps(packages, args.brute_force)),
                        reverse=order, key=lambda x: x['timestamp'])

    if args.benchmark:
        timer_stop = time.time()
        print('#benchmark: {:.02f}s'.format(timer_stop - timer_start))

    channel_width = max([len(extract_channel_platform(x)) for x in channels]) + 1
    print('#{:<20s} {:<{channel_width}s}  {:<40s}'.format(
          'date', 'channel', 'package', channel_width=channel_width))

    try:
        for info in timestamps:
            name = info['name']
            ts = info['timestamp']
            chn = info['channel']

            tstr = ts.isoformat()
            if span_delta < ts:
                print(f'{tstr:<20s}: {chn:<{channel_width}s}: {name:<40s}')
    except IOError as e:
        # Broken pipe on '|head'
        # TODO: Figure out why
        if e.errno == errno.EPIPE:
            pass


if __name__ == '__main__':
    main()
