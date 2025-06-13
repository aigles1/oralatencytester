#!/usr/bin/env python3
import sys
import socket
import time
import threading
from timeit import default_timer as timer
import tkinter as tk
from tkinter import ttk, Menu
import requests

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

        self.filter_remove_started = False  # New: Filtering flag

        self.setup_ui()  # Set up the user interface

    def setup_ui(self):
        """Sets up the user interface, including the layout and widgets."""
        self.create_menu()  # Create the File and Filter menus

        self.frame = ttk.Frame(self)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas to allow scrolling
        self.canvas = tk.Canvas(self.frame)
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add header row (will be kept and redrawn as needed)
        self.header_frame = None
        self.draw_headers()

        self.populate_server_rows()
        
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

        # Bind mousewheel scrolling for Windows and macOS/Linux
        self.bind_mousewheel()

    def bind_mousewheel(self):
        """Binds mousewheel scrolling to the canvas."""
        def _on_mousewheel(event):
            direction = 1 if event.num == 5 or event.delta < 0 else -1
            self.canvas.yview_scroll(direction, "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows/macOS
        self.canvas.bind_all("<Button-4>", _on_mousewheel)    # Linux scroll up
        self.canvas.bind_all("<Button-5>", _on_mousewheel)    # Linux scroll down

    def create_menu(self):
        """Creates a File menu with a Refresh option, and a Filter menu."""
        menu_bar = Menu(self)
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Refresh", command=self.refresh_server_list)
        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        # --- Filter menu and Remove In Progress Games item ---
        filter_menu = Menu(menu_bar, tearoff=0)
        # Checkbutton for filter, calls self.toggle_remove_started
        filter_menu.add_checkbutton(label="Remove In Progress Games", 
                                    onvalue=True, offvalue=False,
                                    variable=tk.BooleanVar(value=False),
                                    command=self.toggle_remove_started)
        self.filter_menu = filter_menu  # Save reference if we want to update it later
        menu_bar.add_cascade(label="Filter", menu=filter_menu)
        self.config(menu=menu_bar)

    def draw_headers(self):
        """Draws the header row and sort buttons."""
        # Remove existing header if any
        if self.header_frame:
            self.header_frame.destroy()
        self.header_frame = ttk.Frame(self.scrollable_frame)
        ttk.Label(self.header_frame, text="          Server Name", width=37).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(self.header_frame, text="IP Address", width=15).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(self.header_frame, text="Port", width=5).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Add buttons to sort the latency column
        latency_header_frame = ttk.Frame(self.header_frame)
        ttk.Label(latency_header_frame, text=" Latency", width=11).pack(side=tk.LEFT)
        
        up_button = ttk.Button(latency_header_frame, text="\u25B2", command=self.sort_latency_asc, width=4)
        up_button.pack(side=tk.LEFT)

        down_button = ttk.Button(latency_header_frame, text="\u25BC", command=self.sort_latency_desc, width=4)
        down_button.pack(side=tk.LEFT)

        latency_header_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.header_frame.pack(fill=tk.X, padx=5, pady=5)

    def populate_server_rows(self):
        """Populates rows for all servers in the current server list."""
        for server in self.server_list:
            self.add_server_row(server)

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
        self.retry_buttons[index].config(state=tk.DISABLED)
        threading.Thread(target=self.ping_ip, args=(index,)).start()
        self.after(2000, lambda: self.retry_buttons[index].config(state=tk.NORMAL))

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
        """Reorders the server rows based on the sorted latency."""
        # Build a new order based on the sorted latency_values
        sorted_indices = [i for _, i in self.latency_values]
        if not sorted_indices:
            return
        # Collect all row frames
        row_frames = [desc_label.master for desc_label in self.description_labels]
        # Detach all rows
        for frame in row_frames:
            frame.pack_forget()
        # Repack in sorted order after header
        for idx in sorted_indices:
            row_frames[idx].pack(fill=tk.X, padx=5, pady=2)
        # Repack any unsorted rows (still at end)
        for i, frame in enumerate(row_frames):
            if i not in sorted_indices:
                frame.pack(fill=tk.X, padx=5, pady=2)

    def add_server_row(self, server):
        description, ip, port = server
        ip_var = tk.StringVar(value=ip)
        port_var = tk.StringVar(value=str(port))
        self.ip_vars.append(ip_var)
        self.port_vars.append(port_var)

        row_frame = ttk.Frame(self.scrollable_frame)

        delete_button = ttk.Button(row_frame, text="X", width=2, command=lambda: self.delete_server_row(row_frame))
        delete_button.pack(side=tk.LEFT, padx=5, pady=2)

        description_label = ttk.Label(row_frame, text=description, width=32)
        description_label.pack(side=tk.LEFT, padx=5, pady=2)
        self.description_labels.append(description_label)

        ip_entry = ttk.Entry(row_frame, textvariable=ip_var, width=15)
        ip_entry.pack(side=tk.LEFT, padx=5, pady=2)

        port_entry = ttk.Entry(row_frame, textvariable=port_var, width=5)
        port_entry.pack(side=tk.LEFT, padx=5, pady=2)

        latency_label = ttk.Label(row_frame, text="N/A", width=11)
        latency_label.pack(side=tk.LEFT, padx=5, pady=2)
        self.latency_labels.append(latency_label)

        latency_color = tk.Label(row_frame, width=2, height=1)
        latency_color.pack(side=tk.LEFT, padx=5, pady=2)
        self.latency_colors.append(latency_color)

        # Retry button now looks up the current index at click time
        retry_button = ttk.Button(
            row_frame,
            text="Retry",
            command=lambda lbl=description_label: self.retry_ping(self.description_labels.index(lbl))
        )
        retry_button.pack(side=tk.LEFT, padx=5, pady=2)
        self.retry_buttons.append(retry_button)

        row_frame.pack(fill=tk.X, padx=5, pady=2)

    def refresh_server_list(self):
        """Fetches the latest server list and updates the UI, keeping headers and filter state."""
        print("Refreshing server list...")
        servers = self.fetch_red_alert_servers()
        if servers:
            print(f"Fetched {len(servers)} servers.")
            # Remove all widgets except the header
            for child in self.scrollable_frame.winfo_children():
                if child != self.header_frame:
                    child.destroy()
            self.server_list = servers  # Update the server list
            self.ip_vars.clear()
            self.port_vars.clear()
            self.description_labels.clear()
            self.latency_labels.clear()
            self.latency_colors.clear()
            self.retry_buttons.clear()
            self.latency_values.clear()
            # Redraw header (to ensure it's always present)
            self.draw_headers()
            self.populate_server_rows()
        else:
            print("No servers to display. Refresh failed or returned no data.")

    def toggle_remove_started(self):
        """Toggles the filter for removing in-progress games and refreshes."""
        self.filter_remove_started = not self.filter_remove_started
        self.refresh_server_list()

    def fetch_red_alert_servers(self):
        """Fetches the list of servers from the OpenRA master server, applying filter settings."""
        url = 'https://master.openra.net/games?protocol=2&type=json'
        print(f"Fetching server list from {url}...")
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
        except requests.RequestException as e:
            print(f"Failed to retrieve data from the server: {e}")
            return []

        games = response.json()  # 'games' is a list of game dictionaries
        seen_ips = set()
        server_info = []

        for game in games:
            mod_title = game.get('modtitle', '')
            version = game.get('version', '')
            name = game.get('name', '')
            address_str = game.get('address', '')
            protected = game.get('protected', False)
            started = game.get('started', False)

            # Only process games that match the specified criteria
            if mod_title == "Red Alert" and version == "release-20250330" and not protected and address_str:
                # Filter out started games if filter is enabled
                if self.filter_remove_started and started:
                    continue
                try:
                    ip, port = address_str.split(':')
                    port = int(port)
                except ValueError:
                    continue

                if ip not in seen_ips:
                    seen_ips.add(ip)
                    formatted_name = f"{name}"
                    server_info.append((formatted_name, ip, port))

        return server_info

if __name__ == "__main__":
    servers = [
        ("|oraladder.net| Competitive 1v1 Ladder Server 1", "185.170.114.56", 10301),
        ("| = genesys-technology.com = | - US - DET - Unofficial 01", "69.41.8.140", 1234)
    ]
    app = TCPPingGUI(servers)  # Create the application instance with the server list
    app.mainloop()  # Start the Tkinter main loop