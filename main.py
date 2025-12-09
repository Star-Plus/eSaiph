from resource_monitor import get_cpu_usage, get_memory_usage
import time

if __name__ == "__main__":

    while True:
        cpu_usage = get_cpu_usage(3434)
        print(f"CPU usage for PID 3434: {cpu_usage}%")
        mem_usage = get_memory_usage(3434)
        print(f"Memory usage for PID 3434: {mem_usage} MB")
        time.sleep(5)
        