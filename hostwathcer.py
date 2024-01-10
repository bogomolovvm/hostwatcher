import concurrent.futures
import subprocess
import time
import queue
import platform
import json
import re
import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.pretty import pprint
import multiprocessing
import sys


try:
    with open("config.json") as file:
        CFG = json.load(file)
except Exception as e:
    print(e)

table_structure = {}
multiprocess_queue = multiprocessing.Queue()


hosts = CFG["hosts"]
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
        result = subprocess.run(['ping', '-n', '1', '-w', '500', host],
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
    if time_match:
        time = time_match.group(1)
    else:
        time = 0
    if rtt_match:
        rtt = rtt_match.group(1)
    else:
        rtt = 0
    result_queue.put({host: [result.returncode, float(time), float(rtt)]})


def queue_to_dict(result_queue):
    while not result_queue.empty():
        result = result_queue.get()
        for hostname, res in result.items():
            if res[0] == 0:
                status = f"[green]{SUCCESS_CHAR}[/green]"
                loss = 0
            else:
                status = f"[red]{FAILED_CHAR}[/red]"
                loss = 1
            if hostname not in table_structure:
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
        time_avg = round(float(table_structure[key]["time"]) / int(table_structure[key]["icmp_seq"]), 1)
        rtt_avg = round(float(table_structure[key]["rtt"]) / int(table_structure[key]["icmp_seq"]), 1)
        loss_prcnt = str(round((int(table_structure[key]["loss"]) * 100) / int(table_structure[key]["icmp_seq"]), 1))
        loss_colored = f"[green]{loss_prcnt + '%'}[/green]" if float(
            loss_prcnt) < LOSS_PERCENT_WARNING else f"[red]{loss_prcnt + '%'}[/red]"
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
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = [executor.submit(ping_cmd, host, result_queue) for host in hosts]
                for result in concurrent.futures.as_completed(results):
                    result.result()
    except KeyboardInterrupt:
        console.clear()
        console.print("[red]The program has been stopped[/red]")
        exit(1)

            
def rich_live_update_process(result_queue):
    try:
        with Live(rich_table(), refresh_per_second=100) as live:
            while True:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future1 = executor.submit(queue_to_dict, result_queue)
                    future2 = executor.submit(live.update,rich_table())
                    concurrent.futures.wait([future1, future2])
    except KeyboardInterrupt:
        console.clear()
        console.print("[red]The program has been stopped[/red]")
        exit(1)


def main():
    if '--multiprocess' in sys.argv:
        writer_process = multiprocessing.Process(target=threading_ping_process, args=(multiprocess_queue,))
        reader_process = multiprocessing.Process(target=rich_live_update_process, args=(multiprocess_queue,))

        writer_process.start()
        reader_process.start()

        writer_process.join()
        reader_process.join()
    else:
        one_thread_queue = queue.Queue()
        with Live(rich_table(), refresh_per_second=100) as live:
            while True:
                threading_ping(one_thread_queue)
                queue_to_dict(one_thread_queue)
                live.update(rich_table())


if __name__ == '__main__':
    console.clear()
    date = datetime.datetime.now()
    console.print("Started at: " + date.strftime("%Y-%m-%d %H:%M:%S") + '\n')
    main()
