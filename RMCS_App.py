import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial
import serial.tools.list_ports
import threading
import queue

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
        self.title("Resistivity Multielectrode Control System (RMCS) - Final")
        self.geometry("1100x700")
        self.configure(bg=STYLE_CONFIG["bg_color"])

        self.serial_port = None
        self.serial_thread = None
        self.data_queue = queue.Queue()
        self.is_connected = False
        self.is_running = False
        self.last_manual_electrodes = {'A': None, 'B': None, 'M': None, 'N': None}
        self.countdown_job = None

        self.measurement_sequence = []
        self.current_step = 0

        self._create_main_layout()
        self._create_all_widgets()
        self.populate_com_ports()

        self.mode_var.trace_add("write", lambda *args: self.toggle_mode())
        self.config_var.trace_add("write", lambda *args: self.handle_config_change())

        self.process_serial_queue()

    # ===================================================================
    # BAGIAN 1: ANTARMUKA (GUI)
    # ===================================================================

    def _create_main_layout(self):
        self.grid_columnconfigure(0, weight=1, uniform="group1")
        self.grid_columnconfigure(1, weight=3, uniform="group1")
        self.grid_rowconfigure(0, weight=1)

        self.left_panel = ttk.Frame(self, padding=10)
        self.left_panel.grid(row=0, column=0, sticky="nsew")
        self.left_panel.rowconfigure(3, weight=1)

        self.right_panel = ttk.Frame(self, padding=10)
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

    def _create_all_widgets(self):
        self._create_comms_frame()
        self._create_measurement_frame()
        self._create_timer_frame()
        self._create_electrode_control_frame()
        self._create_progress_frame()
        self._create_command_setting_frame()
        self._create_data_table_frame()

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

        self.config_var = tk.StringVar(value="Wenner")
        ttk.Radiobutton(frame, text="Schlumberger", variable=self.config_var, value="Schlumberger").pack(anchor="w")
        ttk.Radiobutton(frame, text="Wenner", variable=self.config_var, value="Wenner").pack(anchor="w")
        ttk.Radiobutton(frame, text="Dipole-dipole", variable=self.config_var, value="Dipole-dipole").pack(anchor="w")

        self.start_button = ttk.Button(frame, text="START MEASUREMENT (AUTO)", command=self.start_measurement_sequence, style="Accent.TButton")
        self.start_button.pack(fill="x", pady=10)

    def handle_config_change(self):
        config = self.config_var.get()
        print(f"⚙️ Konfigurasi pengukuran diubah ke: {config}")

    def set_mode_otomatis(self):
        self.mode_var.set("Otomatis")

    def set_mode_manual(self):
        self.mode_var.set("Manual")

    def toggle_mode(self):
        mode = self.mode_var.get()
        print(f"--- toggle_mode() dipanggil. Mode sekarang: {mode} ---")

        self.auto_mode_frame.grid_forget()
        self.manual_mode_frame.grid_forget()

        if mode == "Otomatis":
            self.auto_mode_frame.grid(row=0, column=0, sticky="nsew")
            self.start_button.config(state="normal")
        else:
            self.manual_mode_frame.grid(row=0, column=0, sticky="nsew")
            self.start_button.config(state="disabled")

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

        self.mode_var = tk.StringVar(value="Otomatis")
        ttk.Radiobutton(mode_frame, text="Mode Otomatis", variable=self.mode_var, value="Otomatis", command=self.set_mode_otomatis).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Mode Manual", variable=self.mode_var, value="Manual", command=self.set_mode_manual).pack(side="left", padx=5)

        self.widget_container = ttk.Frame(frame)
        self.widget_container.pack(fill="x")
        self.widget_container.grid_rowconfigure(0, weight=1)
        self.widget_container.grid_columnconfigure(0, weight=1)

        self.auto_mode_frame = ttk.Frame(self.widget_container)
        self.a_label = ttk.Label(self.auto_mode_frame, text="A0", font=STYLE_CONFIG["font_large_display"], foreground="#D32F2F")
        self.b_label = ttk.Label(self.auto_mode_frame, text="B0", font=STYLE_CONFIG["font_large_display"], foreground="#D32F2F")
        self.m_label = ttk.Label(self.auto_mode_frame, text="M0", font=STYLE_CONFIG["font_large_display"], foreground="#1976D2")
        self.n_label = ttk.Label(self.auto_mode_frame, text="N0", font=STYLE_CONFIG["font_large_display"], foreground="#1976D2")
        self.a_label.grid(row=0, column=0, padx=20, pady=5)
        self.b_label.grid(row=0, column=1, padx=20, pady=5)
        self.m_label.grid(row=1, column=0, padx=20, pady=5)
        self.n_label.grid(row=1, column=1, padx=20, pady=5)
        self.auto_mode_frame.grid(row=0, column=0, sticky="nsew")

        self.manual_mode_frame = ttk.Frame(self.widget_container)
        ttk.Label(self.manual_mode_frame, text="A:", font=STYLE_CONFIG["font_bold"]).grid(row=0, column=0, padx=5, pady=5)
        self.a_entry = ttk.Spinbox(self.manual_mode_frame, from_=1, to=64, width=5, font=STYLE_CONFIG["font_normal"])
        self.a_entry.grid(row=0, column=1)
        ttk.Label(self.manual_mode_frame, text="B:", font=STYLE_CONFIG["font_bold"]).grid(row=0, column=2, padx=5, pady=5)
        self.b_entry = ttk.Spinbox(self.manual_mode_frame, from_=1, to=64, width=5, font=STYLE_CONFIG["font_normal"])
        self.b_entry.grid(row=0, column=3)
        ttk.Label(self.manual_mode_frame, text="M:", font=STYLE_CONFIG["font_bold"]).grid(row=1, column=0, padx=5, pady=5)
        self.m_entry = ttk.Spinbox(self.manual_mode_frame, from_=1, to=64, width=5, font=STYLE_CONFIG["font_normal"])
        self.m_entry.grid(row=1, column=1)
        ttk.Label(self.manual_mode_frame, text="N:", font=STYLE_CONFIG["font_bold"]).grid(row=1, column=2, padx=5, pady=5)
        self.n_entry = ttk.Spinbox(self.manual_mode_frame, from_=1, to=64, width=5, font=STYLE_CONFIG["font_normal"])
        self.n_entry.grid(row=1, column=3)
        manual_button = ttk.Button(self.manual_mode_frame, text="KIRIM MANUAL", command=self.send_manual_command)
        manual_button.grid(row=2, column=0, columnspan=4, pady=10, sticky="ew")
        self.manual_mode_frame.grid(row=0, column=0, sticky="nsew")

    def _create_progress_frame(self):
        frame = ttk.LabelFrame(self.left_panel, text="MEA. PROGRESS", padding=10)
        frame.pack(fill="x", pady=5, side="bottom")

        self.progress_bar = ttk.Progressbar(frame, orient="horizontal", length=200, mode="determinate")
        self.progress_bar.pack(fill="x", expand=True, pady=5)
        
        self.reset_button = ttk.Button(frame, text="RESET SYSTEM", command=self.reset_all, style="Red.TButton")
        self.reset_button.pack(fill="x", pady=5)

    def _create_command_setting_frame(self):
        frame = ttk.LabelFrame(self.right_panel, text="Command Setting", padding=10)
        frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        ttk.Label(frame, text="Cmd File:").grid(row=0, column=0, padx=5, sticky="w")
        self.file_path_entry = ttk.Entry(frame, width=50)
        self.file_path_entry.grid(row=0, column=1, padx=5, sticky="ew")
        
        ttk.Button(frame, text="Browse...", command=self.browse_file).grid(row=0, column=2, padx=5)
        ttk.Button(frame, text="Load CMD", command=self.load_cmd_file).grid(row=0, column=3, padx=5)

    def _create_data_table_frame(self):
        frame = ttk.Frame(self.right_panel)
        frame.grid(row=1, column=0, sticky="nsew", pady=5)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        columns = ("no", "a", "b", "m", "n", "curr", "volt", "res", "status")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        
        col_map = {"no": "No", "a": "A", "b": "B", "m": "M", "n": "N", "curr": "Current (mA)", "volt": "Voltage (mV)", "res": "Resistivity (Ωm)", "status": "Status"}
        width_map = {"no": 30, "a": 30, "b": 30, "m": 30, "n": 30, "curr": 100, "volt": 100, "res": 120, "status": 100}

        for col in columns:
            self.tree.heading(col, text=col_map[col])
            self.tree.column(col, width=width_map[col], anchor="center")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    # ===================================================================
    # BAGIAN 2: LOGIKA APLIKASI DAN FUNGSI
    # ===================================================================
    
    def set_mode_otomatis(self):
        self.mode_var.set("Otomatis")
        self.toggle_mode()

    def set_mode_manual(self):
        self.mode_var.set("Manual")
        self.toggle_mode()

    def toggle_mode(self):
        mode = self.mode_var.get()
        print(f"--- toggle_mode() dipanggil. Mode sekarang: {mode} ---")

        self.start_button.config(state="normal" if mode == "Otomatis" else "disabled")
        
        if mode == "Otomatis":
            self.manual_mode_frame.grid_remove() 
            self.auto_mode_frame.grid()          
            
        elif mode == "Manual":
            self.auto_mode_frame.grid_remove()   
            self.manual_mode_frame.grid()        

    def send_manual_command(self):
        if not self.is_connected:
            messagebox.showwarning("Peringatan", "Tidak terhubung ke perangkat.")
            return
        try:
            for elec, pin in self.last_manual_electrodes.items():
                if pin is not None:
                    self.send_command(f"S{pin}:OFF")

            a = self.a_entry.get()
            b = self.b_entry.get()
            m = self.m_entry.get()
            n = self.n_entry.get()
            
            self.send_command(f"S{a}:ON")
            self.send_command(f"S{b}:ON")
            self.send_command(f"S{m}:ON")
            self.send_command(f"S{n}:ON")

            self.last_manual_electrodes = {'A': a, 'B': b, 'M': m, 'N': n}
            print("Perintah manual terkirim.")

        except Exception as e:
            messagebox.showerror("Error", f"Input tidak valid: {e}")

    def update_countdown(self, remaining):
        self.countdown_label.config(text=str(remaining))
        if remaining > 0:
            self.countdown_job = self.after(1000, self.update_countdown, remaining - 1)
        else:
            self.countdown_label.config(foreground="grey")

    def start_measurement_sequence(self):
        if self.mode_var.get() == "Manual":
            return messagebox.showwarning("Peringatan", "Ganti ke 'Mode Otomatis' untuk memulai urutan.")
        if not self.is_connected:
            return messagebox.showwarning("Peringatan", "Tidak terhubung ke perangkat.")
        if not self.measurement_sequence:
            return messagebox.showwarning("Peringatan", "Belum ada urutan pengukuran (Load CMD).")
        if self.is_running:
            return messagebox.showwarning("Peringatan", "Pengukuran sedang berjalan.")
        
        self.is_running = True
        self.current_step = 0
        self.progress_bar['maximum'] = len(self.measurement_sequence)
        self.progress_bar['value'] = 0
        self.execute_next_step()

    def execute_next_step(self):
        if not self.is_running or self.current_step >= len(self.measurement_sequence):
            self.finish_measurement()
            return
        
        try:
            duration = int(self.timer_spinbox.get())
        except ValueError:
            messagebox.showerror("Error", "Durasi timer harus angka yang valid.")
            self.finish_measurement()
            return

        step_data = self.measurement_sequence[self.current_step]
        a, b, m, n = step_data['A'], step_data['B'], step_data['M'], step_data['N']
        
        self.tree.item(self.current_step, values=(self.current_step + 1, a, b, m, n, "", "", "", "Measuring..."))
        self.a_label.config(text=f"A{a}"); self.b_label.config(text=f"B{b}")
        self.m_label.config(text=f"M{m}"); self.n_label.config(text=f"N{n}")
        
        self.send_command(f"S{a}:ON"); self.send_command(f"S{b}:ON")
        self.send_command(f"S{m}:ON"); self.send_command(f"S{n}:ON")
        
        self.send_command(f"S{m}:GETDATA")
        
        self.countdown_label.config(foreground="black")
        self.update_countdown(duration)
        self.after(duration * 1000, self.process_step_result)

    def process_step_result(self):
        step_data = self.measurement_sequence[self.current_step]
        a, b, m, n = step_data['A'], step_data['B'], step_data['M'], step_data['N']
        
        self.send_command(f"S{a}:OFF"); self.send_command(f"S{b}:OFF")
        self.send_command(f"S{m}:OFF"); self.send_command(f"S{n}:OFF")
        
        self.progress_bar['value'] = self.current_step + 1
        
        self.current_step += 1
        self.after(500, self.execute_next_step)

    def finish_measurement(self):
        self.is_running = False
        messagebox.showinfo("Selesai", "Urutan pengukuran telah selesai.")
        self.countdown_label.config(text="0", foreground="grey")
        if self.mode_var.get() == "Otomatis":
            self.a_label.config(text="A0"); self.b_label.config(text="B0")
            self.m_label.config(text="M0"); self.n_label.config(text="N0")

    def reset_all(self):
        self.is_running = False
        if self.countdown_job:
            self.after_cancel(self.countdown_job)
            self.countdown_job = None
        
        self.countdown_label.config(text="0", foreground="grey")

        if self.is_connected:
            for elec, pin in self.last_manual_electrodes.items():
                if pin is not None:
                    self.send_command(f"S{pin}:OFF")
        
        self.last_manual_electrodes = {'A': None, 'B': None, 'M': None, 'N': None}
        self.progress_bar['value'] = 0
        if self.measurement_sequence:
            for i in self.tree.get_children():
                self.tree.delete(i)
            self.measurement_sequence = []
        
        print("SISTEM DIRESET")

    # ===================================================================
    # BAGIAN 3: FUNGSI UTILITAS DAN KOMUNIKASI SERIAL
    # ===================================================================

    def populate_com_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.com_port_combo['values'] = ports
        if ports:
            self.com_port_combo.current(0)
            
    def toggle_connection(self):
        if not self.is_connected: self.connect()
        else: self.disconnect()

    def connect(self):
        port = self.com_port_combo.get()
        if not port: return messagebox.showerror("Error", "Port COM belum dipilih.")
        try:
            self.serial_port = serial.Serial(port, int(self.baud_rate_combo.get()), timeout=1)
            self.status_label.config(text="Connected", foreground="green")
            self.connect_button.config(text="Disconnect")
            self.is_connected = True
            self.serial_thread = threading.Thread(target=self.read_serial_data, daemon=True)
            self.serial_thread.start()
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", f"Gagal terhubung: {e}")

    def disconnect(self):
        self.is_running = False
        if self.serial_port: self.serial_port.close()
        self.serial_port = None
        self.is_connected = False
        self.status_label.config(text="Not ready", foreground="red")
        self.connect_button.config(text="Connect")
        
    def send_command(self, command):
        if self.is_connected and self.serial_port:
            try:
                self.serial_port.write((command + '\n').encode('utf-8'))
                print(f"➡️ Terkirim: {command}")
            except serial.SerialException:
                self.disconnect()
        else:
            print("Tidak bisa mengirim, koneksi terputus.")

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
                print(f"⬅️ Diterima: {line}")
                
                if line.startswith("DATA:"):
                    try:
                        data_part = line.split(":")[1]
                        values = data_part.split(',')
                        
                        if len(values) == 3:
                            slave_id = int(values[0])
                            real_curr = float(values[1])
                            real_volt = float(values[2])
                            
                            resistance = real_volt / real_curr if real_curr != 0 else 0
                            
                            step_data = self.measurement_sequence[self.current_step]
                            a, b, m, n = step_data['A'], step_data['B'], step_data['M'], step_data['N']
                            
                            self.tree.item(self.current_step, values=(
                                self.current_step + 1, a, b, m, n, 
                                f"{real_curr:.2f}", f"{real_volt:.2f}", f"{resistance:.2f}", "Done"
                            ))
                        else:
                            print(f"Format data tidak valid: {line}")
                    except (ValueError, IndexError) as e:
                        print(f"Error mem-parsing data: {e} - Data: {line}")

        finally:
            self.after(100, self.process_serial_queue)

    def browse_file(self):
        filepath = filedialog.askopenfilename(
            title="Buka File Perintah",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if filepath:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, filepath)
    
    def load_cmd_file(self):
        filepath = self.file_path_entry.get()
        if not filepath:
            messagebox.showwarning("Peringatan", "Pilih file perintah terlebih dahulu.")
            return

        new_sequence = []
        try:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
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
                        raise ValueError(f"Setiap baris harus berisi 4 angka. Error di baris {line_num}.")
            
            self.measurement_sequence = new_sequence
            
            for i in self.tree.get_children():
                self.tree.delete(i)
            
            for idx, step in enumerate(self.measurement_sequence):
                values = (idx + 1, step['A'], step['B'], step['M'], step['N'], "", "", "", "Waiting")
                self.tree.insert("", "end", iid=idx, values=values)
                
            messagebox.showinfo("Sukses", f"Berhasil memuat {len(self.measurement_sequence)} titik pengukuran dari file.")

        except FileNotFoundError:
            messagebox.showerror("Error", f"File tidak ditemukan:\n{filepath}")
        except ValueError as e:
            messagebox.showerror("Error Format File", f"Terjadi kesalahan saat membaca file:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Terjadi kesalahan tak terduga:\n{e}")


    def on_closing(self): 
        if messagebox.askokcancel("Keluar", "Apakah Anda yakin ingin keluar?"):
            self.disconnect()
            self.destroy()

if __name__ == "__main__":
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Red.TButton", foreground="white", background=STYLE_CONFIG["red_button"])
    style.configure("Accent.TButton", foreground="white", background=STYLE_CONFIG["green_button"])

    app = RMCSApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
