import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial
import serial.tools.list_ports
import threading
import queue
import csv
import math
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

STYLE_CONFIG = {
    "font_normal": ("Calibri", 10),
    "font_bold": ("Calibri", 10, "bold"),
    "font_large_display": ("Consolas", 28, "bold"),
    "font_timer_display": ("Consolas", 48, "bold"),
    "bg_color": "#F0F0F0",
    "red_button": "#E62E2D",
    "green_button": "#4CAF50",
}

class RMCSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("1920x1080")
        self.configure(bg=STYLE_CONFIG["bg_color"])

        self.serial_port = None
        self.serial_thread = None
        self.data_queue = queue.Queue()
        self.is_connected = False
        self.is_running = False
        self.last_manual_electrodes = {'A': None, 'B': None, 'M': None, 'N': None}
        self.countdown_job = None
        self.manual_measurement_active = False

        self.measurement_sequence = []
        self.current_step = 0
        self.base_spacing = 1.0
        self.plot_data_x = []
        self.plot_data_y = []
        
        self.project_name = f"RMCS_Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.config_var = tk.StringVar(value="Wenner")
        self.mode_var = tk.StringVar(value="Otomatis")

        self._create_main_layout()
        self._create_all_widgets()
        self.populate_com_ports()

        self.mode_var.trace_add("write", self.toggle_mode)
        self.config_var.trace_add("write", self.update_title)
        
        self.toggle_mode()
        self.update_title()

        self.process_serial_queue()

    def _create_main_layout(self):
        self.grid_columnconfigure(0, weight=1, uniform="group1")
        self.grid_columnconfigure(1, weight=3, uniform="group1")
        self.grid_rowconfigure(0, weight=1)

        self.left_panel = ttk.Frame(self, padding=10)
        self.left_panel.grid(row=0, column=0, sticky="nsew")
        self.left_panel.rowconfigure(3, weight=1)

        self.notebook = ttk.Notebook(self, padding=10)
        self.notebook.grid(row=0, column=1, sticky="nsew")

    def _create_all_widgets(self):
        self._create_comms_frame()
        self._create_measurement_frame()
        self._create_timer_frame()
        self._create_electrode_control_frame()
        self._create_progress_frame()
        self._create_data_tab()
        self._create_plot_tab()
        self._create_export_tab()

    def _create_comms_frame(self):
        frame = ttk.LabelFrame(self.left_panel, text="Communication", padding=10)
        frame.pack(fill="x", pady=5)
        ttk.Label(frame, text="COM:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.com_port_combo = ttk.Combobox(frame, state="readonly", width=12)
        self.com_port_combo.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(frame, text="Baudrate:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.baud_rate_combo = ttk.Combobox(frame, values=["9600", "19200", "57600", "115200"], width=12)
        self.baud_rate_combo.set("9600")
        self.baud_rate_combo.grid(row=1, column=1, padx=5, pady=2)
        self.connect_button = ttk.Button(frame, text="Connect", command=self.toggle_connection, width=10)
        self.connect_button.grid(row=2, column=0, pady=10, padx=5)
        self.status_label = ttk.Label(frame, text="Not ready", foreground="red", font=STYLE_CONFIG["font_bold"])
        self.status_label.grid(row=2, column=1, pady=10, padx=5)

    def _create_measurement_frame(self):
        frame = ttk.LabelFrame(self.left_panel, text="Measurement", padding=10)
        frame.pack(fill="x", pady=5)
        
        self.radio_schlum = ttk.Radiobutton(frame, text="Schlumberger", variable=self.config_var, value="Schlumberger", 
                                          command=lambda: self.on_config_change("Schlumberger"))
        self.radio_schlum.pack(anchor="w")
        
        self.radio_wenner = ttk.Radiobutton(frame, text="Wenner", variable=self.config_var, value="Wenner",
                                          command=lambda: self.on_config_change("Wenner"))
        self.radio_wenner.pack(anchor="w")
        
        self.radio_dipole = ttk.Radiobutton(frame, text="Dipole-dipole", variable=self.config_var, value="Dipole-dipole",
                                          command=lambda: self.on_config_change("Dipole-dipole"))
        self.radio_dipole.pack(anchor="w")
        
        self.start_button = ttk.Button(frame, text="START MEASUREMENT (AUTO)", command=self.start_measurement_sequence, style="Accent.TButton")
        self.start_button.pack(fill="x", pady=10)
        
    def _create_timer_frame(self):
        frame = ttk.LabelFrame(self.left_panel, text="MEA. TIMER", padding=10)
        frame.pack(fill="both", expand=True, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        input_frame = ttk.Frame(frame)
        input_frame.grid(row=0, column=0, sticky="ew")
        ttk.Label(input_frame, text="Timer (s):").pack(side="left", padx=5)
        self.timer_spinbox = ttk.Spinbox(input_frame, from_=1, to=60, width=5, font=STYLE_CONFIG["font_normal"])
        self.timer_spinbox.set("5")
        self.timer_spinbox.pack(side="left", padx=5)
        self.countdown_label = ttk.Label(frame, text="0", font=STYLE_CONFIG["font_timer_display"], foreground="grey")
        self.countdown_label.grid(row=1, column=0, sticky="nsew")

    def _create_electrode_control_frame(self):
        frame = ttk.LabelFrame(self.left_panel, text="Electrode Control", padding=10)
        frame.pack(fill="x", pady=5)
        mode_frame = ttk.Frame(frame)
        mode_frame.pack(fill="x", pady=(0, 10))
        
        self.radio_auto = ttk.Radiobutton(mode_frame, text="Mode Otomatis", variable=self.mode_var, value="Otomatis",
                                        command=lambda: self.on_mode_change("Otomatis"))
        self.radio_auto.pack(side="left", padx=5)
        
        self.radio_manual = ttk.Radiobutton(mode_frame, text="Mode Manual", variable=self.mode_var, value="Manual",
                                          command=lambda: self.on_mode_change("Manual"))
        self.radio_manual.pack(side="left", padx=5)
        
        self.widget_container = ttk.Frame(frame)
        self.widget_container.pack(fill="x")
        self.widget_container.grid_rowconfigure(0, weight=1)
        self.widget_container.grid_columnconfigure(0, weight=1)
        self.auto_mode_frame = ttk.Frame(self.widget_container)
        self.a_label = ttk.Label(self.auto_mode_frame, text="A0", font=STYLE_CONFIG["font_large_display"], foreground="#D32F2F")
        self.b_label = ttk.Label(self.auto_mode_frame, text="B0", font=STYLE_CONFIG["font_large_display"], foreground="#D32F2F")
        self.m_label = ttk.Label(self.auto_mode_frame, text="M0", font=STYLE_CONFIG["font_large_display"], foreground="#1976D2")
        self.n_label = ttk.Label(self.auto_mode_frame, text="N0", font=STYLE_CONFIG["font_large_display"], foreground="#1976D2")
        self.a_label.grid(row=0, column=0, padx=20, pady=5); self.b_label.grid(row=0, column=1, padx=20, pady=5)
        self.m_label.grid(row=1, column=0, padx=20, pady=5); self.n_label.grid(row=1, column=1, padx=20, pady=5)
        self.auto_mode_frame.grid(row=0, column=0, sticky="nsew")
        self.manual_mode_frame = ttk.Frame(self.widget_container)
        
        ttk.Label(self.manual_mode_frame, text="A:").grid(row=0, column=0, padx=5, pady=5)
        self.a_entry = ttk.Spinbox(self.manual_mode_frame, from_=1, to=64, width=5); self.a_entry.grid(row=0, column=1)
        ttk.Label(self.manual_mode_frame, text="B:").grid(row=0, column=2, padx=5, pady=5)
        self.b_entry = ttk.Spinbox(self.manual_mode_frame, from_=1, to=64, width=5); self.b_entry.grid(row=0, column=3)
        ttk.Label(self.manual_mode_frame, text="M:").grid(row=1, column=0, padx=5, pady=5)
        self.m_entry = ttk.Spinbox(self.manual_mode_frame, from_=1, to=64, width=5); self.m_entry.grid(row=1, column=1)
        ttk.Label(self.manual_mode_frame, text="N:").grid(row=1, column=2, padx=5, pady=5)
        self.n_entry = ttk.Spinbox(self.manual_mode_frame, from_=1, to=64, width=5); self.n_entry.grid(row=1, column=3)
        
        ttk.Label(self.manual_mode_frame, text="Command:", font=STYLE_CONFIG["font_bold"]).grid(row=2, column=0, columnspan=4, pady=(10,5), sticky="w")
        self.manual_cmd_label = ttk.Label(self.manual_mode_frame, text="No command", font=STYLE_CONFIG["font_normal"], foreground="grey")
        self.manual_cmd_label.grid(row=3, column=0, columnspan=4, pady=5, sticky="w")
        
        manual_button_frame = ttk.Frame(self.manual_mode_frame)
        manual_button_frame.grid(row=4, column=0, columnspan=4, pady=10, sticky="ew")
        manual_button_frame.grid_columnconfigure(0, weight=1)
        manual_button_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Button(manual_button_frame, text="SEND & MEASURE", command=self.send_manual_measurement, style="Accent.TButton").grid(row=0, column=0, padx=2, sticky="ew")
        ttk.Button(manual_button_frame, text="STOP MANUAL", command=self.stop_manual_measurement, style="Red.TButton").grid(row=0, column=1, padx=2, sticky="ew")
        
        self.manual_mode_frame.grid(row=0, column=0, sticky="nsew")

    def _create_progress_frame(self):
        frame = ttk.LabelFrame(self.left_panel, text="MEA. PROGRESS", padding=10)
        frame.pack(fill="x", pady=5, side="bottom")
        self.progress_bar = ttk.Progressbar(frame, orient="horizontal", length=200, mode="determinate")
        self.progress_bar.pack(fill="x", expand=True, pady=5)
        self.reset_button = ttk.Button(frame, text="RESET SYSTEM", command=self.reset_all, style="Red.TButton")
        self.reset_button.pack(fill="x", pady=5)

    def _create_data_tab(self):
        data_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(data_frame, text="Data Table & Project")
        data_frame.grid_rowconfigure(1, weight=1)
        data_frame.grid_columnconfigure(0, weight=1)
        cmd_frame = ttk.LabelFrame(data_frame, text="Project & Command Setting", padding=10)
        cmd_frame.grid(row=0, column=0, sticky="ew", pady=5)
        cmd_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(cmd_frame, text="Project Name:").grid(row=0, column=0, padx=5, sticky="w")
        self.project_name_entry = ttk.Entry(cmd_frame, width=50)
        self.project_name_entry.insert(0, self.project_name)
        self.project_name_entry.grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(cmd_frame, text="Update", command=self.update_project_name).grid(row=0, column=2, padx=5)
        ttk.Label(cmd_frame, text="Cmd File:").grid(row=1, column=0, padx=5, sticky="w")
        self.file_path_entry = ttk.Entry(cmd_frame, width=50)
        self.file_path_entry.grid(row=1, column=1, padx=5, sticky="ew")
        ttk.Button(cmd_frame, text="Browse...", command=self.browse_file).grid(row=1, column=2, padx=5)
        ttk.Button(cmd_frame, text="Load CMD", command=self.load_cmd_file).grid(row=1, column=3, padx=5)
        table_frame = ttk.Frame(data_frame)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        columns = ("no", "a", "b", "m", "n", "curr", "volt", "res", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        col_map = {"no": "No", "a": "A", "b": "B", "m": "M", "n": "N", "curr": "Current (mA)", "volt": "Voltage (mV)", "res": "Resistivity (Ωm)", "status": "Status"}
        for col in columns:
            self.tree.heading(col, text=col_map[col])
            self.tree.column(col, anchor="center", width=80)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def _create_plot_tab(self):
        plot_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(plot_frame, text="Plot Resistivity")
        self.plot_figure = Figure(figsize=(8, 6), dpi=100)
        self.plot_axes = self.plot_figure.add_subplot(111)
        self.plot_axes.set_title("Apparent Resistivity Profile")
        self.plot_axes.set_xlabel("Measurement Point")
        self.plot_axes.set_ylabel("Apparent Resistivity (Ωm)")
        self.plot_axes.grid(True)
        self.plot_canvas = FigureCanvasTkAgg(self.plot_figure, master=plot_frame)
        self.plot_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(self.plot_canvas, plot_frame)
        toolbar.update()
        self.plot_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _create_export_tab(self):
        export_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(export_frame, text="Export")
        ttk.Button(export_frame, text="Export Data to CSV", command=self.export_to_csv, style="Accent.TButton").pack(pady=10, fill="x")
        ttk.Button(export_frame, text="Save Plot as Image", command=self.save_plot_image, style="Accent.TButton").pack(pady=10, fill="x")

    def update_title(self, *args):
        config = self.config_var.get()
        self.title(f"RMCS - {self.project_name} [{config}]")
        print(f"🔄  Configuration changed to '{config}' - Title updated")

    def on_config_change(self, expected_config=None):
        actual_config = self.config_var.get()
        
        print(f"🎯  Configuration radio button clicked - Expected: '{expected_config}', Actual: '{actual_config}'")
        
        if expected_config and expected_config != actual_config:
            print(f"⚠️   Config mismatch detected! Forcing set to '{expected_config}'")
            self.config_var.set(expected_config)
            actual_config = expected_config
        
        self.update_title()
        
        if self.mode_var.get() == "Manual":
            self.update_manual_command_display()
        
        print(f"✅  Configuration successfully changed to '{actual_config}'")

    def on_mode_change(self, expected_mode=None):
        actual_mode = self.mode_var.get()
        
        print(f"🔀  Mode radio button clicked - Expected: '{expected_mode}', Actual: '{actual_mode}'")
        
        if expected_mode and expected_mode != actual_mode:
            print(f"⚠️   Mode mismatch detected! Forcing set to '{expected_mode}'")
            self.mode_var.set(expected_mode)
            actual_mode = expected_mode
        
        self.toggle_mode()
        
        print(f"✅  Mode successfully changed to '{actual_mode}'")

    def update_project_name(self):
        new_name = self.project_name_entry.get().strip()
        if new_name:
            old_name = self.project_name
            self.project_name = new_name
            self.update_title()
            print(f"📝  Project name changed from '{old_name}' to '{new_name}'")
        else:
            messagebox.showwarning("Warning", "Project name cannot be empty.")
            
    def toggle_mode(self, *args):
        mode = self.mode_var.get()
        print(f"🔀  Mode switched to '{mode}'")
        
        self.start_button.config(state="normal" if mode == "Otomatis" else "disabled")
        if mode == "Otomatis":
            self.manual_mode_frame.grid_remove()
            self.auto_mode_frame.grid()
            print("  ↳ Automatic mode activated - Auto controls visible")
        else:
            self.auto_mode_frame.grid_remove()
            self.manual_mode_frame.grid()
            print("  ↳ Manual mode activated - Manual controls visible")

    def update_manual_command_display(self):
        try:
            a = self.a_entry.get() or "?"
            b = self.b_entry.get() or "?"
            m = self.m_entry.get() or "?"
            n = self.n_entry.get() or "?"
            config = self.config_var.get()
            
            cmd_text = f"A={a}, B={b}, M={m}, N={n} [{config}]"
            self.manual_cmd_label.config(text=cmd_text, foreground="black")
            print(f"🔧  Manual command display updated: {cmd_text}")
        except:
            self.manual_cmd_label.config(text="Invalid input", foreground="red")

    def send_manual_measurement(self):
        if not self.is_connected:
            return messagebox.showwarning("Warning", "Not connected to device.")
        
        if self.manual_measurement_active:
            return messagebox.showwarning("Warning", "Manual measurement is already in progress.")
            
        try:
            a = int(self.a_entry.get())
            b = int(self.b_entry.get())
            m = int(self.m_entry.get())
            n = int(self.n_entry.get())
            
            if not all(1 <= x <= 64 for x in [a, b, m, n]):
                raise ValueError("Electrode values must be between 1-64")
                
            print(f"🎯  Starting manual measurement A={a}, B={b}, M={m}, N={n}")
            
            self.update_manual_command_display()
            
            if self.measurement_sequence:
                print("⚠️   Clearing existing CMD sequence for manual measurement")
                self.measurement_sequence = []
                for i in self.tree.get_children():
                    self.tree.delete(i)
            
            for elec_num_str in self.last_manual_electrodes.values():
                if elec_num_str is not None:
                    self.send_command(f"OFF:{elec_num_str}")

            for elec_num_str in [str(a), str(b), str(m), str(n)]:
                self.send_command(f"ON:{elec_num_str}")

            self.last_manual_electrodes = {'A': str(a), 'B': str(b), 'M': str(m), 'N': str(n)}
            
            self.manual_measurement_active = True
            self.send_command(f"GETDATA:{m}")
            
            manual_row_id = "manual_" + str(len(self.tree.get_children()))
            self.tree.insert("", "end", iid=manual_row_id, values=("Manual", a, b, m, n, "", "", "", "Measuring..."))
            
            try:
                duration = int(self.timer_spinbox.get())
                self.countdown_label.config(foreground="black")
                self.update_countdown(duration)
                self.after(duration * 1000, lambda: self.finish_manual_measurement(manual_row_id, a, b, m, n))
                print(f"⏱️   Manual measurement timer started ({duration}s)")
            except ValueError:
                self.finish_manual_measurement(manual_row_id, a, b, m, n)
                messagebox.showerror("Error", "Timer duration must be a valid number.")
                
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
            print(f"❌  Manual measurement failed - {e}")

    def finish_manual_measurement(self, row_id, a, b, m, n):
        print(f"🏁  Finishing manual measurement for A={a}, B={b}, M={m}, N={n}")
        
        for elec_num_str in [str(a), str(b), str(m), str(n)]:
            self.send_command(f"OFF:{elec_num_str}")
        
        self.countdown_label.config(text="0", foreground="grey")
        self.manual_measurement_active = False
        
        if self.tree.exists(row_id):
            current_values = self.tree.item(row_id)["values"]
            if current_values[7] == "Measuring...":
                self.tree.item(row_id, values=(current_values[0], a, b, m, n, "N/A", "N/A", "N/A", "Timeout"))
                print("⏰  Manual measurement timed out")
        
        print("✅  Manual measurement completed")

    def stop_manual_measurement(self):
        if self.manual_measurement_active:
            print("🛑  Stopping manual measurement")
            
            for elec_num_str in self.last_manual_electrodes.values():
                if elec_num_str is not None:
                    self.send_command(f"OFF:{elec_num_str}")
            
            self.manual_measurement_active = False
            self.countdown_label.config(text="0", foreground="grey")
            
            if self.countdown_job:
                self.after_cancel(self.countdown_job)
                self.countdown_job = None
            
            print("✅  Manual measurement stopped")
        else:
            print("ℹ️   No manual measurement to stop")

    def send_manual_command(self):
        self.send_manual_measurement()

    def update_countdown(self, remaining):
        self.countdown_label.config(text=str(remaining))
        if remaining > 0:
            self.countdown_job = self.after(1000, self.update_countdown, remaining - 1)
        else:
            self.countdown_label.config(foreground="grey")

    def start_measurement_sequence(self):
        if self.mode_var.get() == "Manual":
            return messagebox.showwarning("Warning", "Switch to 'Automatic Mode' to start sequence.")
        if not self.is_connected:
            return messagebox.showwarning("Warning", "Not connected to device.")
        if not self.measurement_sequence:
            return messagebox.showwarning("Warning", "No measurement sequence loaded (Load CMD).")
        if self.is_running:
            return messagebox.showwarning("Warning", "Measurement is already running.")
        
        print(f"🚀  Starting automatic measurement sequence with {len(self.measurement_sequence)} steps")
        
        self.reset_plot()
        self.is_running = True
        self.current_step = 0
        self.progress_bar['maximum'] = len(self.measurement_sequence)
        self.progress_bar['value'] = 0
        self.execute_next_step()

    def execute_next_step(self):
        if not self.is_running or self.current_step >= len(self.measurement_sequence):
            return self.finish_measurement()
        try:
            duration = int(self.timer_spinbox.get())
        except ValueError:
            self.finish_measurement()
            return messagebox.showerror("Error", "Timer duration must be a valid number.")
        
        step_data = self.measurement_sequence[self.current_step]
        a, b, m, n = step_data['A'], step_data['B'], step_data['M'], step_data['N']
        
        print(f"📊  Executing step {self.current_step + 1}/{len(self.measurement_sequence)} - A={a}, B={b}, M={m}, N={n}")
        
        self.tree.item(self.current_step, values=(self.current_step + 1, a, b, m, n, "", "", "", "Measuring..."))
        self.a_label.config(text=f"A{a}"); self.b_label.config(text=f"B{b}")
        self.m_label.config(text=f"M{m}"); self.n_label.config(text=f"N{n}")

        self.send_command(f"ON:{a}"); self.send_command(f"ON:{b}")
        self.send_command(f"ON:{m}"); self.send_command(f"ON:{n}")
        
        self.send_command(f"GETDATA:{m}")

        self.countdown_label.config(foreground="black")
        self.update_countdown(duration)
        self.after(duration * 1000, self.process_step_result)

    def process_step_result(self):
        step_data = self.measurement_sequence[self.current_step]
        a, b, m, n = step_data['A'], step_data['B'], step_data['M'], step_data['N']
        
        print(f"🔄  Processing step {self.current_step + 1} result - A={a}, B={b}, M={m}, N={n}")
        
        self.send_command(f"OFF:{a}"); self.send_command(f"OFF:{b}")
        self.send_command(f"OFF:{m}"); self.send_command(f"OFF:{n}")

        self.progress_bar['value'] = self.current_step + 1
        self.current_step += 1
        self.after(500, self.execute_next_step)

    def finish_measurement(self):
        self.is_running = False
        print("🏁  Automatic measurement sequence completed")
        messagebox.showinfo("Completed", "Measurement sequence has been completed.")
        self.countdown_label.config(text="0", foreground="grey")
        if self.mode_var.get() == "Otomatis":
            self.a_label.config(text="A0"); self.b_label.config(text="B0")
            self.m_label.config(text="M0"); self.n_label.config(text="N0")

    def reset_all(self):
        print("🔄  Resetting all systems")
        
        self.is_running = False
        self.manual_measurement_active = False
        
        if self.countdown_job:
            self.after_cancel(self.countdown_job)
            self.countdown_job = None
        self.countdown_label.config(text="0", foreground="grey")
        
        if self.is_connected:
            for elec, pin_str in self.last_manual_electrodes.items():
                if pin_str is not None:
                    self.send_command(f"OFF:{pin_str}")

        self.last_manual_electrodes = {'A': None, 'B': None, 'M': None, 'N': None}
        self.progress_bar['value'] = 0
        
        if self.measurement_sequence:
            for i in self.tree.get_children(): self.tree.delete(i)
            self.measurement_sequence = []
            
        self.reset_plot()
        
        if hasattr(self, 'manual_cmd_label'):
            self.manual_cmd_label.config(text="No command", foreground="grey")
        
        print("✅  System reset completed")

    def update_plot(self):
        self.plot_axes.clear()
        self.plot_axes.plot(self.plot_data_x, self.plot_data_y, marker='o', linestyle='-')
        self.plot_axes.set_title("Apparent Resistivity Profile")
        self.plot_axes.set_xlabel("Measurement Point")
        self.plot_axes.set_ylabel("Apparent Resistivity (Ωm)")
        self.plot_axes.grid(True)
        self.plot_canvas.draw()

    def reset_plot(self):
        self.plot_data_x.clear()
        self.plot_data_y.clear()
        self.plot_axes.clear()
        self.plot_axes.set_title("Apparent Resistivity Profile")
        self.plot_axes.set_xlabel("Measurement Point")
        self.plot_axes.set_ylabel("Apparent Resistivity (Ωm)")
        self.plot_axes.grid(True)
        self.plot_canvas.draw()

    def export_to_csv(self):
        if not self.tree.get_children():
            return messagebox.showwarning("Warning", "No data to export.")
        default_name = f"{self.project_name}_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = filedialog.asksaveasfilename(initialfile=default_name, defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")], title="Save Data as CSV")
        if not filepath: return
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([self.tree.heading(col)["text"] for col in self.tree["columns"]])
                for row_id in self.tree.get_children():
                    writer.writerow(self.tree.item(row_id)["values"])
            messagebox.showinfo("Success", f"Data successfully saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{e}")

    def save_plot_image(self):
        if not self.plot_data_x:
            return messagebox.showwarning("Warning", "No plot to save.")
        config_type = self.config_var.get()
        default_name = f"{self.project_name}_Plot_{config_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = filedialog.asksaveasfilename(initialfile=default_name, defaultextension=".png", filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("All files", "*.*")], title="Save Plot Image")
        if not filepath: return
        try:
            self.plot_figure.savefig(filepath, dpi=300)
            messagebox.showinfo("Success", f"Plot successfully saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image:\n{e}")

    def populate_com_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.com_port_combo['values'] = ports
        if ports: self.com_port_combo.current(0)
            
    def toggle_connection(self):
        if not self.is_connected: self.connect()
        else: self.disconnect()

    def connect(self):
        port = self.com_port_combo.get()
        if not port: return messagebox.showerror("Error", "COM port not selected.")
        try:
            self.serial_port = serial.Serial(port, int(self.baud_rate_combo.get()), timeout=1)
            self.status_label.config(text="Connected", foreground="green")
            self.connect_button.config(text="Disconnect")
            self.is_connected = True
            self.serial_thread = threading.Thread(target=self.read_serial_data, daemon=True)
            self.serial_thread.start()
            print(f"🔌  Connected to {port} at {self.baud_rate_combo.get()} baud")
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")
            print(f"❌  Connection failed - {e}")

    def disconnect(self):
        self.is_running = False
        self.manual_measurement_active = False
        if self.serial_port: self.serial_port.close()
        self.serial_port = None
        self.is_connected = False
        self.status_label.config(text="Not ready", foreground="red")
        self.connect_button.config(text="Connect")
        print("🔌  Disconnected from serial port")
        
    def send_command(self, command):
        if self.is_connected and self.serial_port:
            try:
                self.serial_port.write((command + '\n').encode('utf-8'))
                print(f"➡️  Command sent to Master: {command}")
            except serial.SerialException:
                self.disconnect()
        else:
            print("❌  Cannot send command - not connected")

    def read_serial_data(self):
        while self.is_connected and self.serial_port:
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line: self.data_queue.put(line)
            except (serial.SerialException, TypeError):
                break

    def process_serial_queue(self):
        try:
            while not self.data_queue.empty():
                line = self.data_queue.get_nowait()
                print(f"⬅️  Data received from Master: {line}")
                
                if line.startswith("DATA:"):
                    try:
                        data_part = line.split(":")[1]
                        values = data_part.split(',')
                        if len(values) == 3:
                            slave_id, real_curr, real_volt = map(float, values)
                            resistance = real_volt / real_curr if real_curr != 0 else 0
                            
                            if self.manual_measurement_active:
                                for row_id in self.tree.get_children():
                                    if str(row_id).startswith("manual_"):
                                        current_values = self.tree.item(row_id)["values"]
                                        if current_values[8] == "Measuring...":
                                            a, b, m, n = int(current_values[1]), int(current_values[2]), int(current_values[3]), int(current_values[4])
                                            resistivity = self.calculate_resistivity(a, b, m, n, resistance)
                                            
                                            curr_str = f"{real_curr:.2f}".replace('.', ',')
                                            volt_str = f"{real_volt:.2f}".replace('.', ',')
                                            res_str = f"{resistivity:.2f}".replace('.', ',')
                                            
                                            self.tree.item(row_id, values=("Manual", a, b, m, n, curr_str, volt_str, res_str, "Done"))
                                            print(f"📊  Manual measurement data processed - Resistivity: {resistivity:.2f} Ωm")
                                            break
                            else:
                                if self.current_step < len(self.measurement_sequence):
                                    step_data = self.measurement_sequence[self.current_step]
                                    a, b, m, n = step_data['A'], step_data['B'], step_data['M'], step_data['N']
                                    resistivity = self.calculate_resistivity(a, b, m, n, resistance)
                                    
                                    curr_str = f"{real_curr:.2f}".replace('.', ',')
                                    volt_str = f"{real_volt:.2f}".replace('.', ',')
                                    res_str = f"{resistivity:.2f}".replace('.', ',')

                                    self.tree.item(self.current_step, values=(self.current_step + 1, a, b, m, n, curr_str, volt_str, res_str, "Done"))
                                    
                                    self.plot_data_x.append(self.current_step + 1)
                                    self.plot_data_y.append(resistivity)
                                    self.update_plot()
                                    print(f"📊  Automatic measurement data processed - Step {self.current_step + 1}, Resistivity: {resistivity:.2f} Ωm")
                                    
                    except (ValueError, IndexError) as e:
                        print(f"❌  Error parsing data: {e} - Raw data: {line}")
        finally:
            self.after(100, self.process_serial_queue)

    def calculate_resistivity(self, a, b, m, n, resistance):
        config_type = self.config_var.get()
        K = 0.0
        
        if config_type == "Wenner":
            spacing = abs(m - a) * self.base_spacing
            K = 2 * math.pi * spacing
            print(f"🧮  Wenner calculation - spacing: {spacing}, K: {K:.2f}")
        elif config_type == "Schlumberger":
            ab_dist = abs(b - a) * self.base_spacing
            mn_dist = abs(n - m) * self.base_spacing
            if mn_dist > 0: 
                K = math.pi * ( ((ab_dist/2)**2 - (mn_dist/2)**2) / mn_dist )
            print(f"🧮  Schlumberger calculation - AB: {ab_dist}, MN: {mn_dist}, K: {K:.2f}")
        elif config_type == "Dipole-dipole":
            a_spacing = abs(b - a) * self.base_spacing
            dipole_center_dist = abs(((m+n)/2) - ((a+b)/2)) * self.base_spacing
            if a_spacing > 0:
                n_factor = dipole_center_dist / a_spacing
                K = math.pi * n_factor * (n_factor + 1) * (n_factor + 2) * a_spacing
            print(f"🧮  Dipole-dipole calculation - a_spacing: {a_spacing}, n_factor: {n_factor:.2f}, K: {K:.2f}")
        
        resistivity = K * resistance
        print(f"🧮  Final resistivity calculation - K: {K:.2f}, R: {resistance:.2f}, ρ: {resistivity:.2f} Ωm")
        return resistivity

    def browse_file(self):
        filepath = filedialog.askopenfilename(title="Open Command File", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if filepath:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, filepath)
    
    def load_cmd_file(self):
        filepath = self.file_path_entry.get()
        if not filepath:
            return messagebox.showwarning("Warning", "Please select a command file first.")
        new_sequence = []
        try:
            encodings = ['utf-8', 'latin-1', 'cp1252']
            file_content = None
            
            for encoding in encodings:
                try:
                    with open(filepath, 'r', encoding=encoding) as f:
                        file_content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if file_content is None:
                raise ValueError("Cannot read file with supported encoding")
            
            for line_num, line in enumerate(file_content.splitlines(), 1):
                if not line.strip() or line.strip().startswith('#'):
                    continue
                
                parts = []
                if ',' in line:
                    parts = line.strip().split(',')
                elif ' ' in line:
                    parts = line.strip().split()
                else:
                    parts = line.strip().split('\t')

                if len(parts) == 4:
                    a, b, m, n = map(int, parts)
                    new_sequence.append({'A': a, 'B': b, 'M': m, 'N': n})
                else:
                    raise ValueError(f"Each line must contain 4 numbers. Error at line {line_num}.")
            
            self.measurement_sequence = new_sequence
            
            for i in self.tree.get_children():
                self.tree.delete(i)
            
            for idx, step in enumerate(self.measurement_sequence):
                values = (idx + 1, step['A'], step['B'], step['M'], step['N'], "", "", "", "Waiting")
                self.tree.insert("", "end", iid=idx, values=values)
                
            print(f"📁  CMD file loaded - {len(self.measurement_sequence)} measurement points")
            messagebox.showinfo("Success", f"Successfully loaded {len(self.measurement_sequence)} measurement points from file.")

        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found:\n{filepath}")
        except ValueError as e:
            messagebox.showerror("File Format Error", f"Error occurred while reading file:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error occurred:\n{e}")

    def on_closing(self):
        if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            print("🚪  Application closing")
            self.disconnect()
            self.destroy()

if __name__ == "__main__":
    import sys
    
    # Remove problematic sys.stdout.flush() call
    
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Red.TButton", foreground="white", background=STYLE_CONFIG["red_button"])
    style.configure("Accent.TButton", foreground="white", background=STYLE_CONFIG["green_button"])
    
    print("🚀  RMCS Application starting...")
    
    app = RMCSApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    print("🚀  RMCS Application started successfully!")
    
    # Ensure the app window is brought to front
    app.lift()
    app.attributes('-topmost', True)
    app.after_idle(lambda: app.attributes('-topmost', False))
    
    app.mainloop()