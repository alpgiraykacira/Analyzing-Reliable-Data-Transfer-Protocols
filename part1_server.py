"""
Name: Alp Giray Kaçıra
ID: 150170091
Date: 2025-06-12
"""

import socket
import sys
import random as rd

def unreliableSend(packet, sock, userIP, errRate):
    if errRate < rd.randint(0,100):
        sock.sendto(packet, userIP)

def send_with_corruption(packet, sock, userIP, corruption_rate):
    """
    Send packet with a chance of corruption.
    """
    if rd.randint(0, 100) < corruption_rate:
        # Create corrupted packet by changing first byte to type 4
        corrupt_packet = bytearray(packet)
        corrupt_packet[0] = 4  # Corrupt packet type
        # Send corrupted packet with no loss (errRate=0)
        unreliableSend(corrupt_packet, sock, userIP, 0)
        print("Sent CORRUPT packet!")
    else:
        # Send normal packet with no loss (errRate=0) - RDT 2.2 has no packet loss
        unreliableSend(packet, sock, userIP, 0)

def create_data_packet(seq_num, data):
    """Create DATA packet: [type=2, payload_len, seq_num, data]"""
    packet = bytearray()
    packet.append(2)  # Packet type = 2
    data_bytes = data.encode('utf-8')
    payload_len = min(len(data_bytes), 253)  # Max 253 bytes for payload
    packet.append(payload_len)  # Payload length
    packet.append(seq_num)  # Sequence number
    packet.extend(data_bytes[:payload_len])  # Data
    return packet

def create_fin_packet(seq_num):
    """Create FIN packet: [type=3, seq_num]"""
    packet = bytearray()
    packet.append(3)  # Packet type = 3
    packet.append(seq_num)  # Sequence number
    return packet

def parse_packet(data):
    """Parse received packet"""
    if len(data) < 2:
        return None
    
    packet_type = data[0]
    
    if packet_type == 0:  # Handshake packet
        if len(data) < 2:
            return None
        payload_length = data[1]
        if len(data) < 2 + payload_length:
            return None
        filename = data[2:2+payload_length].decode('utf-8', errors='ignore')
        return {'type': 'HANDSHAKE', 'filename': filename}
    elif packet_type == 1:  # ACK packet
        seq_num = data[1]
        return {'type': 'ACK', 'seq_num': seq_num}
    elif packet_type == 4:  # Corrupt packet
        return {'type': 'CORRUPT'}
    
    return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python part1_server.py <error_rate>")
        sys.exit(1)
    
    corruption_rate = int(sys.argv[1])  # This is corruption rate for RDT 2.2
    
    # Server setup
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('localhost', 12000))
    # RDT 2.2: Longer timeout since no packet loss expected
    server_socket.settimeout(10.0)
    
    print(f"RDT 2.2 Server listening on localhost:12000 with corruption rate {corruption_rate}%")
    
    while True:
        try:
            # Wait for handshake
            print("Waiting for handshake...")
            data, client_addr = server_socket.recvfrom(1024)
            packet = parse_packet(data)
            
            if packet is None or packet['type'] == 'CORRUPT':
                print("Received corrupted handshake, ignoring...")
                continue
            
            if packet['type'] == 'HANDSHAKE':
                filename = packet['filename']
                print(f"Received handshake for file: {filename}")
                
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    print(f"File loaded with {len(lines)} lines")
                    
                    # Send data using RDT 2.2 protocol
                    seq_num = 0
                    line_index = 0
                    
                    while line_index < len(lines):
                        # Send data packet with potential corruption
                        data_packet = create_data_packet(seq_num, lines[line_index])
                        print(f"Sending DATA packet {seq_num}: {lines[line_index][:50]}...")
                        send_with_corruption(data_packet, server_socket, client_addr, corruption_rate)
                        
                        # Wait for ACK - RDT 2.2 behavior (no timeout needed, but keep for robustness)
                        ack_received = False
                        retransmit_count = 0
                        max_retransmits = 5  # Reduced since no packet loss
                        
                        while not ack_received and retransmit_count < max_retransmits:
                            try:
                                ack_data, _ = server_socket.recvfrom(1024)
                                ack_packet = parse_packet(ack_data)
                                
                                if ack_packet is None or ack_packet['type'] == 'CORRUPT':
                                    print("Received corrupted ACK, retransmitting...")
                                    retransmit_count += 1
                                    send_with_corruption(data_packet, server_socket, client_addr, corruption_rate)
                                    continue
                                
                                if ack_packet['type'] == 'ACK':
                                    if ack_packet['seq_num'] == seq_num:
                                        print(f"Received correct ACK {seq_num}")
                                        ack_received = True
                                        line_index += 1
                                        seq_num = (seq_num + 1) % 256
                                    else:
                                        # Check if this is a NAK (ACK for previous packet)
                                        expected_prev_ack = (seq_num - 1) % 256
                                        if ack_packet['seq_num'] == expected_prev_ack:
                                            print(f"Received NAK (ACK {ack_packet['seq_num']}), retransmitting packet {seq_num}")
                                        else:
                                            print(f"Received unexpected ACK {ack_packet['seq_num']}, expected {seq_num}")
                                        
                                        retransmit_count += 1
                                        send_with_corruption(data_packet, server_socket, client_addr, corruption_rate)
                                
                            except socket.timeout:
                                print(f"ACK timeout for packet {seq_num} (rare in RDT 2.2), retransmitting...")
                                retransmit_count += 1
                                send_with_corruption(data_packet, server_socket, client_addr, corruption_rate)
                        
                        if retransmit_count >= max_retransmits:
                            print(f"Max retransmits reached for packet {seq_num}, moving to next")
                            line_index += 1
                            seq_num = (seq_num + 1) % 256
                    
                    # Send FIN packet with potential corruption
                    print("Sending FIN packet...")
                    fin_packet = create_fin_packet(seq_num)
                    fin_retries = 0
                    max_fin_retries = 3  # Reduced since no packet loss
                    
                    while fin_retries < max_fin_retries:
                        send_with_corruption(fin_packet, server_socket, client_addr, corruption_rate)
                        
                        # Wait for FIN ACK
                        try:
                            fin_ack_data, _ = server_socket.recvfrom(1024)
                            fin_ack_packet = parse_packet(fin_ack_data)
                            if fin_ack_packet and fin_ack_packet['type'] == 'ACK' and fin_ack_packet['seq_num'] == seq_num:
                                print("Received FIN ACK - transmission complete")
                                break
                            else:
                                print("Received invalid FIN ACK, retrying...")
                                fin_retries += 1
                        except socket.timeout:
                            fin_retries += 1
                            print(f"FIN ACK timeout (rare in RDT 2.2), retry {fin_retries}")
                    
                    if fin_retries >= max_fin_retries:
                        print("FIN ACK timeout, but considering transmission complete")
                    
                    print(f"File transmission completed")
                    break
                    
                except FileNotFoundError:
                    print(f"File {filename} not found")
                    break
                except Exception as e:
                    print(f"Error reading file: {e}")
                    break
            
        except socket.timeout:
            print("No handshake received, continuing to wait...")
            continue
        except Exception as e:
            print(f"Server error: {e}")
            break
    
    server_socket.close()

if __name__ == "__main__":
    main()