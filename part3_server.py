"""
Name: Alp Giray Kaçıra
ID: 150170091
Date: 2025-06-12
"""

import socket
import sys
import time
import os

class TCPServer:
    def __init__(self, port=12000, error_rate=0):
        self.port = port
        self.error_rate = error_rate  # For consistency with other parts
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('localhost', self.port))
        self.buffer_size = 4096
        
    def handle_client(self):
        print(f"TCP Server started on port {self.port} (error_rate parameter: {self.error_rate}% - ignored)")
        self.socket.listen(5)
        
        while True:
            try:
                client_socket, client_addr = self.socket.accept()
                print(f"Connection established with {client_addr}")
                
                # Receive filename request
                filename_data = client_socket.recv(1024).decode('utf-8')
                filename = filename_data.strip()
                
                print(f"Client requested file: {filename}")
                
                # Check if file exists
                if os.path.exists(filename):
                    # Send file size first
                    file_size = os.path.getsize(filename)
                    client_socket.send(f"{file_size}".encode('utf-8'))
                    
                    # Wait for acknowledgment
                    ack = client_socket.recv(1024).decode('utf-8')
                    if ack == "READY":
                        # Send entire file content
                        self.send_file(client_socket, filename)
                        print(f"File {filename} sent successfully")
                    else:
                        print("Client not ready to receive file")
                        
                else:
                    # Send error message
                    client_socket.send(b"ERROR: File not found")
                    print(f"File {filename} not found")
                
                client_socket.close()
                print("Connection closed")
                break  # Handle one client then exit
                
            except Exception as e:
                print(f"Error handling client: {e}")
                if 'client_socket' in locals():
                    client_socket.close()
                continue
    
    def send_file(self, client_socket, filename):
        """Send entire file using TCP socket"""
        try:
            bytes_sent = 0
            
            with open(filename, 'rb') as f:
                while True:
                    data = f.read(self.buffer_size)
                    if not data:
                        break
                    
                    client_socket.send(data)
                    bytes_sent += len(data)
                    
            print(f"File {filename} transmission completed ({bytes_sent} bytes sent)")
            
        except Exception as e:
            print(f"Error sending file: {e}")
            raise

def main():
    if len(sys.argv) != 2:
        print("Usage: python part3_server.py <error_rate>")
        print("Note: TCP provides reliable transport, but error_rate parameter required for consistency")
        sys.exit(1)
    
    try:
        error_rate = int(sys.argv[1])
        if error_rate < 0 or error_rate > 100:
            raise ValueError("Error rate must be between 0 and 100")
    except ValueError as e:
        print(f"Invalid error rate: {e}")
        sys.exit(1)
    
    server = TCPServer(error_rate=error_rate)
    
    try:
        server.handle_client()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server.socket.close()

if __name__ == "__main__":
    main()