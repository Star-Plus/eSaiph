import psutil

def get_cpu_usage(pid: int) -> float:
    p = psutil.Process(pid)
    return p.cpu_percent(interval=1)

def get_memory_usage(pid: int) -> float:
    p = psutil.Process(pid)
    mem_info = p.memory_info()
    return mem_info.rss / (1024 * 1024)