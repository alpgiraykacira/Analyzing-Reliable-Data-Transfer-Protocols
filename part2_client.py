"""
Name: Alp Giray Kaçıra
ID: 150170091
Date: 2025-06-12
"""

import socket
import sys
import time
import random as rd
import matplotlib.pyplot as plt
import csv

def unreliableSend(packet, sock, userIP, errRate):
    if errRate < rd.randint(0, 100):
        sock.sendto(packet, userIP)

class RDT3Client:
    def __init__(self, server_host='localhost', server_port=12345, err_rate=0):
        self.server_host = server_host
        self.server_port = server_port
        self.server_addr = (server_host, server_port)
        self.err_rate = err_rate
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.buffer_size = 1024
        self.received_lines = []
        
    def create_handshake_packet(self, filename):
        """Create handshake packet: [type=0, payload_len, filename]"""
        filename_bytes = filename.encode('utf-8')
        payload_len = len(filename_bytes)
        return bytes([0, payload_len]) + filename_bytes
    
    def create_ack_packet(self, seq_num):
        """Create ACK packet: [type=1, seq_num]"""
        return bytes([1, seq_num])
    
    def parse_packet(self, packet):
        """Parse incoming packet and return type, data, seq_num"""
        if len(packet) < 1:
            return None, None, None
            
        packet_type = packet[0]
        
        if packet_type == 1:  # ACK
            if len(packet) < 2:
                return 1, None, None
            seq_num = packet[1]
            return 1, None, seq_num
            
        elif packet_type == 2:  # Data
            if len(packet) < 3:
                return 2, None, None
            payload_len = packet[1]
            seq_num = packet[2]
            data = packet[3:3+payload_len].decode('utf-8')
            return 2, data, seq_num
            
        elif packet_type == 3:  # FIN
            if len(packet) < 2:
                return 3, None, None
            seq_num = packet[1]
            return 3, None, seq_num
            
        elif packet_type == 4:  # Corrupt packet
            return 4, None, None
            
        return packet_type, None, None
    
    def request_file(self, filename):
        """Request file from server using RDT 3.0 with Go-Back-N"""
        print(f"Requesting file: {filename} with error rate: {self.err_rate}%")
        
        start_time = time.time()
        
        # Send handshake with retries
        handshake_packet = self.create_handshake_packet(filename)
        handshake_acked = False
        handshake_retries = 0
        max_handshake_retries = 10
        
        while not handshake_acked and handshake_retries < max_handshake_retries:
            unreliableSend(handshake_packet, self.socket, self.server_addr, self.err_rate)
            handshake_retries += 1
            
            self.socket.settimeout(2.0)
            try:
                data, addr = self.socket.recvfrom(self.buffer_size)
                packet_type, _, seq_num = self.parse_packet(data)
                
                if packet_type == 1 and seq_num == 0:  # Handshake ACK
                    print("Handshake acknowledged")
                    handshake_acked = True
                    break
                    
            except socket.timeout:
                print(f"Handshake timeout, retry {handshake_retries}")
                continue
        
        if not handshake_acked:
            print("Failed to establish connection")
            return None
        
        # Receive file data
        self.receive_file_gbn()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"File transfer completed in {total_time:.2f} seconds")
        print(f"Received {len(self.received_lines)} lines")
        
        # Save received file
        output_filename = f"rdt3_received_{filename}_for_error_rate_{self.err_rate}.txt"
        with open(output_filename, 'w', encoding='utf-8') as f:
            for line in self.received_lines:
                f.write(line + '\n')
        
        print(f"File saved as: {output_filename}")
        
        # Plot window sizes
        self.plot_window_sizes_from_log()
        
        return total_time
    
    def receive_file_gbn(self):
        """Receive file using Go-Back-N protocol with cumulative ACKs"""
        expected_seq = 0
        
        while True:
            self.socket.settimeout(10.0)
            
            try:
                data, addr = self.socket.recvfrom(self.buffer_size)
                packet_type, line_data, seq_num = self.parse_packet(data)
                
                if packet_type == 2:  # Data packet
                    print(f"Received data packet {seq_num}")
                    
                    if seq_num == expected_seq % 256:
                        # Correct packet received
                        self.received_lines.append(line_data)
                        
                        # Send cumulative ACK
                        ack_packet = self.create_ack_packet(seq_num)
                        unreliableSend(ack_packet, self.socket, self.server_addr, self.err_rate)
                        print(f"Sent ACK for packet {seq_num}")
                        
                        expected_seq += 1
                        
                    else:
                        # Out of order packet, send ACK for last correctly received packet
                        if expected_seq > 0:
                            last_correct_seq = (expected_seq - 1) % 256
                            ack_packet = self.create_ack_packet(last_correct_seq)
                            unreliableSend(ack_packet, self.socket, self.server_addr, self.err_rate)
                            print(f"Out of order packet {seq_num}, sent cumulative ACK for {last_correct_seq}")
                        
                elif packet_type == 3:  # FIN packet
                    print("Received FIN packet, file transfer complete")
                    # Send ACK for FIN
                    ack_packet = self.create_ack_packet(seq_num)
                    unreliableSend(ack_packet, self.socket, self.server_addr, self.err_rate)
                    break
                    
                elif packet_type == 4:  # Corrupt packet
                    print("Received corrupt packet, ignoring")
                    # Send cumulative ACK for last correctly received packet
                    if expected_seq > 0:
                        last_correct_seq = (expected_seq - 1) % 256
                        ack_packet = self.create_ack_packet(last_correct_seq)
                        unreliableSend(ack_packet, self.socket, self.server_addr, self.err_rate)
                        
            except socket.timeout:
                print("Timeout waiting for data packet")
                break
                
            except Exception as e:
                print(f"Error receiving data: {e}")
                break
    
    def plot_window_sizes_from_log(self):
        """Plot window size changes from log file"""
        log_filename = "window_size_log.txt"
        try:
            times = []
            window_sizes = []
            with open(log_filename, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                first_time = None
                for row in reader:
                    if len(row) >= 2:
                        t, n = float(row[0]), int(row[1])
                        if first_time is None:
                            first_time = t
                        times.append(t - first_time)
                        window_sizes.append(n)

            if times and window_sizes:
                plt.figure(figsize=(10, 6))
                plt.plot(times, window_sizes, marker='o', linewidth=2, markersize=4)
                plt.xlabel("Time (s)")
                plt.ylabel("Window Size (N)")
                plt.title(f"Go-Back-N Window Size Changes (Error Rate: {self.err_rate}%)")
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plot_filename = f"window_size_for_{self.err_rate}_percent_error.png"
                plt.savefig(plot_filename)
                print(f"Window size plot saved as: {plot_filename}")
            else:
                print("No window size data to plot")
        except FileNotFoundError:
            print("Window size log file not found")
        except Exception as e:
            print(f"Error plotting window sizes: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python part2_client.py <error_rate>")
        sys.exit(1)
    
    try:
        err_rate = int(sys.argv[1])
        if err_rate < 0 or err_rate > 100:
            raise ValueError("Error rate must be between 0 and 100")
    except ValueError as e:
        print(f"Invalid error rate: {e}")
        sys.exit(1)
    
    filename = "crime-and-punishment.txt" # Change this to the file you want to request
    
    client = RDT3Client(err_rate=err_rate)
    
    try:
        transfer_time = client.request_file(filename)
        if transfer_time:
            print(f"\nTransfer Statistics:")
            print(f"Total time: {transfer_time:.2f} seconds")
            print(f"Error rate: {err_rate}%")
        
    except KeyboardInterrupt:
        print("\nTransfer interrupted by user")
    except Exception as e:
        print(f"Error during transfer: {e}")
    finally:
        client.socket.close()

if __name__ == "__main__":
    main()