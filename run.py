from nash import run_experiment
from util import print_error
import os
import sys


def generate_combinations(algos, size):
    if algos == '':
        return []
    if size == 0:
        return [''];
    with_first = set([(algos[0] + s) for s in generate_combinations(algos, size - 1)])
    without_first = set(generate_combinations(algos[1:], size))
    return sorted(with_first.union(without_first))


# flows: number of flows, e.g. 6
# algos: algos represented by letter, e.g. BC
def generate_flows(nflows, algos):
    combinations = generate_combinations(algos, nflows // 3)
    return generate_flows_rec(3, combinations)


def generate_flows_rec(groups, combinations):
    s = set()
    if groups == 0:
        s.add('')
        return s

    prev = generate_flows_rec(groups - 1, combinations)
    for c in combinations:
        for p in prev:
            s.add(c + p)

    return sorted(s)


class Flow:
    algo = 'bbr'
    rtt = 20


class Config:
    delay = 1
    burst=12288
    bw = 20
    RTTs = [20, 50, 80]
    flows = []
    bits = 'BCBCBC'
    duration = 120
    limit = 1e6


def make_base(nflows, algos, bw, bdps, rtts, duration):
    output_base_dir = 'run1'
    if os.path.exists(output_base_dir):
        print_error("Folder {} already exists!".format(output_base_dir))
        sys.exit(1)

    os.makedirs(output_base_dir)
    os.chdir(output_base_dir)

    list_of_flows = generate_flows(nflows, algos)

    for bdp in bdps:
        output_folder = '{}Mbps-{}BDP-{}flows'.format(bw, bdp, nflows)
        os.makedirs(output_folder)
        os.chdir(output_folder)
        for bits in list_of_flows:
            print("Running experiment {} ({} BDP)".format(bits, bdp))
            config = Config()
            config.bw = bw
            config.RTTs = rtts
            config.limit = bdp * max(rtts) * bw * 1000 / 8
            config.duration = duration
            config.bits = bits
            config.flows = []
            for i in range(len(bits)):
                b = bits[i]
                flow = Flow()
                flow.algo = 'bbr' if b == 'B' else 'cubic'
                flow.rtt = rtts[i // (nflows // 3)]
                config.flows.append(flow)

            run_experiment(config)
            os.system("/root/pcap2csv.sh {}-nemo.pcap".format(bits))

        os.chdir('..')


def run_single(nflows, bits, bw, bdp, rtts, duration):
    print("Running experiment {} ({} BDP)".format(bits, bdp))

    output_base_dir = 'run1'
    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir)
    os.chdir(output_base_dir)

    output_folder = '{}Mbps-{}BDP-{}flows'.format(bw, bdp, nflows)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    os.chdir(output_folder)


    config = Config()
    config.bw = bw
    config.RTTs = rtts
    config.limit = bdp * max(rtts) * bw * 1000 / 8
    config.duration = duration
    config.bits = bits
    config.flows = []
    for i in range(len(bits)):
        b = bits[i]
        flow = Flow()
        flow.algo = 'bbr' if b == 'B' else 'cubic'
        flow.rtt = rtts[i // (nflows // 3)]
        config.flows.append(flow)

    run_experiment(config)
    os.system("/root/pcap2csv.sh {}-nemo.pcap".format(bits))
    os.chdir('..')


def make_6_flow_20Mbps():
    bdps = [0.5, 1, 3, 5, 10]
    bandwidth = 20
    rtts = [20, 50, 80]
    duration = 60
    make_base(6, "BC", bandwidth, bdps, rtts, duration)


def run_multi():
    flows = ["CCCCBC", "CCCCBB"]
    run_single(6, flows[int(sys.argv[1])], 20, 10, [20, 50, 80], 60)


def main():
    run_multi()
    # make_6_flow_20Mbps()


if __name__ == '__main__':
    main()