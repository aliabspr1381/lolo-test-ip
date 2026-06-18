#!/usr/bin/env python3
import socket
import threading
import subprocess
import os
import sys
import time
import atexit
import signal

# Test Ports
PORTS = [80, 443, 53, 123, 500, 4500, 3074, 8080, 8443, 55424]

fw_originally_active = False
active_test_ports = []

def is_port_in_use(port):
    """Checks if a port is occupied by another process"""
    # TCP Check
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            return True
    # UDP Check
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

def get_ufw_status():
    """Checks UFW firewall state"""
    try:
        output = subprocess.check_output(["sudo", "ufw", "status"], stderr=subprocess.STDOUT).decode()
        if "Status: active" in output:
            return True
    except Exception:
        pass
    return False

def manage_firewall_rules(ports, action='allow'):
    """Applies or removes firewall rules"""
    for port in ports:
        try:
            subprocess.run(["sudo", "ufw", action, str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def cleanup_and_rollback():
    """Rollbacks firewall changes on exit"""
    global fw_originally_active, active_test_ports
    if fw_originally_active and active_test_ports:
        print("\n🔄 [SAFETY SYSTEM] Cleaning test rules and restoring firewall...")
        manage_firewall_rules(active_test_ports, 'delete')
        subprocess.run(["sudo", "ufw", "reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("🔒 Firewall restored to original secured state.")
    else:
        print("\n✨ Cleanup finished. No firewall changes left on the server.")

# Register cleanup function
atexit.register(cleanup_and_rollback)

def handle_signal(signum, frame):
    sys.exit(0)

# Catch terminal disconnect (SIGHUP) and user interrupts (SIGINT/SIGTERM)
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
        print("❌ Error: This script must be run with root privileges (sudo).")
        sys.exit(1)
        
    print("====================================================")
    print("🛰️ SMART NETWORK AUDITOR ENGINE (SERVER SIDE - v2026)")
    print("====================================================")
    
    # Filter busy ports
    skipped_ports = []
    for p in PORTS:
        if is_port_in_use(p):
            skipped_ports.append(p)
        else:
            active_test_ports.append(p)
            
    if skipped_ports:
        print(f"⚠️ Ports skipped (actively used by other apps): {skipped_ports}")
    print(f"✅ Idle ports ready for testing: {active_test_ports}")
    
    # Firewall logic
    fw_originally_active = get_ufw_status()
    if fw_originally_active:
        print("🔒 UFW Firewall is ACTIVE. Opening test ports temporarily...")
        manage_firewall_rules(active_test_ports, 'allow')
        subprocess.run(["sudo", "ufw", "reload"], stdout=subprocess.DEVNULL)
        print("🔓 Test ports temporarily allowed through UFW.")
    else:
        print("🔓 UFW Firewall is INACTIVE. Skipping firewall rules modification.")
        
    # Start threads
    stop_event = threading.Event()
    for port in active_test_ports:
        threading.Thread(target=start_tcp_listener, args=(port, stop_event), daemon=True).start()
        threading.Thread(target=start_udp_listener, args=(port, stop_event), daemon=True).start()
        
    print("\n[READY] Server is listening for Windows Client requests.")
    print("Safety Notice: Firewall auto-rolls back on Ctrl+C or SSH disconnection.")
    
    try:
        while True:
            time.sleep(1)
    except SystemExit:
        pass

if __name__ == '__main__':
    main()
