#!/usr/bin/env python3
import sys
import socket
import time
import threading
from timeit import default_timer as timer
import tkinter as tk
from tkinter import ttk

class TCPPingGUI(tk.Tk):
    def __init__(self, server_list, maxCount=1):
        super().__init__()
        self.title("Test Latency")  # Set the window title
        self.geometry("650x800")  # Set the window size
        
        # Initialize various lists to store the server data and widgets
        self.server_list = server_list
        self.maxCount = maxCount
        self.ip_vars = []
        self.port_vars = []
        self.description_labels = []
        self.latency_labels = []
        self.latency_colors = []
        self.retry_buttons = []
        self.latency_values = []
        self.sort_asc = True  # Flag for sorting order
        self.cancel_ping = False  # Flag to cancel ping operations
        
        self.setup_ui()  # Set up the user interface
    
    def setup_ui(self):
        """Sets up the user interface, including the layout and widgets."""
        self.frame = ttk.Frame(self)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas to allow scrolling
        self.canvas = tk.Canvas(self.frame)
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure the scrollable frame to adjust the canvas scroll region
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        # Add the scrollable frame to the canvas and configure scrolling
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Set up the header row with column labels
        header_frame = ttk.Frame(self.scrollable_frame)
        ttk.Label(header_frame, text="          Server Name", width=37).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(header_frame, text="IP Address", width=15).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(header_frame, text="Port", width=5).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Add buttons to sort the latency column
        latency_header_frame = ttk.Frame(header_frame)
        ttk.Label(latency_header_frame, text=" Latency", width=11).pack(side=tk.LEFT)
        
        up_button = ttk.Button(latency_header_frame, text="\u25B2", command=self.sort_latency_asc, width=4)
        up_button.pack(side=tk.LEFT)

        down_button = ttk.Button(latency_header_frame, text="\u25BC", command=self.sort_latency_desc, width=4)
        down_button.pack(side=tk.LEFT)

        latency_header_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        header_frame.pack(fill=tk.X, padx=5, pady=5)

        # Add a row for each server in the initial server list
        for server in self.server_list:
            self.add_server_row(server)
        
        # Create the frame at the bottom of the window for control buttons
        self.ping_all_frame = ttk.Frame(self)
        
        # Add a "Test All" button to start the pinging process
        self.ping_button = ttk.Button(self.ping_all_frame, text="Test All", command=self.ping_all_ips)
        self.ping_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Add a "Cancel" button to stop the pinging process
        self.cancel_button = ttk.Button(self.ping_all_frame, text="Cancel", command=self.cancel_ping_ips, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5, pady=10)

        # Add an "Exit" button to close the application
        self.exit_button = ttk.Button(self.ping_all_frame, text="Exit", command=self.quit)
        self.exit_button.pack(side=tk.RIGHT, padx=5, pady=10)  
              
        self.ping_all_frame.pack(pady=10)
    
    def add_server_row(self, server):
        """Adds a row in the UI for a given server."""
        description, ip, port = server
        ip_var = tk.StringVar(value=ip)
        port_var = tk.StringVar(value=str(port))
        self.ip_vars.append(ip_var)
        self.port_vars.append(port_var)
        
        # Create a frame for this server's row
        row_frame = ttk.Frame(self.scrollable_frame)
        
        # Add a delete button to remove this server row
        delete_button = ttk.Button(row_frame, text="X", width=2, command=lambda: self.delete_server_row(row_frame))
        delete_button.pack(side=tk.LEFT, padx=5, pady=2)

        # Add labels and entries for server description, IP, and port
        description_label = ttk.Label(row_frame, text=description, width=32)
        description_label.pack(side=tk.LEFT, padx=5, pady=2)
        self.description_labels.append(description_label)
        
        ip_entry = ttk.Entry(row_frame, textvariable=ip_var, width=15)
        ip_entry.pack(side=tk.LEFT, padx=5, pady=2)
        
        port_entry = ttk.Entry(row_frame, textvariable=port_var, width=5)
        port_entry.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Add a label for latency and a color indicator
        latency_label = ttk.Label(row_frame, text="N/A", width=11)
        latency_label.pack(side=tk.LEFT, padx=5, pady=2)
        self.latency_labels.append(latency_label)
        
        latency_color = tk.Label(row_frame, width=2, height=1)
        latency_color.pack(side=tk.LEFT, padx=5, pady=2)
        self.latency_colors.append(latency_color)
        
        # Add a retry button to ping this server again
        retry_button = ttk.Button(row_frame, text="Retry", command=lambda idx=len(self.retry_buttons): self.retry_ping(idx))
        retry_button.pack(side=tk.LEFT, padx=5, pady=2)
        self.retry_buttons.append(retry_button)
        
        row_frame.pack(fill=tk.X, padx=5, pady=2)
    
    def delete_server_row(self, row_frame):
        """Deletes a server row from the UI and updates the internal lists."""
        index = self.latency_labels.index(row_frame.winfo_children()[4])
        row_frame.destroy()  # Remove the row from the UI
        del self.ip_vars[index]
        del self.port_vars[index]
        del self.description_labels[index]
        del self.latency_labels[index]
        del self.latency_colors[index]
        del self.retry_buttons[index]
        
        # Update the indices in latency_values to reflect the removed row
        self.latency_values = [(latency, i) for latency, i in self.latency_values if i != index]
        self.latency_values = [(latency, i - 1 if i > index else i) for latency, i in self.latency_values]
    
    def ping_all_ips(self):
        """Initiates the process to ping all servers in the list."""
        self.ping_button.config(state=tk.DISABLED)  # Disable the "Test All" button
        self.cancel_button.config(state=tk.NORMAL)  # Enable the "Cancel" button
        self.cancel_ping = False
        self.latency_values.clear()  # Clear any previous latency data
        threading.Thread(target=self.ping_all_ips_sequentially).start()  # Run pinging in a separate thread
    
    def ping_all_ips_sequentially(self):
        """Pings each server one by one with a delay between each."""
        for i in range(len(self.ip_vars)):
            if self.cancel_ping:  # Check if pinging was cancelled
                break
            self.ping_ip(i)
            time.sleep(0.3)  # Add a short delay between each ping
        
        # Re-enable the "Test All" button after a delay
        self.after(4000, lambda: self.ping_button.config(state=tk.NORMAL))
        self.cancel_button.config(state=tk.DISABLED)  # Disable the "Cancel" button
    
    def cancel_ping_ips(self):
        """Cancels the ongoing ping operation."""
        self.cancel_ping = True
        self.cancel_button.config(state=tk.DISABLED)
    
    def retry_ping(self, index):
        """Retries pinging a specific server."""
        self.retry_buttons[index].config(state=tk.DISABLED)  # Disable the retry button temporarily
        threading.Thread(target=self.ping_ip, args=(index,)).start()
        self.after(2000, lambda: self.retry_buttons[index].config(state=tk.NORMAL))  # Re-enable the retry button
    
    def ping_ip(self, index):
        """Pings a specific server and updates the UI with the result."""
        host = self.ip_vars[index].get()
        port = int(self.port_vars[index].get())
        
        success = False
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s_start = timer()
        
        try:
            s.connect((host, port))
            s.shutdown(socket.SHUT_RD)
            success = True
        except (socket.timeout, OSError):
            pass
        
        s_stop = timer()
        s_runtime = "%.2f" % (1000 * (s_stop - s_start))
        
        latency_text = f"{s_runtime} ms" if success else "Failed"
        self.latency_labels[index].config(text=latency_text)
        
        if success:
            latency = float(s_runtime)
            self.latency_values.append((latency, index))  # Store latency and index for sorting
            # Update the color based on latency
            if latency < 100:
                self.latency_colors[index].config(bg='lime')
            elif latency < 200:
                self.latency_colors[index].config(bg='green')
            elif latency < 300:
                self.latency_colors[index].config(bg='orange')
            else:
                self.latency_colors[index].config(bg='red')
        else:
            self.latency_colors[index].config(bg='darkgray')  # Mark as failed with dark gray
        
        time.sleep(1)
    
    def sort_latency_asc(self):
        """Sorts the servers by latency in ascending order."""
        self.latency_values.sort()
        self.sort_asc = True
        self.update_sorted_latency()
    
    def sort_latency_desc(self):
        """Sorts the servers by latency in descending order."""
        self.latency_values.sort(reverse=True)
        self.sort_asc = False
        self.update_sorted_latency()
    
    def update_sorted_latency(self):
        """Updates the UI to reflect the sorted order."""
        for latency, index in self.latency_values:
            if index < len(self.latency_labels):
                row = self.latency_labels[index].master
                row.pack_forget()  # Remove the row temporarily
                row.pack(fill=tk.X, padx=5, pady=2)  # Re-pack the row in the new order

