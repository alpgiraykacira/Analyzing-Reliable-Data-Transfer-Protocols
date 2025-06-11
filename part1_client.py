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
    if errRate < rd.randint(0,100):
        sock.sendto(packet, userIP)

def create_handshake_packet(filename):
    """Create handshake packet: [type=0, payload_len, filename]"""
    packet = bytearray()
    packet.append(0)  # Packet type = 0
    packet.append(len(filename.encode('utf-8')))  # Payload length
    packet.extend(filename.encode('utf-8'))  # Filename
    return packet

def create_ack_packet(seq_num):
    """Create ACK packet: [type=1, seq_num]"""
    packet = bytearray()
    packet.append(1)  # Packet type = 1
    packet.append(seq_num)  # Sequence number
    return packet

def parse_packet(data):
    """Parse received packet"""
    if len(data) < 2:
        return None
    
    packet_type = data[0]
    
    if packet_type == 2:  # DATA packet
        if len(data) < 3:
            return None
        payload_length = data[1]
        seq_num = data[2]
        if len(data) < 3 + payload_length:
            return None
        payload = data[3:3+payload_length].decode('utf-8', errors='ignore')
        return {'type': 'DATA', 'seq_num': seq_num, 'payload': payload}
    elif packet_type == 3:  # FIN packet
        seq_num = data[1]
        return {'type': 'FIN', 'seq_num': seq_num}
    elif packet_type == 4:  # Corrupt packet
        return {'type': 'CORRUPT'}
    
    return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python part1_client.py <error_rate>")
        sys.exit(1)
    
    error_rate = int(sys.argv[1])
    
    # Client setup
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(1.0)
    
    server_address = ('localhost', 12000)
    filename = "crime-and-punishment.txt" # File to request
    
    # For RDT 2.2: NO packet loss, only corruption handled by server
    # Client always uses errRate=0 (no loss) in unreliableSend
    loss_rate = 0
    
    # Send handshake with retries
    handshake_packet = create_handshake_packet(filename)
    print(f"Sending handshake for file: {filename}")
    
    handshake_sent = False
    handshake_retries = 0
    max_handshake_retries = 10
    
    while not handshake_sent and handshake_retries < max_handshake_retries:
        unreliableSend(handshake_packet, client_socket, server_address, loss_rate)
        handshake_retries += 1
        
        try:
            data, addr = client_socket.recvfrom(1024)
            handshake_sent = True
            first_packet_data = data
            break
        except socket.timeout:
            print(f"Handshake timeout, retry {handshake_retries}")
            continue
    
    if not handshake_sent:
        print("Failed to establish connection after maximum handshake retries")
        client_socket.close()
        return
    
    expected_seq = 0
    received_data = []
    last_ack_sent = -1
    
    start_time = time.time()
    consecutive_timeouts = 0
    max_consecutive_timeouts = 20
    
    # Process the first packet we already received
    packet = parse_packet(first_packet_data)
    if packet and packet['type'] == 'DATA' and packet['seq_num'] == expected_seq:
        received_data.append(packet['payload'])
        print(f"Received DATA packet {packet['seq_num']}: {packet['payload'][:50]}...")
        ack_packet = create_ack_packet(expected_seq)
        print(f"Sending ACK {expected_seq}")
        unreliableSend(ack_packet, client_socket, server_address, loss_rate)
        last_ack_sent = expected_seq
        expected_seq = (expected_seq + 1) % 256
        consecutive_timeouts = 0
    
    while True:
        try:
            data, addr = client_socket.recvfrom(1024)
            consecutive_timeouts = 0
            packet = parse_packet(data)
            
            if packet is None or packet['type'] == 'CORRUPT':
                # Send NAK (duplicate ACK for previous sequence) - RDT 2.2 behavior
                nak_seq = (expected_seq - 1) % 256
                if nak_seq != last_ack_sent:
                    ack_packet = create_ack_packet(nak_seq)
                    print(f"Sending NAK (ACK {nak_seq}) for corrupted packet")
                    unreliableSend(ack_packet, client_socket, server_address, loss_rate)
                    last_ack_sent = nak_seq
                continue
            
            if packet['type'] == 'DATA':
                if packet['seq_num'] == expected_seq:
                    # Correct packet received
                    received_data.append(packet['payload'])
                    print(f"Received DATA packet {packet['seq_num']}: {packet['payload'][:50]}...")
                    
                    # Send ACK using unreliableSend
                    ack_packet = create_ack_packet(expected_seq)
                    print(f"Sending ACK {expected_seq}")
                    unreliableSend(ack_packet, client_socket, server_address, loss_rate)
                    last_ack_sent = expected_seq
                    
                    expected_seq = (expected_seq + 1) % 256
                else:
                    # Wrong sequence number, send ACK for last correctly received packet
                    ack_seq = (expected_seq - 1) % 256
                    if ack_seq != last_ack_sent:
                        ack_packet = create_ack_packet(ack_seq)
                        print(f"Wrong sequence {packet['seq_num']}, expected {expected_seq}. Sending ACK {ack_seq}")
                        unreliableSend(ack_packet, client_socket, server_address, loss_rate)
                        last_ack_sent = ack_seq
            
            elif packet['type'] == 'FIN':
                print("Received FIN packet - transmission complete")
                # Send ACK for FIN using unreliableSend
                ack_packet = create_ack_packet(packet['seq_num'])
                unreliableSend(ack_packet, client_socket, server_address, loss_rate)
                break
                
        except socket.timeout:
            consecutive_timeouts += 1
            print(f"Timeout waiting for packet ({consecutive_timeouts}/{max_consecutive_timeouts})")
            
            # Send duplicate ACK to help server if we're waiting too long
            if consecutive_timeouts % 3 == 0 and last_ack_sent >= 0:
                ack_packet = create_ack_packet(last_ack_sent)
                print(f"Sending duplicate ACK {last_ack_sent} due to timeout")
                unreliableSend(ack_packet, client_socket, server_address, loss_rate)
            
            if consecutive_timeouts >= max_consecutive_timeouts:
                print("Too many consecutive timeouts, ending transfer")
                break
            continue
        except Exception as e:
            print(f"Error: {e}")
            break
    
    end_time = time.time()
    total_time = end_time - start_time

    print(f"Total time: {total_time:.2f} seconds")
    print(f"Received {len(received_data)} lines")
    
    # Save received file
    output_filename = f"rdt2.2_received_{filename}_for_error_rate_{error_rate}.txt"
    with open(output_filename, 'w', encoding='utf-8') as f:
        for line in received_data:
            f.write(line)
    
    print(f"File saved as: {output_filename}")
    
    client_socket.close()

if __name__ == "__main__":
    main()