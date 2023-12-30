import concurrent.futures
import subprocess
import time
import queue
import platform
from rich.console import Console
from rich.table import Table
from rich.live import Live

result_queue = queue.Queue()
hosts = [
    "google.com",
    "youtube.com",
    "facebook.com",
    "amazon.com",
    "yahoo.com",
    "wikipedia.org",
    "twitter.com",
    "instagram.com",
    "linkedin.com",
    "netflix.com",
    "ebay.com",
    "reddit.com",
    "pinterest.com",
    "tumblr.com",
    "microsoft.com",
    "apple.com",
    "cnn.com",
    "bbc.co.uk",
    "nytimes.com",
    "huffpost.com",
    "foxnews.com",
    "theguardian.com",
    "forbes.com",
    "bloomberg.com",
    "wsj.com",
    "weather.com",
    "espn.com",
    "nba.com",
    "nfl.com",
    "mlb.com",
    "nhl.com",
    "imdb.com",
    "etsy.com",
    "tripadvisor.com",
    "booking.com",
    "airbnb.com",
    "expedia.com",
    "kayak.com"
]
table_structure = {}
STATUS_WIDTH = 20
console = Console(color_system="truecolor")


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
        result = subprocess.run(['ping', '-n', '1', '-w', '500', host],
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
            status =f"[green]{'▅'}[/green]" if res[0] == 0 else f"[red]{'▁'}[/red]"
            if hostname not in table_structure:
                table_structure[hostname] = list()
                table_structure[hostname].append(status)
            else:
                table_structure[hostname].append(status)
                table_structure[hostname] = table_structure[hostname][-STATUS_WIDTH:]
        result_queue.task_done()


def rich_table():
    console.clear()
    table = Table(title="Hostwatcher", style='bold')
    table.add_column("Host", style="bold", justify='center')
    table.add_column("Status", style="bold", justify='left')
    for key, value in table_structure.items():
            table.add_row(str(key), "".join(value))
    console.print(table)


def parallel():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = [executor.submit(ping_cmd, host) for host in hosts]
        for result in concurrent.futures.as_completed(results):
            result.result()


def main():
    console.clear()
    console.print('Collecting data. Please wait...')
    while True:
        parallel()
        queue_to_dict()
        rich_table()


if __name__ == '__main__':
    main()
