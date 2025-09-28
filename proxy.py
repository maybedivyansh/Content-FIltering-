import socket
import os
import mimetypes

HOST = '127.0.0.1'
PORT = 8888

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

print(f"[*] Listening on {HOST}:{PORT}")

while True:
    client_socket, addr = server_socket.accept()
    print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")
    
    request_data = client_socket.recv(4096).decode('utf-8', errors='ignore')
    
    if not request_data:
        continue
    
    print("[*] Received request:\n" + request_data.split('\n')[0]) # Print just the first line
    
    first_line = request_data.split('\n')[0]
    filename = first_line.split(' ')[1]
    
    if filename == '/':
        filename = '/index.html'
    
    clean_filename = filename.lstrip('/')
    if clean_filename == '':
        clean_filename = 'index.html'

    # Prevent directory traversal
    clean_filename = os.path.normpath(clean_filename)
    if clean_filename.startswith('..'):
        clean_filename = 'index.html'

    print(f"[*] Parsed filename: {clean_filename}")

    # --- Serve static files with correct content types; filter only HTML via blacklist ---
    try:
        mime_type, _ = mimetypes.guess_type(clean_filename)
        if mime_type is None:
            # Default to binary stream; handle common cases explicitly below
            mime_type = 'application/octet-stream'

        ext = os.path.splitext(clean_filename)[1].lower()

        if ext in ('', '.html', '.htm'):
            with open(clean_filename, 'r', encoding='utf-8', errors='ignore') as f:
                content_text = f.read()

            # Read blacklist and filter only HTML content
            with open('blacklist.txt', 'r', encoding='utf-8', errors='ignore') as f:
                keywords = [line.strip() for line in f if line.strip()]

            found_keyword = None
            for keyword in keywords:
                if keyword in content_text:
                    found_keyword = keyword
                    break

            if found_keyword:
                print(f"[!] Keyword '{found_keyword}' found. Blocking access.")
                response_body_bytes = b"<h1>403 Forbidden</h1><p>Access denied: Content is blocked by proxy.</p>"
                response_headers = (
                    "HTTP/1.1 403 Forbidden\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n\r\n"
                )
            else:
                print("[+] No keywords found. Allowing access.")
                response_body_bytes = content_text.encode('utf-8')
                response_headers = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n\r\n"
                )
        else:
            # Binary/static assets (images, css, js, ico, etc.)
            if ext in ('.svg',):
                # Ensure correct mime for SVG specifically
                mime_type = 'image/svg+xml'
            with open(clean_filename, 'rb') as f:
                response_body_bytes = f.read()
            response_headers = (
                f"HTTP/1.1 200 OK\r\nContent-Type: {mime_type}\r\n\r\n"
            )
            
    except FileNotFoundError:
        print(f"[!] File not found: {clean_filename}. Sending 404.")
        response_body = "<h1>404 Not Found</h1>"
        response_headers = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n"

    # Send headers and body correctly for text/binary
    client_socket.sendall(response_headers.encode('utf-8'))
    client_socket.sendall(response_body_bytes)
    
    client_socket.close()