if __name__ == "__main__":
    # List of servers with descriptions, IP addresses, and ports
    servers = [
        ("|oraladder.net| Competitive 1v1 Ladder Server 1", "185.170.114.56", 10301),
        ("000 - ORAServer.co.uk 02", "51.38.81.218", 1235),
        ("0 | GB | Just an OpenRA Server - 1", "198.244.233.123", 1234),
        ("EU -CH - JustSomeServer 01", "195.15.242.160", 12201),
        ("EU -DE - Lumpies-Server", "93.130.228.70", 1234),
        ("AMP Powered OpenRA Server", "103.195.102.234", 2226),
        ("AMP Powered OpenRA Red Alert Server HALHAN Germany", "109.199.102.236", 1234),
        ("AUS/BRIS BGS Red Alert", "117.20.64.204", 1234),
        ("AU-PrawnTown-RedAlert", "106.71.97.159", 1234),
        ("Blue Firestick | RA Public 1", "54.36.165.167", 14001),
        ("codecapi.nl | EU | NL", "152.70.51.164", 1234),
        ("Commander's Game", "109.168.173.234", 1234),
        ("Donita-Dunes", "72.77.28.14", 1234),
        ("DUS1", "45.11.248.201", 1234),
        ("EU - DE - Official 05", "94.130.38.140", 3004),
        ("FoAZ Public Red Alert Server (Australia)", "167.114.209.31", 1236),
        ("Gamecom Red Alert", "93.174.188.115", 1234),
        ("|=GOD=| Spielwiese III erstellt mit NixOS", "49.12.218.209", 1236),
        ("LAF Lounge", "38.172.90.247", 1234),
        ("LegoLan", "161.97.98.249", 5500),
        ("L.A.I.N.O. Red Alert", "185.11.80.134", 1201),
        ("MMS Public Server (0et)", "192.145.58.53", 1237),
        ("OpenRA - Amarillo", "70.233.5.234", 2228),
        ("Reichs-Server 01", "80.82.215.108", 1488),
        ("Some OpenRA Server 8)", "88.214.57.222", 27100),
        ("WLG-NZ | Mobi Munchers Public | Hosted with love by Mobi", "210.79.184.48", 50001),
        ("Xorp Game Server", "78.131.12.254", 1234),
        ("Zero Evolution Server 01", "213.171.210.213", 1234),
        ("Zero Gravity Server 01", "185.132.39.160", 1234),
        ("Zero Hour Server 01", "77.68.87.57", 1234),
        ("|Skyrider.me| Red Alert (DE)", "138.201.32.219", 26000),
        ("|| ChimoTeam RA | (CA-QC-1)", "155.248.237.137", 1234)
    ]
    app = TCPPingGUI(servers)  # Create the application instance with the server list
    app.mainloop()  # Start the Tkinter main loop

'''
Explanation of the Program:
Initialization: The __init__ method sets up the initial configuration and calls setup_ui() to create the user interface.

setup_ui: This method creates the main frame, a scrollable canvas, and adds the header labels and initial rows for each server.

add_server_row: Adds a new row to the interface for each server, including delete buttons, text fields for IP and port, and buttons for retrying the ping.

delete_server_row: Removes a row and updates the internal data structures to keep indices consistent.

ping_all_ips: Starts the ping process for all servers. It runs in a separate thread to keep the GUI responsive.

ping_ip: Pings a specific server and updates the latency label and color indicator. This uses tcpping by yantisj.

sort_latency_asc/desc: Sorts the rows by latency either in ascending or descending order.

update_sorted_latency: Rearranges the rows in the UI based on the sorted latency values.

'''