"""
Name: Alp Giray Kaçıra
ID: 150170091
Date: 2025-06-12
"""

import socket
import sys
import time

class TCPClient:
    def __init__(self, server_host='localhost', server_port=12000, error_rate=0):
        self.server_host = server_host
        self.server_port = server_port
        self.error_rate = error_rate  # For consistency with other parts
        self.buffer_size = 4096
        
    def request_file(self, filename):
        """Request and receive file using TCP socket"""
        print(f"Requesting file: {filename} using TCP (error_rate parameter: {self.error_rate}% - ignored)")
        
        start_time = time.time()
        
        try:
            # Create TCP connection
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((self.server_host, self.server_port))
            
            print(f"Connected to server at {self.server_host}:{self.server_port}")
            
            # Send filename request
            client_socket.send(filename.encode('utf-8'))
            
            # Receive file size or error message
            response = client_socket.recv(1024).decode('utf-8')
            
            if response.startswith("ERROR"):
                print(f"Server error: {response}")
                return None
            
            try:
                file_size = int(response)
                print(f"File size: {file_size} bytes")
                
                # Send ready acknowledgment
                client_socket.send(b"READY")
                
                # Receive file content
                received_data = self.receive_file(client_socket, file_size)
                
                if received_data:
                    # Save received file
                    output_filename = f"tcp_received_{filename}_for_error_rate_{self.error_rate}.txt"
                    with open(output_filename, 'wb') as f:
                        f.write(received_data)
                    
                    end_time = time.time()
                    total_time = end_time - start_time
                    
                    print(f"File received successfully in {total_time:.2f} seconds")
                    print(f"File saved as: {output_filename}")
                    print(f"Received {len(received_data)} bytes")
                    
                    return total_time
                else:
                    print("Failed to receive file")
                    return None
                    
            except ValueError:
                print(f"Invalid response from server: {response}")
                return None
                
        except Exception as e:
            print(f"Error during file transfer: {e}")
            return None
            
        finally:
            if 'client_socket' in locals():
                client_socket.close()
    
    def receive_file(self, client_socket, expected_size):
        """Receive file data from TCP socket"""
        received_data = b""
        bytes_received = 0
        
        print("Receiving file data...")
        
        try:
            while bytes_received < expected_size:
                chunk = client_socket.recv(min(self.buffer_size, expected_size - bytes_received))
                
                if not chunk:
                    print("Connection closed by server")
                    break
                
                received_data += chunk
                bytes_received += len(chunk)
                
                # Progress indicator
                progress = (bytes_received / expected_size) * 100
                if bytes_received % (self.buffer_size * 10) == 0 or bytes_received == expected_size:
                    print(f"Progress: {progress:.1f}% ({bytes_received}/{expected_size} bytes)")
            
            if bytes_received == expected_size:
                print("File received completely")
                return received_data
            else:
                print(f"Incomplete file received: {bytes_received}/{expected_size} bytes")
                return received_data if received_data else None
                
        except Exception as e:
            print(f"Error receiving file: {e}")
            return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python part3_client.py <error_rate>")
        print("Note: TCP provides reliable transport, but error_rate parameter required for consistency")
        sys.exit(1)
    
    try:
        error_rate = int(sys.argv[1])
        if error_rate < 0 or error_rate > 100:
            raise ValueError("Error rate must be between 0 and 100")
    except ValueError as e:
        print(f"Invalid error rate: {e}")
        sys.exit(1)
    
    filename = "crime-and-punishment.txt"  # File to request
    
    client = TCPClient(error_rate=error_rate)
    
    try:
        transfer_time = client.request_file(filename)
        
        if transfer_time:
            print(f"\nTransfer Statistics:")
            print(f"Total time: {transfer_time:.2f} seconds")
            print(f"Protocol: TCP (reliable)")
            print(f"Error rate parameter: {error_rate}% (ignored by TCP)")
        else:
            print("File transfer failed")
            
    except KeyboardInterrupt:
        print("\nTransfer interrupted by user")
    except Exception as e:
        print(f"Client error: {e}")

if __name__ == "__main__":
    main()