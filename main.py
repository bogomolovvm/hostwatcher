from pythonping import ping

data_structure = {
    "host": "",
    "result": "",
    "packet_loss": "",
    "rtt": "" 
}

def check_host(host_address: str, verbose=False, timeout=1, payload="TestString"):
    try:
        request = ping(host_address, verbose=verbose, timeout=timeout, payload=payload, count=1)
        return request.stats_packets_lost, request.rtt_avg_ms
    except Exception as e:
        return False


if __name__ == '__main__':
    test = check_host("192.168.1.1")    
    print(test)