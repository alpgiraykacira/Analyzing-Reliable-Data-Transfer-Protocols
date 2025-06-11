"""
Name: Alp Giray Kaçıra
ID: 150170091
Date: 2025-06-12
"""

import socket
import sys
import time
import random as rd

def unreliableSend(packet, sock, userIP, errRate):
    if errRate < rd.randint(0, 100):
        sock.sendto(packet, userIP)

class RDT3Server:
    def __init__(self, port=12345, err_rate=0):
        self.port = port
        self.err_rate = err_rate
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('localhost', self.port))
        self.buffer_size = 1024
        
    def create_ack_packet(self, seq_num):
        """Create ACK packet: [type=1, seq_num]"""
        return bytes([1, seq_num])
    
    def create_fin_packet(self, seq_num):
        """Create FIN packet: [type=3, seq_num]"""
        return bytes([3, seq_num])
    
    def parse_packet(self, packet):
        """Parse incoming packet and return type, payload"""
        if len(packet) < 1:
            return None, None, None
            
        packet_type = packet[0]
        
        if packet_type == 0:  # Handshake
            if len(packet) < 2:
                return 0, None, None
            payload_len = packet[1]
            filename = packet[2:2+payload_len].decode('utf-8')
            return 0, filename, None
        
        elif packet_type == 1: # ACK packet
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
            
        elif packet_type == 4:  # Corrupt packet
            return 4, None, None
            
        return packet_type, None, None
    
    def handle_client(self):
        print(f"Server started on port {self.port} with error rate {self.err_rate}%")

        try:
            # Wait for handshake
            data, client_addr = self.socket.recvfrom(self.buffer_size)
            packet_type, filename, _ = self.parse_packet(data)

            if packet_type == 0 and filename:
                print(f"Received handshake request for file: {filename}")

                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    print(f"File found with {len(lines)} lines")

                    # Send ACK for handshake
                    ack_packet = self.create_ack_packet(0)
                    unreliableSend(ack_packet, self.socket, client_addr, self.err_rate)

                    # Send file line by line using Go-Back-N
                    self.send_file_gbn(lines, client_addr)

                except FileNotFoundError:
                    print(f"File {filename} not found")

        except Exception as e:
            print(f"Error handling client: {e}")

    
    def send_file_gbn(self, lines, client_addr):
        """Send file using Go-Back-N protocol with proper window management"""
        N = 1  # Initial window size
        base = 0
        next_seq = 0
        sent_packets = {}
        timeout = 2.0
        total_lines = len(lines)
        last_window_start = 0

        # Create window size log
        window_log = open("window_size_log.txt", "w")
        window_log.write("timestamp,N\n")
        window_log.write(f"{time.time()},{N}\n")
        window_log.flush()
        
        while base < total_lines:
            # Send packets within window
            while next_seq < base + N and next_seq < total_lines:
                line = lines[next_seq].rstrip('\n')
                
                # Create data packet
                line_bytes = line.encode('utf-8')
                payload_len = min(len(line_bytes), 253)
                data_packet = bytes([2, payload_len, next_seq % 256]) + line_bytes[:payload_len]
                
                # Send packet
                unreliableSend(data_packet, self.socket, client_addr, self.err_rate)
                sent_packets[next_seq] = data_packet
                
                print(f"Sent packet {next_seq} (seq {next_seq % 256}), window size: {N}, base: {base}")
                next_seq += 1
            
            # Wait for ACK with timeout
            self.socket.settimeout(timeout)
            
            try:
                data, addr = self.socket.recvfrom(self.buffer_size)
                packet_type, _, ack_seq = self.parse_packet(data)
                
                if packet_type == 1:  # ACK received
                    print(f"Received ACK for packet {ack_seq}")
                    
                    # Calculate how many packets were acknowledged
                    old_base = base
                    
                    # Move base forward based on cumulative ACK
                    # ACK seq_num acknowledges all packets up to and including seq_num
                    while base < total_lines and (base % 256) != ((ack_seq + 1) % 256):
                        base += 1
                    
                    packets_acked = base - old_base
                    
                    if packets_acked > 0:
                        print(f"Base moved from {old_base} to {base} ({packets_acked} packets acknowledged)")
                        
                        # Check if we completed a transmission round (window fully acknowledged)
                        if base >= last_window_start + N:
                            # Increase window size additively after successful round
                            N = min(N + 1, 100)
                            last_window_start = base
                            print(f"Transmission round completed, window size increased to: {N}")
                            window_log.write(f"{time.time()},{N}\n")
                            window_log.flush()
                    
            except socket.timeout:
                print(f"Timeout occurred, resending from base {base}")
                
                # Halve window size on timeout
                old_N = N
                N = max(N // 2, 1)
                if N != old_N:
                    print(f"Window size halved from {old_N} to {N}")
                    window_log.write(f"{time.time()},{N}\n")
                    window_log.flush()
                
                # Reset transmission round tracking
                last_window_start = base
                
                # Resend packets from base
                next_seq = base
                
            except Exception as e:
                print(f"Error receiving ACK: {e}")
                next_seq = base
        
        # Send FIN packet
        fin_packet = self.create_fin_packet(total_lines % 256)
        fin_retries = 0
        max_fin_retries = 5
        
        while fin_retries < max_fin_retries:
            unreliableSend(fin_packet, self.socket, client_addr, self.err_rate)
            print("Sent FIN packet")
            
            # Wait for FIN ACK
            self.socket.settimeout(3.0)
            try:
                data, addr = self.socket.recvfrom(self.buffer_size)
                packet_type, _, ack_seq = self.parse_packet(data)
                
                if packet_type == 1 and ack_seq == total_lines % 256:
                    print("Received FIN ACK - transmission complete")
                    break
                else:
                    fin_retries += 1
                    
            except socket.timeout:
                fin_retries += 1
                print(f"FIN ACK timeout, retry {fin_retries}")
        
        window_log.close()
        print("File transfer completed")

def main():
    if len(sys.argv) != 2:
        print("Usage: python part2_server.py <error_rate>")
        sys.exit(1)
    
    try:
        err_rate = int(sys.argv[1])
        if err_rate < 0 or err_rate > 100:
            raise ValueError("Error rate must be between 0 and 100")
    except ValueError as e:
        print(f"Invalid error rate: {e}")
        sys.exit(1)
    
    server = RDT3Server(err_rate=err_rate)
    server.handle_client()

if __name__ == "__main__":
    main()