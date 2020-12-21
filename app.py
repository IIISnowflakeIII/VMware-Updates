#!/usr/bin/env python3
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError
from pyVim import connect
from pyVmomi import vim
from os import environ
import logging
import requests
import schedule
import time
import json

#Get host variables
vcenter_host = environ['VCENTER_HOST']
vcenter_usr = environ['VCENTER_USR']
vcenter_pwd = environ['VCENTER_PWD']
influx_host = environ['INFLUX_HOST']
influx_usr = environ['INFLUX_USR']
influx_pwd = environ['INFLUX_PWD']
influx_db = environ['INFLUX_DB']

#Influx client 
influx_client = InfluxDBClient(
  host=influx_host, 
  port=8086, 
  username=influx_usr, 
  password=influx_pwd
)

#VSphere client
vsphere_client = connect.SmartConnectNoSSL (
  host=vcenter_host,
  user=vcenter_usr,
  pwd=vcenter_pwd
)

content = vsphere_client.RetrieveContent()
container = content.rootFolder
viewType = [vim.HostSystem]
containerView = content.viewManager.CreateContainerView(
            container, viewType, recursive=True)

hosts = containerView.view

#Get build number
def host_build_number(host):
  summary = host.summary
  hostname = summary.config.name
  build = summary.config.product.build
  print("Hostname : " + hostname)
  print("Build    : " + build)
  print("")
  return int(build)

#Get lastest ESXi build number from Virten
def latest_build():
  builds = json.loads(requests.get("https://www.virten.net/repo/esxiReleases.json").text)
  latest = (builds['data']['esxiReleases'][0]['build'])
  print("Latest ESXi build is: " + latest)
  return int(latest)

#Writes data to InfluxDB
def write_to_influx(hostname, update):
        measurement = {}
        measurement['measurement'] = 'vsphere_update_available'
        measurement['tags'] = {}
        measurement['tags'] ['host'] = hostname
        measurement['fields'] = {}
        measurement['fields']['value'] = update
        try:
          influx_client.switch_database(influx_db)
          influx_client.write_points([measurement])
          print("Exported to InfluxDB successfully")
          print("")
        except InfluxDBClientError as e:
          logging.error("Failed to export data to Influxdb: %s" % e)

def main():
  for host in hosts:
    summary = host.summary
    hostname = summary.config.name
    if latest_build() >= host_build_number(host):
      write_to_influx(hostname, 1)
    elif latest_build() == host_build_number(host):
      write_to_influx(hostname, 1)

if __name__ == "__main__":
  print("Starting vSphere update monitor...")
  schedule.every(1).minutes.do(main)
  while 1:
    schedule.run_pending()
    time.sleep(1)