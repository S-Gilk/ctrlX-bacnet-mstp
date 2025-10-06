import json, time
import mstp_services as ms

INI = "/ctrlx-bacnet-mstp/config/bc.ini"  # stable path exposed by layout

def main():
    # WHO-IS / I-AM
    devices = ms.whois(INI, timeout=3.0)
    print(json.dumps({"whois": devices}))

    sent = ms.iam(INI)
    print(json.dumps({"iam": sent}))

    # READ/WRITE examples
    if devices:
        mac = devices[0]["source_mac"]
        devid = devices[0]["device_instance"]

        # read device name
        rp = ms.read(INI, mac, "device", devid, "objectName")
        print(json.dumps({"read_objectName": rp}))

        # discover object list
        # disc = ms.discover(INI, mac, devid, timeout=5.0)
        # print(json.dumps({"discover": disc}))

        # write example (change as appropriate)
        wp = ms.write(INI, mac, "binaryOutput", 1, "presentValue", "inactive", priority=8)
        print(json.dumps({"write": wp}))

    # loop if you want a service cadence
    # while True:
    #     ... call services ...
    #     time.sleep(10)

if __name__ == "__main__":
    main()