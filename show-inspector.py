#!/usr/bin/env python

# convertSize() taken from:
# http://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python

import json
import os
import math
import sys
from ironicclient import client as iclient
from swiftclient import client as sclient


def convertSize(size):
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size,1024)))
   p = math.pow(1024,i)
   s = round(size/p,2)
   if (s > 0):
       return '%s %s' % (s,size_name[i])
   else:
       return '0B'


def getConfig():
    kwargs = {'os_username': None,
              'os_password': None,
              'os_auth_url': None,
              'os_tenant_name': None
              }

    for variable in kwargs.keys():
        try:
            kwargs[variable] = os.environ[variable.upper()]
        except KeyError:
            print "Variable ${variable} is not set.".format(variable=variable.upper())
            sys.exit(1)

    return(kwargs)


def getIronicNodes(**kwargs):
    uuids = []
    ironic = iclient.get_client(1, **kwargs)
    nodes = ironic.node.list(detail=True)
    for node in nodes:
        try:
            if node.extra['hardware_swift_object']:
                uuids.append(node.uuid) 
        except KeyError:
            print "WARNING: could not find introspection data for node " \
            "{node}.".format(node=node.uuid)
            pass
    return uuids


def getIntrospectionData(**kwargs):
    swift = sclient.Connection(
        user = kwargs['os_username'],
        key = kwargs['os_password'],
        authurl = kwargs['os_auth_url'],
        tenant_name = 'service',
        auth_version = 2
        )
    object_name = "extra_hardware-"+uuid
    data_touple = swift.get_object('ironic-discoverd',object_name)
    data = data_touple[1]

    return data


def prettyPrintNodeData(data):
    ram_total = 0
    disks = []
    cpus = {}
    nics = {}
    ipmi_mac = None
    ipmi_ip = None

    for i in data_json:
        if i[0] == 'memory' and i[1] == 'total' and i[2] == 'size':
            ram_total += int(i[3])
        if i[0] == 'disk' and i[2] == 'size':
            disks.append([i[1], i[3]])
        if i[0] == 'cpu' and i[2] == 'number':
            cpus[i[1]] = i[3]
        if i[0] == 'ipmi' and i[2] == 'mac-address':
            ipmi_mac = i[3]
        if i[0] == 'ipmi' and i[2] == 'ip-address':
            ipmi_ip = i[3]
        if i[0] == 'network':
            nic_name = i[1]
            if nic_name not in nics.keys():
                nics[nic_name] = {}
            if i[2] == 'link':
                nics[nic_name]['link'] = i[3]
            if i[2] == 'speed':
                nics[nic_name]['speed'] = i[3]
            if i[2] == 'serial':
                nics[nic_name]['serial'] = i[3]
            if i[2] == 'businfo':
                nics[nic_name]['businfo'] = i[3]



    print "Node {uuid}: ".format(uuid=uuid)
    print "  IPMI: {ipmi_ip} ({ipmi_mac})".format(ipmi_ip=ipmi_ip, ipmi_mac=ipmi_mac)
    print "  CPU: physical: {physical}, logical: {logical}".format(physical=cpus['physical'], logical=cpus['logical'])
    print "  RAM: {size}".format(size=convertSize(ram_total))
    print "  Disks:"
    for disk in disks:
        print "    - /dev/{drive}: {disk_size}".format(drive=disk[0], disk_size=disk[1])
    print "  NICs:"
    nic_n = 1
    for nic in sorted(nics, key=lambda x: (nics[x]['businfo'])):
        serial = nics[nic].get('serial', 'Unknown')
        link = nics[nic].get('link', 'Unknown')
        speed = nics[nic].get('speed', 'Unknown')
        businfo = nics[nic].get('businfo')
        if link == 'no':
            print "    - DOWN: {nic} ({serial}): link up: {link},\tlink speed:"\
              "{speed},\t{businfo}".format(nic_n=nic_n, nic=nic,
                  link=link, speed=speed, serial=serial, businfo=businfo)
        else:
          print "    - nic{nic_n}: {nic} ({serial}): link up: {link},\tlink speed:"\
              "{speed},\t{businfo}".format(nic_n=nic_n, nic=nic,
                  link=link, speed=speed, serial=serial, businfo=businfo)
          nic_n += 1

    print "\n"


if __name__ == "__main__":

    config = getConfig()
    uuids = getIronicNodes(**config)

    for uuid in uuids:
        data = getIntrospectionData(uuid=uuid, **config)
        data_json = json.loads(data)
        prettyPrintNodeData(data_json)



