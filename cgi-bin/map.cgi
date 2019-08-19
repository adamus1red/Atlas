#!/usr/bin/env python3

import urllib3
import sqlite3
import json
from shutil import copyfile
import os
import hashlib 

def create_connection(db_file):
    try:
        conn = sqlite3.connect('file:'+db_file+'?mode=ro', uri=True)
        return conn
    except Exception as ex:
        print(ex)
    return None

def create_httppool():
    try:
        return urllib3.PoolManager(cert_reqs='CERT_NONE')
    except Exception as ex:
        print(ex)
    return None

def fetchHostData(conn, host):
    cur = conn.cursor()
    d=cur.execute("SELECT class,os,os_version,uplink,type FROM hosts h, ostype o WHERE h.os_id=o.os_id AND hostname = ?", (host,)).fetchone()
    return d

def getAllHosts(conn):
    cur = conn.cursor()
    d=cur.execute("SELECT hostname,class,os,os_version,uplink,type FROM hosts h, ostype o WHERE h.os_id=o.os_id").fetchall()
    return d

def getFileHash(file):
    # BUF_SIZE is totally arbitrary, change for your app!
    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!

    md5 = hashlib.md5()
    sha1 = hashlib.sha1()

    with open(file, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
            #sha1.update(data)
    return md5.hexdigest()

def main():
    copyfile("/mnt/dist/core/hostdata.db", "/tmp/hostdata.db")
    conn = create_connection("/tmp/hostdata.db")
    http = create_httppool()

    r=http.request('GET',"https://localhost/dhcp.leases")
    raw_data=r.data.decode('utf-8').split('\n')
    hosts=[]
    unknowns=0
    for rd in raw_data:
        temp=rd.split(' ')
        if len(temp) > 2:
            # print (temp)
            db_data=fetchHostData(conn,temp[3])
            if db_data is None:
                if "00:0c:29:" not in temp[1]:
                    db_data=(None,None,None,"sw-01",None)
                else:
                    db_data=("server",None,None,"olympus","vm")
            if temp[3] is "*":
                temp[3]="Unknown-" + str(unknowns)
                unknowns += 1
            hosts.append({"hostname": temp[3], "ip": temp[2],"class":db_data[0], "os":db_data[1], "os_version":db_data[2], "uplink":db_data[3], "type":db_data[4], "mac": temp[1]})
    for d in getAllHosts(conn):
        #print(json.dumps(d))
        found=False
        for i in range(len(hosts)):
            if hosts[i]["hostname"]==d[0]:
                    found=True
                    break
        if not found:
            db_data=fetchHostData(conn,d[0])
            hosts.append({"hostname": d[0], "ip": None,"class":db_data[0], "os":db_data[1], "os_version":db_data[2], "uplink":db_data[3], "type":db_data[4], "mac": None})
    os.remove("/tmp/hostdata.db")
    print('Content-Type: application/json\n\n')
    print('{"data":' + json.dumps(hosts) + ',"hash": ' + getFileHash("/tmp/hostdata.db") + getFileHash("/tmp/dhcp.leases") + ' }')
    #print(type(hosts))

if __name__ == '__main__':
    main()