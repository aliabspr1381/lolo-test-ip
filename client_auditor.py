import tkinter as tk
import customtkinter as ctk
import socket
import time
import threading

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AdvancedNetworkAudit(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("تست پیشرفته پورت و پروتکل شبکه (v2026)")
        self.geometry("600x750")
        self.resizable(False, False)
        
        # پورت‌های پیش‌فرض به‌روزرسانی شده
        self.default_ports = [80, 443, 53, 123, 500, 4500, 3074, 8080, 8443]
        self.custom_ports = []
        self.port_checkboxes = {}
        
        # IP & Protocol Selection
        self.lbl_ip = ctk.CTkLabel(self, text="آی‌پی سرور (IPv4 یا IPv6):", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_ip.pack(pady=(15, 2))
        self.ent_ip = ctk.CTkEntry(self, placeholder_text="مثال: 5.188.190.154 یا 2001:db8::1", width=350, justify="center")
        self.ent_ip.pack(pady=5)
        
        # Protocol Frame
        self.proto_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.proto_frame.pack(pady=5)
        
        self.chk_all_proto = ctk.CTkCheckBox(self.proto_frame, text="انتخاب همه پروتکل‌ها", command=self.toggle_all_protocols)
        self.chk_all_proto.grid(row=0, column=0, padx=10)
        self.chk_all_proto.select()
        
        self.chk_tcp = ctk.CTkCheckBox(self.proto_frame, text="تست TCP")
        self.chk_tcp.grid(row=0, column=1, padx=10)
        self.chk_tcp.select()
        
        self.chk_udp = ctk.CTkCheckBox(self.proto_frame, text="تست UDP")
        self.chk_udp.grid(row=0, column=2, padx=10)
        self.chk_udp.select()

        # Port Management Frame
        self.port_frame = ctk.CTkLabelFrame(self, text=" مدیریت پورت‌های مورد تست ")
        self.port_frame.pack(pady=10, padx=30, fill="x")
        
        self.chk_all_ports = ctk.CTkCheckBox(self.port_frame, text="انتخاب همه پورت‌ها", command=self.toggle_all_ports)
        self.chk_all_ports.pack(anchor="w", padx=15, pady=5)
        self.chk_all_ports.select()
        
        # Grid for checkboxes
        self.cb_grid_frame = ctk.CTkFrame(self.port_frame, fg_color="transparent")
        self.cb_grid_frame.pack(fill="x", padx=15, pady=5)
        self.render_port_checkboxes()
        
        # Add Custom Port
        self.add_port_frame = ctk.CTkFrame(self.port_frame, fg_color="transparent")
        self.add_port_frame.pack(fill="x", padx=15, pady=(5, 10))
        self.ent_custom_port = ctk.CTkEntry(self.add_port_frame, placeholder_text="پورت جدید", width=100, justify="center")
        self.ent_custom_port.pack(side="left", padx=5)
        self.btn_add_port = ctk.CTkButton(self.add_port_frame, text="اضافه کردن پورت", width=120, command=self.add_custom_port)
        self.btn_add_port.pack(side="left", padx=5)
        
        # Start Button
        self.btn_start = ctk.CTkButton(self, text="شروع تست خودکار", fg_color="#2b8a3e", hover_color="#237032", font=ctk.CTkFont(size=14, weight="bold"), width=350, command=self.start_test)
        self.btn_start.pack(pady=10)
        
        # Progress
        self.progress = ctk.CTkProgressBar(self, width=350)
        self.progress.pack(pady=5)
        self.progress.set(0)
        
        # Console Output
        self.txt_output = ctk.CTkTextbox(self, width=540, height=240, font=ctk.CTkFont(family="Courier", size=11))
        self.txt_output.pack(pady=15, padx=30)
        
    def render_port_checkboxes(self):
        for widget in self.cb_grid_frame.winfo_children():
            widget.destroy()
            
        all_ports = self.default_ports + self.custom_ports
        for idx, port in enumerate(all_ports):
            row = idx // 4
            col = idx % 4
            
            if port not in self.port_checkboxes:
                cb = ctk.CTkCheckBox(self.cb_grid_frame, text=str(port))
                cb.select()
                self.port_checkboxes[port] = cb
            else:
                cb = self.port_checkboxes[port]
                
            cb.grid(row=row, column=col, padx=10, pady=5, sticky="w")
            
    def add_custom_port(self):
        port_str = self.ent_custom_port.get().strip()
        if port_str.isdigit():
            port = int(port_str)
            if 0 < port <= 65535 and port not in (self.default_ports + self.custom_ports):
                self.custom_ports.append(port)
                self.render_port_checkboxes()
                self.ent_custom_port.delete(0, tk.END)
                
    def toggle_all_protocols(self):
        if self.chk_all_proto.get():
            self.chk_tcp.select()
            self.chk_udp.select()
        else:
            self.chk_tcp.deselect()
            self.chk_udp.deselect()
            
    def toggle_all_ports(self):
        for cb in self.port_checkboxes.values():
            if self.chk_all_ports.get():
                cb.select()
            else:
                cb.deselect()
                
    def log(self, text):
        self.txt_output.insert(tk.END, f"{text}\n")
        self.txt_output.see(tk.END)
        
    def is_ipv6(self, ip):
        try:
            socket.inet_pton(socket.AF_INET6, ip)
            return True
        except socket.error:
            return False

    def start_test(self):
        ip = self.ent_ip.get().strip()
        if not ip:
            self.txt_output.delete("1.0", tk.END)
            self.log("❌ خطا: لطفا آی‌پی سرور را وارد کنید.")
            return
            
        self.btn_start.configure(state="disabled")
        self.txt_output.delete("1.0", tk.END)
        self.progress.set(0)
        
        threading.Thread(target=self.run_audit, args=(ip,), daemon=True).start()
        
    def run_audit(self, ip):
        is_v6 = self.is_ipv6(ip)
        addr_family = socket.AF_INET6 if is_v6 else socket.AF_INET
        
        self.log(f"🔍 تشخیص نوع پروتکل شبکه: {'IPv6' if is_v6 else 'IPv4'}")
        self.log(f"🛰️ شروع تست به سمت آدرس: {ip}")
        self.log("==========================================")
        
        selected_ports = [port for port, cb in self.port_checkboxes.items() if cb.get()]
        if not selected_ports:
            self.log("❌ خطا: هیچ پورتی برای تست انتخاب نشده است.")
            self.btn_start.configure(state="normal")
            return
            
        total_steps = len(selected_ports) * 2
        current_step = 0
        
        for port in selected_ports:
            # 1. TCP Test
            if self.chk_tcp.get():
                current_step += 1
                self.progress.set(current_step / total_steps)
                try:
                    s = socket.socket(addr_family, socket.SOCK_STREAM)
                    s.settimeout(2.0)
                    start = time.time()
                    s.connect((ip, port))
                    s.sendall(b'\x16\x03\x01\x02\x00')
                    s.close()
                    self.log(f"✅ پورت TCP {port} [باز] | تأخیر: {int((time.time()-start)*1000)}ms")
                except Exception:
                    self.log(f"❌ پورت TCP {port} [مسدود یا بدون پاسخ]")
            
            # 2. UDP Test
            if self.chk_udp.get():
                current_step += 1
                self.progress.set(current_step / total_steps)
                try:
                    u = socket.socket(addr_family, socket.SOCK_DGRAM)
                    u.settimeout(2.0)
                    u.sendto(b'\x01\x00\x00\x00' + b'\x23' * 100, (ip, port))
                    data, addr = u.recvfrom(1024)
                    u.close()
                    self.log(f"✅ پورت UDP {port} [باز - پاسخ پروتکل دریافت شد]")
                except socket.timeout:
                    self.log(f"⚠️ پورت UDP {port} [دراپ / احتمال فیلترینگ ترافیک]")
                except Exception:
                    self.log(f"❌ پورت UDP {port} [بسته]")
                    
        self.log("==========================================")
        self.log("🎉 تست پورت‌های انتخابی به پایان رسید.")
        self.progress.set(1.0)
        self.btn_start.configure(state="normal")

if __name__ == "__main__":
    app = AdvancedNetworkAudit()
    app.mainloop()
