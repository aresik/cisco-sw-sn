import paramiko
import getpass
import time
import os
import sys
import re
import json
import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

def recv_all(shell, timeout=1.0):
    end = time.time() + timeout
    output = ""
    while time.time() < end:
        if shell.recv_ready():
            output += shell.recv(65536).decode('utf-8', errors='ignore')
            end = time.time() + timeout
        else:
            time.sleep(0.1)
    return output

def parse_show_module(raw):
    """
    Parse 'show module' output and return list of dicts:
      [{'member': 1, 'model': 'C9300-48UXM', 'serial': 'FOC666Y4WY'}, ...]
    """
    if not raw:
        return []

    def looks_like_mac(token):
        t = re.sub(r'[^0-9A-F]', '', token.upper())
        return bool(re.fullmatch(r'[0-9A-F]{12}', t))

    items = []

    for line in raw.splitlines():
        if not line or line.strip().startswith('-'):
            continue
        low = line.lower()
        if 'model' in low and 'serial' in low:
            continue

        l = line.lstrip('*').strip()
        # Expect: member_number, ports, model, serial, mac ...
        m = re.match(r'^\s*(\d+)\s+\d+\s+(\S+)\s+([A-Z0-9\-]{6,})\b', l.upper())
        if m:
            member = int(m.group(1))
            model = m.group(2).strip()
            serial = m.group(3).strip().strip('",')
            if serial and serial.upper():
                items.append({'member': member, 'model': model, 'serial': serial.upper()})
            continue

    # Fallback: try to find labeled serials if table parse failed
    if not items:
        for m in re.finditer(r'(?:Serial(?:\sNo\.?| Number)?|SN)[:\s]*([^\s,;]+)', raw, re.I):
            serial = m.group(1).strip().strip('",').upper()
            if len(serial) < 6:
                continue
            if looks_like_mac(serial):
                continue
            items.append({'member': None, 'model': None, 'serial': serial})
    return items

def run_show_module(host, username, password, command="show module", port=22, timeout=10):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=port, username=username, password=password,
                       look_for_keys=False, allow_agent=False, timeout=timeout)
        shell = client.invoke_shell()
        time.sleep(0.5)
        shell.recv(65536)  # clear banner

        # disable paging
        shell.send("terminal length 0\n")
        time.sleep(0.2)
        shell.recv(65536)

        shell.send(command + "\n")
        time.sleep(1.0)
        out = recv_all(shell, timeout=2.0)

        client.close()

        items = parse_show_module(out)
        return {"host": host, "success": True, "items": items, "raw": out}
    except Exception as e:
        return {"host": host, "success": False, "error": str(e)}

def load_devices(path="devices.txt"):
    hosts = []
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                hosts.append(line)
    except Exception as e:
        print(f"Failed to read devices file '{path}': {e}")
        sys.exit(1)
    if not hosts:
        print(f"No devices found in '{path}'.")
        sys.exit(1)
    return hosts

def main():
    devices_file = input("Devices file [devices.txt]: ").strip() or "devices.txt"
    username = input("SSH username: ").strip()
    password = getpass.getpass("SSH password: ")

    hosts = load_devices(devices_file)
    max_workers = min(20, len(hosts))

    results_map = {}  # host -> list of serials or error

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(run_show_module, h, username, password): h for h in hosts}
        for fut in as_completed(futures):
            res = fut.result()
            host = res.get("host")
            if res.get("success"):
                # run_show_module returns parsed data under "items"
                items = res.get("items") or []
                results_map[host] = items
            else:
                results_map[host] = {"error": res.get("error")}

    # JSON output
    print(json.dumps(results_map, indent=2, ensure_ascii=False))

    # CSV output (host, member:model:serial) - multiple entries joined with semicolon
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["host", "members"])
    for host, val in sorted(results_map.items(), key=lambda x: x[0].lower()):
        if isinstance(val, dict) and "error" in val:
            writer.writerow([host, f"ERROR: {val['error']}"])
        else:
            # val is list of items dicts
            entries = []
            for it in val:
                member = it.get("member")
                model = it.get("model") or ""
                serial = it.get("serial") or ""
                if member is None:
                    entries.append(f"{model}:{serial}")
                else:
                    entries.append(f"{member}:{model}:{serial}")
            writer.writerow([host, ";".join(entries)])
    print("\nCSV output:\n")
    print(buf.getvalue())

if __name__ == "__main__":
    main()
