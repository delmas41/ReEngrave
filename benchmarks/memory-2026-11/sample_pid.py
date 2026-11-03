"""Sample one process's memory from OUTSIDE it (ROADMAP 2.249; reads only).

usage: sample_pid.py PID OUT.tsv [--every 10] [--stop-gb 56]

Every N seconds: elapsed, RSS, phys_footprint (what macOS counts against the machine: resident + compressed, the number
Activity Monitor shows), the machine's swap used. Ends when the process ends; with --stop-gb, sends SIGTERM to PID (and
says so) if its footprint passes that many GB -- a run that would swap the 64 GB box is stopped, not left to thrash.
"""
import sys, time, ctypes, os, signal, subprocess, argparse

ap = argparse.ArgumentParser()
ap.add_argument("pid", type=int); ap.add_argument("out")
ap.add_argument("--every", type=float, default=10.0); ap.add_argument("--stop-gb", type=float, default=0.0)
a = ap.parse_args()
lib = ctypes.CDLL("/usr/lib/libproc.dylib")


class RU(ctypes.Structure):     # rusage_info_v2, enough of it to reach ri_phys_footprint
    _fields_ = [("uuid", ctypes.c_uint8 * 16), ("user_time", ctypes.c_uint64), ("system_time", ctypes.c_uint64),
                ("pkg_idle_wkups", ctypes.c_uint64), ("interrupt_wkups", ctypes.c_uint64), ("pageins", ctypes.c_uint64),
                ("wired_size", ctypes.c_uint64), ("resident_size", ctypes.c_uint64), ("phys_footprint", ctypes.c_uint64),
                ("rest", ctypes.c_uint64 * 32)]


def sample(pid):
    ru = RU()
    if lib.proc_pid_rusage(pid, 2, ctypes.byref(ru)) != 0:
        return None
    return ru.resident_size, ru.phys_footprint


def swap_used_gb():
    try:
        s = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
        used = s.split("used =")[1].split()[0]
        return float(used.rstrip("M")) / 1024 if used.endswith("M") else float(used.rstrip("G"))
    except Exception:
        return -1.0


t0 = time.time(); peak = 0
with open(a.out, "w") as fh:
    fh.write("t_s\trss_gb\tfootprint_gb\tswap_used_gb\n")
    while True:
        r = sample(a.pid)
        if r is None:
            break
        peak = max(peak, r[1])
        fh.write(f"{time.time() - t0:.0f}\t{r[0] / 1e9:.2f}\t{r[1] / 1e9:.2f}\t{swap_used_gb():.2f}\n"); fh.flush()
        if a.stop_gb and r[1] / 1e9 > a.stop_gb:
            fh.write(f"# footprint {r[1] / 1e9:.1f} GB > {a.stop_gb} GB: SIGTERM sent\n"); fh.flush()
            os.kill(a.pid, signal.SIGTERM)
            break
        time.sleep(a.every)
    fh.write(f"# end; peak footprint {peak / 1e9:.2f} GB\n")
