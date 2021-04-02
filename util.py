import subprocess
import time
import sys
import gzip
import bz2

import os


colors = {
    'red': '[1;31;40m',
    'green': '[1;32;40m',
    'yellow': '[1;33;40m',
}


def print_error(line):
    print(colorize(line, 'red'))


def print_warning(line):
    print(colorize(line, 'yellow'))


def print_success(line):
    print(colorize(line, 'green'))


def colorize(string, color=None):
    if color not in colors.keys():
        return string
    return '\x1b{color}{string}\x1b[0m'.format(color=colors[color], string=string)


def get_git_revision_hash():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.PIPE).rstrip()
    except subprocess.CalledProcessError as e:
        print_error(e)
        return 'unknown'


def get_host_version():
    try:
        return subprocess.check_output(['uname', '-ovr'], stderr=subprocess.PIPE).rstrip()
    except subprocess.CalledProcessError as e:
        print_error(e)
        return 'unknown'


def get_available_algorithms():
    try:
        return subprocess.check_output(['sysctl net.ipv4.tcp_available_congestion_control '
                                        '| sed -ne "s/[^=]* = \(.*\)/\\1/p"'], shell=True)
    except subprocess.CalledProcessError as e:
        print_error('Cannot retrieve available congestion control algorithms.')
        print_error(e)
        return ''


def check_tools():
    missing_tools = []
    tools = {
        'tcpdump': 'tcpdump',
        'ethtool': 'ethtool',
        'netcat': 'netcat',
        'moreutils': 'ts'
    }

    for package, tool in tools.items():
        if not check_tool(tool):
            missing_tools.append(package)

    if len(missing_tools) > 0:
        print_error('Missing tools. Please run')
        print_error('  apt install ' + ' '.join(missing_tools))

    return len(missing_tools)


def check_tool(tool):
    try:
        process = subprocess.Popen(['which', tool], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = process.communicate()[0]
        if out == "":
            return False
    except (OSError, subprocess.CalledProcessError) as e:
        return False
    return True


def print_line(string, new_line=False):
    if new_line:
        string += '\n'
    else:
        string += '\r'
    sys.stdout.write(string)
    sys.stdout.flush()


def print_timer(complete, current):
    share = current * 100.0 / complete

    string = '  {:6.2f}%'.format(share)
    if complete == current:
        string = colorize(string, 'green')

    string += ' ['
    string += '=' * int(share / 10 * 3)
    string += ' ' * (30 - int(share / 10 * 3))
    string += '] {:6.1f}s remaining'.format(complete - current)

    print_line(string, new_line=complete == current)


def sleep_progress_bar(seconds, current_time, complete):
    print_timer(complete=complete, current=current_time)
    while seconds > 0:
        time.sleep(min(1, seconds))
        current_time = current_time + min(1, seconds)
        print_timer(complete=complete, current=current_time)
        seconds -= 1
    return current_time


def compress_file(uncompressed_file, method):
    try:
        subprocess.check_call([method, uncompressed_file])

    except Exception as e:
        print_error('Error on compressing {}.\n {}'.format(uncompressed_file, e))
