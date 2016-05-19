#!/usr/bin/env python
#
# SNMP CPU load averages script
#
# Currently this only supports snmp v1
#
# :author David Lundgren <dlundgren@syberisle.net>:
#
import optparse
import subprocess
import decimal
import sys
import os

def which(file):
    '''Operates like which

    :see http://stackoverflow.com/a/5227009/1281788:
    :param file:
    :return:
    '''
    for path in os.environ["PATH"].split(os.pathsep):
        if os.path.exists(os.path.join(path, file)):
                return os.path.join(path, file)

    return None

def call_snmpwalk(host, community, oid):
    '''Calls to snmpwalk

    :param host:
    :param community:
    :param oid:
    :returns tuple: (returncode, joined output, and err)
    '''
    snmpwalk = which('snmpwalk')
    if snmpwalk is None:
        raise Exception("snmpwalk is missing")
    p = subprocess.Popen([snmpwalk, "-v", "1", "-On", "-c", community, host, oid], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = p.communicate()
    rc = p.returncode

    return (rc, "".join(output), err)


def get_cpu_count(host, community):
    '''Returns the number of cpus

    :param host:
    :param community:
    :return int: The number of cpus
    '''
    lines = call_snmpwalk(host, community, '.1.3.6.1.2.1.25.3.3.1.2')[1].split("\n")
    count = 0
    for line in lines:
        if line.startswith(".1.3.6.1.2.1.25.3.3.1.2"):
            count += 1
    return count

def get_cpu_usage(host, community):
    '''Returns the cpu usage for 1,5,15 minutes

    :param host:
    :param community:
    :return tuple:
    '''
    load_one = call_snmpwalk(host, community, '.1.3.6.1.4.1.2021.10.1.6.1')
    load_five = call_snmpwalk(host, community, '.1.3.6.1.4.1.2021.10.1.6.2')
    load_fifteen = call_snmpwalk(host, community, '.1.3.6.1.4.1.2021.10.1.6.3')

    return (
        decimal.Decimal(load_one[1].split("=")[1].split(':')[-1]),
        decimal.Decimal(load_five[1].split("=")[1].split(':')[-1]),
        decimal.Decimal(load_fifteen[1].split("=")[1].split(':')[-1])
    )

def check_load(cpus, load, warning, critical):
    '''Checks the load agains the warning/critical marks

    The load is enclosed by * when there is a problem

    :param cpus:
    :param load:
    :param warning:
    :param critical:
    :return tuple: (load, load percentage and status)
    '''
    percent_load = round((load/cpus * 100), 0)
    status = 0
    load = "%d" % percent_load
    if percent_load > int(warning):
        status = 1
        load = "*%d*" % percent_load
    if percent_load > int(critical):
        status = 2
        load = "*%d*" % percent_load

    return (load, int(percent_load), status)

def render_load(label, load):
    if len(label) > 0:
        return "%s=%s" % (label, load)
    else:
        return load

def main():
    parser = optparse.OptionParser()
    parser.add_option("-C", dest="community", help="SNMP Community string")
    parser.add_option("-H", dest="host", help="Hostname / IP Address")
    parser.add_option("-w", dest="warning", help="CPU Usage warning % (default: 70,60,50)", default="70,60,50")
    parser.add_option("-c", dest="critical", help="CPU Usage warning % (default: 90,80,70)", default="90,80,70")
    parser.add_option("-l", dest="label", help="CPU usage labels (default: load1,load5,load15)", default="load1,load5,load15")
    parser.add_option("-p", action="store_true", dest="perf", default=False)

    options, args = parser.parse_args()

    warning = options.warning.split(',')
    if len(warning) == 1:
        warning.append(warning[0])
        warning.append(warning[0])
    elif len(warning) == 2:
        warning.append(warning[1])

    critical = options.critical.split(',')
    if len(critical) == 1:
        critical.append(critical[0])
        critical.append(critical[0])
    elif len(critical) == 2:
        critical.append(critical[1])

    label = options.label.split(',')
    if len(label) == 1:
        label.append('')
        label.append('')
    elif len(label) == 2:
        label.append('')

    cpus = get_cpu_count(options.host, options.community)
    l1, l5, l15 = get_cpu_usage(options.host, options.community)

    # we need to check the stats against the warning/critical thresholds
    l1_load, l1_perf_load, l1_status = check_load(cpus, l1, warning[0], critical[0])
    l5_load, l5_perf_load, l5_status = check_load(cpus, l5, warning[1], critical[1])
    l15_load, l15_perf_load, l15_status = check_load(cpus, l15, warning[2], critical[2])

    status = int(l1_status | l5_status | l15_status)
    if status & 2:
        status = "CRIT"
    elif status & 1:
        status = "WARN"
    else:
        status = "OK"

    print "SNMP %s - Load average:" % status,
    print "%s," % (render_load(label[0], l1_load)),
    print "%s," % (render_load(label[1], l5_load)),
    print "%s" % (render_load(label[2], l15_load)),

    if options.perf is True:
        print "|",
        print "%s=%s;%s;%s;0;" % (label[0], l1_perf_load, warning[0], critical[0]),
        print "%s=%s;%s;%s;0;" % (label[1], l5_perf_load, warning[1], critical[1]),
        print "%s=%s;%s;%s;0;" % (label[2], l15_perf_load, warning[2], critical[2]),
    print ""

    if status is "WARN":
        sys.exit(1)

    if status is "CRIT":
        sys.exit(2)

if __name__ == "__main__":
    main()