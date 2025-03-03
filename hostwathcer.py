import concurrent.futures
import datetime
import json
import logging
import multiprocessing
import platform
import queue
import re
import subprocess
import sys

from rich.console import Console
from rich.live import Live
from rich.table import Table
from collections import OrderedDict


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    with open("config.json") as file:
        CFG = json.load(file)
    with open("hosts.txt") as file:
        hosts = file.read().splitlines()
except Exception as e:
    logging.error(f"Error loading config or hosts: {e}")
    sys.exit()

table_structure = OrderedDict((host, {}) for host in hosts)
multiprocess_queue = multiprocessing.Queue()

STATUS_WIDTH = CFG["rich"]["table"]["status_column_width"]
SUCCESS_CHAR = CFG["rich"]["table"]["success_char"]
FAILED_CHAR = CFG["rich"]["table"]["failed_char"]
LOSS_PERCENT_WARNING = CFG["rich"]["table"]["loss_warning"]

console = Console(color_system=CFG["rich"]["console"]["console_color_system"],
                  style=CFG["rich"]["console"]["console_style"])


def get_operating_system():
    system = platform.system()
    if system == 'Windows':
        return 'Windows'
    elif system == 'Linux' or system == 'Darwin':
        return 'Unix'
    else:
        return 'Unknown'


def ping_cmd(host, result_queue):
    system_name = get_operating_system()
    if system_name == 'Windows':
        result = subprocess.run(['ping', '-n', '1', '-w', '00', host],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
    else:
        result = subprocess.run(['ping', '-c', '1', '-W', '1', host],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
    time_match = re.search(r'time=(\d+\.\d+)', result.stdout)
    rtt_match = re.search(r'(\d+\.\d+)\/', result.stdout)
    time = float(time_match.group(1)) if time_match else 0
    rtt = float(rtt_match.group(1)) if rtt_match else 0
    result_queue.put({host: [result.returncode, time, rtt]})


def queue_to_dict(result_queue):
    while not result_queue.empty():
        try:
            result = result_queue.get()
            for hostname, res in result.items():
                status = f"[green]{SUCCESS_CHAR}[/green]" if res[0] == 0 else f"[red]{FAILED_CHAR}[/red]"
                loss = 0 if res[0] == 0 else 1
                if len(table_structure[hostname].values()) == 0:
                    table_structure[hostname] = {
                        "status": [status],
                        "time": res[1],
                        "rtt": res[2],
                        "icmp_seq": 1,
                        "loss": loss
                    }
                else:
                    table_structure[hostname]["status"].append(status)
                    table_structure[hostname]["time"] += res[1]
                    table_structure[hostname]["rtt"] += res[2]
                    table_structure[hostname]["icmp_seq"] += 1
                    table_structure[hostname]["loss"] += loss
                    table_structure[hostname]["status"] = table_structure[hostname]["status"][-STATUS_WIDTH:]
        except Exception as e:
            logging.error(f"Error processing queue: {e}")


def rich_table():
    if not table_structure:
        return 'Collecting data. Please wait...'
    table = Table(title="Hostwatcher", style='bold')
    table.add_column("Host", style="bold", justify='center')
    table.add_column("RTT AVG", style="bold", justify='center')
    table.add_column("TIME AVG", style="bold", justify='center')
    table.add_column("LOSS", style="bold", justify='center')
    table.add_column("SEQ", style="bold", justify='center')
    table.add_column("Status", style="bold", justify='left')
    for key, value in table_structure.items():
        if len(table_structure[key].values()) == 0:
            continue
        time_avg = round(float(table_structure[key]["time"]) / int(table_structure[key]["icmp_seq"]), 1)
        rtt_avg = round(float(table_structure[key]["rtt"]) / int(table_structure[key]["icmp_seq"]), 1)
        loss_prcnt = str(round((int(table_structure[key]["loss"]) * 100) / int(table_structure[key]["icmp_seq"]), 1))
        if float(loss_prcnt) >= LOSS_PERCENT_WARNING:
            loss_colored = f"[red]{loss_prcnt + '%'}[/red]"
        elif 0 < float(loss_prcnt) < LOSS_PERCENT_WARNING:
            loss_colored = f"[orange1]{loss_prcnt + '%'}[orange1]"
        else:
            loss_colored = f"[green]{loss_prcnt + '%'}[/green]"
        table.add_row(str(key),
                      str(rtt_avg) + 'ms',
                      str(time_avg) + 'ms',
                      loss_colored,
                      str(table_structure[key]["icmp_seq"]),
                      "".join(table_structure[key]["status"]))
    return table


def threading_ping(result_queue):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = [executor.submit(ping_cmd, host, result_queue) for host in hosts]
        for result in concurrent.futures.as_completed(results):
            result.result()


def threading_ping_process(result_queue):
    try:
        while True:
            threading_ping(result_queue)
    except KeyboardInterrupt:
        console.clear()
        logging.info("Ping process stopped by user")
        sys.exit(0)


def rich_live_update_process(result_queue):
    try:
        with Live(rich_table(), refresh_per_second=4) as live:
            while True:
                queue_to_dict(result_queue)
                live.update(rich_table())
    except KeyboardInterrupt:
        console.clear()
        logging.info("Live update process stopped by user")
        sys.exit(0)


def main():
    if '--multiprocess' in sys.argv:
        writer_process = multiprocessing.Process(target=threading_ping_process, args=(multiprocess_queue,))
        reader_process = multiprocessing.Process(target=rich_live_update_process, args=(multiprocess_queue,))

        writer_process.start()
        reader_process.start()

        try:
            writer_process.join()
            reader_process.join()
        except KeyboardInterrupt:
            console.clear()
            logging.info("Main process stopped by user")
            writer_process.terminate()
            reader_process.terminate()
            writer_process.join()
            reader_process.join()
    else:
        one_thread_queue = queue.Queue()
        with Live(rich_table()) as live:
            while True:
                threading_ping(one_thread_queue)
                queue_to_dict(one_thread_queue)
                live.update(rich_table())


if __name__ == '__main__':
    console.clear()
    date = datetime.datetime.now()
    console.print("Started at: " + date.strftime("%Y-%m-%d %H:%M:%S") + '\n')
    main()
