import tkinter as tk
import threading
import subprocess
import time
import webbrowser
import socket
import sys
import os


NOTEBOOKS = [
    ("001_All_Types.ipynb",          8866),
    ("002_Data_export.ipynb",        8867),
    ("003_VMNED_Data_Export.ipynb",  8869),
    ("004_Factorupdate.ipynb",       8870),
    ("005_MV_Switch.ipynb",          8871),
    ("006_Vervanging_Tool.ipynb",    8872),
    ("007_Storage_Method.ipynb",    8873),
    ("000_Start_UI.ipynb",           8868) # main UI
]

MAIN_UI_PORT     = 8868
MAIN_UI_NOTEBOOK = "000_Start_UI.ipynb"

def is_port_open(host, port, timeout=1):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0

def launch_notebook(notebook, port):
    cmd = [
        "voila",
        notebook,
        f"--port={port}",
        "--no-browser",
        "--ip=127.0.0.1"
    ]
    print(f"[INFO] Launching {notebook} on port {port} with: {' '.join(cmd)}")
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )

def start_servers_and_wait(update_label):
    for nb, port in NOTEBOOKS:
        if not os.path.isfile(nb):
            msg = f"[ERROR] Notebook '{nb}' not found in {os.getcwd()}."
            print(msg)
            update_label(msg)
            return

    processes = []
    for nb, port in NOTEBOOKS:
        update_label(f"Launching {nb} on port {port}...")
        proc = launch_notebook(nb, port)
        processes.append(proc)
        time.sleep(0.5)

    update_label(f"Waiting for {MAIN_UI_NOTEBOOK} on port {MAIN_UI_PORT}...")
    while not is_port_open("127.0.0.1", MAIN_UI_PORT):
        time.sleep(2)

    update_label("Application is ready! Opening your browser...")
    webbrowser.open(f"http://127.0.0.1:{MAIN_UI_PORT}")

    update_label("All notebooks are running. Close this window to exit.")
    while True:
        if not any(p.poll() is None for p in processes):
            update_label("One or more notebooks have exited; shutting down...")
            break
        time.sleep(2)

def main():
    root = tk.Tk()
    root.title("EnergyMonitor Launcher")
    root.geometry("480x200")
    root.resizable(False, False)

    status_label = tk.Label(root, text="Initializing...", font=("Arial", 12))
    status_label.pack(pady=40)

    def update_label(msg):
        status_label.config(text=msg)
        print(msg)

    thread = threading.Thread(target=start_servers_and_wait, args=(update_label,))
    thread.start()

    def on_closing():
        update_label("Shutting down application processes...")
        root.destroy()
        sys.exit(0)

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
