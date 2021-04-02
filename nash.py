'''
router topology example for TCP competions.
   
   h1----+
         |
         r ---- h3
         |
   h2----+

'''

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.examples.linuxrouter import LinuxRouter
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.log import setLogLevel, info
import multiprocessing
import subprocess
import time
import os
import sys


# TODO Buffer usage/Multiple values
from util import sleep_progress_bar


class RTopo(Topo):
    def build(self, flows=[]):  # special names?
        defaultIP = '10.0.0.1/24'  # IP address for r0-eth1
        r = self.addNode('r', cls=LinuxRouter, ip=defaultIP)

        n0 = self.addHost('n0', ip='10.0.0.10/24', defaultRoute='via 10.0.0.1')
        self.addLink(n0, r, intfName1='n0-eth', intfName2='r-eth0', params2={'ip': '10.0.0.1/24'})

        for i, flow in enumerate(flows, 1):
            h = self.addHost('h{}'.format(i), ip='10.0.{}.10/24'.format(i), defaultRoute='via 10.0.{}.1'.format(i))

            self.addLink(h, r, intfName1='h{}-eth'.format(i), intfName2='r-eth{}'.format(i), params2={'ip': '10.0.{}.1/24'.format(i)})


def run_experiment(config):
    rtopo = RTopo(config.flows)
    net = Mininet(topo=rtopo)

    net.start()
    # CLI(net)

    r = net['r']
    IF = 'r-eth0'

    r.cmd('tc qdisc add dev ' + IF + ' root handle 1: netem delay ' + str(config.delay) + 'ms')
    r.cmd('tc qdisc add dev ' + IF + ' parent 1: handle 10: tbf rate ' + str(config.bw) + 'mbit' + \
          ' burst ' + str(config.burst) + ' limit ' + str(config.limit))

    n0 = net['n0']

    print('Starting receiver..')
    for idx, flow in enumerate(config.flows, 1):
        n0.cmd('iperf3 -s -p {} &> /dev/null &'.format(5000 + idx))

    # Start PCAP tracing
    r.cmd('tcpdump -i r-eth0 -n tcp -s 88 -w {}-nemo.pcap &'.format(config.bits))

    print('Starting senders..')

    for idx, flow in enumerate(config.flows, 1):
        hlog = '{}-h{}.log'.format(config.bits, idx)
        h = net['h{}'.format(idx)]
        r.cmd('tc qdisc add dev h{}-eth root handle 1: netem delay {} ms'.format(idx, flow.rtt))
        h.cmd('iperf3 -c 10.0.0.10 -t ' + str(config.duration) + ' -i 1 -p ' + str(5000 + idx) + ' -C ' + str(flow.algo) + ' &> ' + hlog + ' &')

    time.sleep(2)
    start = 0
    current_time = 0
    complete = config.duration
    current_time = sleep_progress_bar(start, current_time=current_time, complete=complete)
    current_time = sleep_progress_bar((complete - current_time) % 1, current_time=current_time, complete=complete)
    current_time = sleep_progress_bar(complete - current_time, current_time=current_time, complete=complete)

    net.stop()


# if __name__ == "__main__":
#
#     ccPairs = [('bbr', 'cubic')]
#     limits = [1e4, 1e5, 1e6, 5e6, 1e7, 5e7, 1e8]
#     bw, delay, burst = 20, 20, 12288  # 20Mbps, 20ms, 12KB
#     duration = 60
#     for run in range(1):
#         for cc1, cc2 in ccPairs:
#             logName = '-'.join([cc1, cc2]) + '.log' + str(run)
#             logFile = open(logName, 'w+')
#
#             for limit in limits:
#                 expName = '-'.join([cc1, cc2, str(convertSize(limit))])
#                 print('\n' + expName)
#
#                 main()
#
#             logFile.close()
