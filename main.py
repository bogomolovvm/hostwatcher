import concurrent.futures
import subprocess
import time
import queue
import platform
from rich.console import Console
from rich.table import Table

result_queue = queue.Queue()
hosts = ['google.com', 'example.com', 'localhost', 'yandex.com', 'habr.com', 'vk.com', 'eltex.loc', '3.3.3.3']

table_structure = {}
STATUS_WIDTH = 20
console = Console()


def get_operating_system():
    system = platform.system()
    if system == 'Windows':
        return 'Windows'
    elif system == 'Linux' or system == 'Darwin':
        return 'Unix'
    else:
        return 'Unknown'


def ping_cmd(host):
    system_name = get_operating_system()
    if system_name == 'Windows':
        result = subprocess.run(['ping', '-n', '1', '-w', '1', host],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
    else:
        result = subprocess.run(['ping', '-c', '1', '-W', '1', host],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
    result_queue.put({host: [result.returncode, 0, 0]})


def queue_to_dict():
    while not result_queue.empty():
        result = result_queue.get()
        for hostname, res in result.items():
            status = '✓' if res[0] == 0 else 'x'
            if hostname not in table_structure:
                table_structure[hostname] = status
            else:
                table_structure[hostname] = (table_structure[hostname][-(STATUS_WIDTH - 1):] + status)
        result_queue.task_done()


def rich_table():
    console.clear()
    table = Table(title="Hostwatcher")
    table.add_column("Host", style="magenta")
    table.add_column("Status", style="magenta")
    table.add_column("LEN", style="magenta")
    for key, value in table_structure.items():
        table.add_row(str(key), str(value), str(len(value)))
    console.print(table)


def parallel():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = [executor.submit(ping_cmd, host) for host in hosts]
        for result in concurrent.futures.as_completed(results):
            result.result()


def main():
    while True:
        parallel()
        queue_to_dict()
        rich_table()


if __name__ == '__main__':
    main()
