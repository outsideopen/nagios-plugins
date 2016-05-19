#!/usr/bin/env python
#
# SNMP Disk reporter
#
# Currently this only supports snmp v1
#
# :author David Lundgren <dlundgren@syberisle.net>:
#
from __future__ import division
import optparse
import subprocess
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


def parse_snmp_entry(entry):
    line = entry.split(':')
    t = line[0].strip()
    if t == 'INTEGER' or t == 'GAUGE32':
        return int(line[1].strip())
    elif t == 'STRING' or t == 'OID':
        return line[1].strip()

    return 'UNKNOWN'

def get_disks(host, community):
    '''Returns the number of cpus

    :param host:
    :param community:
    :return int: The number of cpus
    '''
    disks = {}
    lines = call_snmpwalk(host, community, '.1.3.6.1.2.1.25.2.3.1')[1].split("\n")
    for line in lines:
        tmp = line.split("=")
        if line.startswith('.1.3.6.1.2.1.25.2.3.1.1.'):
            idx = int(tmp[0].replace('.1.3.6.1.2.1.25.2.3.1.1.', '').strip())
            disks[idx] = {}
        elif line.startswith('.1.3.6.1.2.1.25.2.3.1.2.'):
            idx = int(tmp[0].replace('.1.3.6.1.2.1.25.2.3.1.2.', '').strip())
            disks[idx]['type'] = parse_snmp_entry(tmp[1])
        elif line.startswith('.1.3.6.1.2.1.25.2.3.1.3.'):
            idx = int(tmp[0].replace('.1.3.6.1.2.1.25.2.3.1.3.', '').strip())
            disks[idx]['descr'] = parse_snmp_entry(tmp[1])
        elif line.startswith('.1.3.6.1.2.1.25.2.3.1.4.'):
            idx = int(tmp[0].replace('.1.3.6.1.2.1.25.2.3.1.4.', '').strip())
            disks[idx]['units'] = parse_snmp_entry(tmp[1])
        elif line.startswith('.1.3.6.1.2.1.25.2.3.1.5.'):
            idx = int(tmp[0].replace('.1.3.6.1.2.1.25.2.3.1.5.', '').strip())
            disks[idx]['size'] = parse_snmp_entry(tmp[1])
        elif line.startswith('.1.3.6.1.2.1.25.2.3.1.6.'):
            idx = int(tmp[0].replace('.1.3.6.1.2.1.25.2.3.1.6.', '').strip())
            disks[idx]['used'] = parse_snmp_entry(tmp[1])

    calcs = []
    oids = [
        '.1.3.6.1.2.1.25.2.1.4',
        '.1.3.6.1.2.1.25.2.1.5',
        '.1.3.6.1.2.1.25.2.1.6',
        '.1.3.6.1.2.1.25.2.1.7',
        '.1.3.6.1.2.1.25.2.1.8',
        '.1.3.6.1.2.1.25.2.1.9',
    ]

    for idx in sorted(disks):
        if not disks[idx]['type'] in oids:
            continue
        total = disks[idx]['size'] * disks[idx]['units']
        used = disks[idx]['used'] * disks[idx]['units']
        calcs.append({
            'path' : disks[idx]['descr'],
            'total': total,
            'used' : used,
            'avail' : total - used,
            'percent' : round((used/total)*100,0)
        })

    return calcs

def resolve_size_calc(total):
    '''Resolves the size calculation to MB or GB
    :param total:
    :return:
    '''
    # start on KB
    unit = 1024
    unitDisplay = 'KB'
    useRounding = False
    if total >= 1024**2:
        unit = 1024**2
        unitDisplay = 'MB'
        useRounding = True
    if total >= 1024**3:
        unit = 1024**3
        unitDisplay = 'GB'
        useRounding = True
    if total >= 1024**4:
        unit = 1024**4
        unitDisplay = 'TB'
        useRounding = True

    return (unit, unitDisplay, useRounding)

def format_disk(disk):
    '''Formats the disk output

    :param disk:
    :return:
    '''

    unit, unitDisplay, useRounding = resolve_size_calc(disk['total'])
    total = disk['total'] / unit
    avail = disk['avail'] / unit

    if total is 0:
        return "%s 0 MB (100%%)" % disk['path'].strip('"')

    if useRounding:
        avail = round(avail, 1)

    return "%s %.f %s (%.f%%)" % (disk['path'].strip('"'), round(avail), unitDisplay, (disk['avail'] / disk['total']) * 100)

def format_disk_perf(disk, warn, crit):
    '''Formats the disk performance metrics
    :param disk:
    :param warn:
    :param crit:
    :return:
    '''

    unit, unitDisplay, useRounding = resolve_size_calc(disk['total'])
    total = disk['total'] / unit
    used = disk['used'] / unit
    wt = round(total - (total * (warn / 100.0)), 0)
    ct = round(total - (total * (crit / 100.0)), 0)

    return "%s=%.f%s;%d;%d;%d;%d" % (disk['path'].strip('"'), round(used), unitDisplay, wt, ct, 0, round(total))

def main():
    parser = optparse.OptionParser()
    parser.add_option("-C", dest="community", help="SNMP Community string")
    parser.add_option("-H", dest="host", help="Hostname / IP Address")
    parser.add_option("-w", dest="warning", help="Disk Usage warning % (default: 20)", default="20")
    parser.add_option("-c", dest="critical", help="Disk Usage warning % (default: 10)", default="10")
    parser.add_option("-e", dest="errors_only", action="store_true", default=False, help="Display only devices/mountpoints with errors")
    parser.add_option("-p", dest="perf", action="store_true", default=False)

    options, args = parser.parse_args()

    warn = int(options.warning)
    crit = int(options.critical)

    disks = get_disks(options.host, options.community)

    if len(disks) == 0:
        print "DISK UNKNOWN - unable to retrieve disks"
        sys.exit(3)

    # cycle through all the disks and see if we have any errors
    outDisks = []
    perf = []
    hasWarn = False
    hasCrit = False
    for idx in disks:
        p = 100 - int(idx['percent'])
        if p <= crit:
            hasCrit = True
        elif p <= warn:
            hasWarn = True
        if options.perf:
            perf.append(format_disk_perf(idx, warn, crit))
        if options.errors_only:
            if hasCrit or hasWarn:
                outDisks.append(format_disk(idx))
        else:
            outDisks.append(format_disk(idx))


    state = 0
    status = "OK"
    if hasCrit:
        state = 2
        status = "CRIT"
    elif hasWarn:
        state = 1
        status = "WARN"

    print "DISK %s" % status,
    if options.errors_only and state is 0:
        None
    else:
        print "- free space",
    if outDisks:
        print "; ".join(outDisks),
    if options.perf:
        print "| %s" % "; ".join(perf)
    print ""
    sys.exit(state)

if __name__ == "__main__":
    main()