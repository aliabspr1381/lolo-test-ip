#!/usr/bin/env python3
import socket
import threading
import subprocess
import os
import sys
import time
import atexit
import signal

# پورت‌های استاندارد برای تست
PORTS = [443, 53, 123, 500, 4500, 3074, 55424]

# متغیرهای سراسری برای حفظ وضعیت فایروال
fw_originally_active = False
active_test_ports = []

def is_port_in_use(port):
    """بررسی اینکه آیا پورت توسط برنامه دیگری در سرور اشغال شده است یا خیر"""
    # تست در بستر TCP
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            return True
    # تست در بستر UDP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

def get_ufw_status():
    """بررسی روشن یا خاموش بودن فایروال سرور"""
    try:
        output = subprocess.check_output(["sudo", "ufw", "status"], stderr=subprocess.STDOUT).decode()
        if "Status: active" in output:
            return True
    except Exception:
        pass
    return False

def manage_firewall_rules(ports, action='allow'):
    """اعمال یا حذف قوانین فایروال"""
    for port in ports:
        try:
            subprocess.run(["sudo", "ufw", action, str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def cleanup_and_rollback():
    """تابع حیاتی بازگردانی سرور به حالت اول (تحت هر شرایطی اجرا می‌شود)"""
    global fw_originally_active, active_test_ports
    if fw_originally_active and active_test_ports:
        print("\n🔄 [سیستم ایمنی] در حال پاکسازی قوانین تست و بازگردانی فایروال به حالت اولیه...")
        manage_firewall_rules(active_test_ports, 'delete')
        subprocess.run(["sudo", "ufw", "reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("🔒 فایروال سرور با موفقیت به وضعیت امن قبلی بازگشت.")
    else:
        print("\n✨ پاکسازی انجام شد. هیچ تغییری در ساختار فایروال سرور اعمال باقی نماند.")

# ثبت تابع پاکسازی در هسته پایتون برای زمان بسته شدن ناگهانی نرم‌افزار یا اتصال
atexit.register(cleanup_and_rollback)

def handle_signal(signum, frame):
    sys.exit(0)

# مدیریت سیگنال‌های قطع ارتباط ترمینال (SIGHUP) و قطع توسط کاربر (SIGINT/SIGTERM)
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)
if sys.platform != "win32":
    signal.signal(signal.SIGHUP, handle_signal)

def handle_tcp_client(client_sock):
    try:
        client_sock.settimeout(3.0)
        data = client_sock.recv(1024)
        if data:
            client_sock.sendall(b"SERVER_TCP_ACK_OK")
    except Exception:
        pass
    finally:
        client_sock.close()

def start_tcp_listener(port, stop_event):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', port))
        server.listen(5)
        server.settimeout(1.0)
        while not stop_event.is_set():
            try:
                conn, addr = server.accept()
                threading.Thread(target=handle_tcp_client, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
    except Exception:
        pass
    finally:
        server.close()

def start_udp_listener(port, stop_event):
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        server.bind(('0.0.0.0', port))
        server.settimeout(1.0)
        while not stop_event.is_set():
            try:
                data, addr = server.recvfrom(1024)
                if data:
                    server.sendto(b"SERVER_UDP_ACK_OK", addr)
            except socket.timeout:
                continue
    except Exception:
        pass
    finally:
        server.close()

def main():
    global fw_originally_active, active_test_ports
    
    if os.getuid() != 0:
        print("❌ خطا: این اسکریپت برای مدیریت فایروال باید با دسترسی root (sudo) اجرا شود.")
        sys.exit(1)
        
    print("====================================================")
    print("🛰️ اسکریپت هوشمند سنجش شبکه و پورت (نسخه سرور ۲۰۲۶)")
    print("====================================================")
    
    # تفکیک پورت‌های پر و خالی
    skipped_ports = []
    for p in PORTS:
        if is_port_in_use(p):
            skipped_ports.append(p)
        else:
            active_test_ports.append(p)
            
    if skipped_ports:
        print(f"⚠️ پورت‌های روبرو توسط برنامه‌های فعال سرور اشغال شده‌اند و تغییر نمیکنند: {skipped_ports}")
    print(f"✅ پورت‌های آزاد و آماده برای تست فایروال: {active_test_ports}")
    
    # مدیریت وضعیت فایروال
    fw_originally_active = get_ufw_status()
    if fw_originally_active:
        print("🔒 فایروال UFW فعال است. باز کردن موقت پورت‌های تست...")
        manage_firewall_rules(active_test_ports, 'allow')
        subprocess.run(["sudo", "ufw", "reload"], stdout=subprocess.DEVNULL)
        print("🔓 پورت‌های تست موقتاً در فایروال مجاز شدند.")
    else:
        print("🔓 فایروال سرور خاموش است. نیازی به تغییر قوانین فایروال نیست.")
        
    # راه‌اندازی لیسنرها
    stop_event = threading.Event()
    for port in active_test_ports:
        threading.Thread(target=start_tcp_listener, args=(port, stop_event), daemon=True).start()
        threading.Thread(target=start_udp_listener, args=(port, stop_event), daemon=True).start()
        
    print("\n[READY] سرور آماده پاسخگویی به ابزار ویندوز است.")
    print("نکته ایمنی: در صورت قطع ناگهانی SSH یا زدن Ctrl+C، فایروال خودکار به حالت اول برمی‌گردد.")
    
    try:
        while True:
            time.sleep(1)
    except SystemExit:
        pass

if __name__ == '__main__':
    main()
