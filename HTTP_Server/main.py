import socket
import sys
import time
from datetime import datetime
import threading
from os import path
from func import parse_headers


def generate_headers(response_code, length=0):
    """
    Generate HTTP response headers.
    Parameters:
        - response_code: HTTP response code to add to the header. 200 and 404 supported
    Returns:
        A formatted HTTP header for the given response_code
    """
    header = ''
    if response_code == 200:
        header += 'HTTP/1.1 200 OK\n'
    elif response_code == 304:
        header += 'HTTP/1.1 304 Not Modified\n'
    elif response_code == 400:
        header += 'HTTP/1.1 400 Bad Request\n'
    elif response_code == 404:
        header += 'HTTP/1.1 404 Not Found\n'
    elif response_code == 500:
        header += 'HTTP/1.1 500 Server Error\n'

    time_now = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    header += 'Date: {now}\n'.format(now=time_now)
    header += 'Server: CN Assignment 1 O. Vandenryt\n'
    header += 'Content-Length: {length}\n'.format(length=str(length))
    header += 'Connection: keep-alive\n\n'  # Signal that connection will be kept alive
    return header


class WebServer(object):
    """
    Class for describing simple HTTP server objects
    """

    def __init__(self, port=8000):
        self.s = None
        self.host = 'localhost'  # Default to any available network interface
        self.port = port
        self.content_dir = 'web'  # Directory where webpage files are stored

    def start(self):
        """
        Attempts to create and bind a socket to launch the server
        """
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        try:
            print("Starting server on {host}:{port}".format(host=self.host, port=self.port))
            self.s.bind((self.host, self.port))
            print("Server started on port {port}.".format(port=self.port))

        except socket.error:
            print("Error: Could not bind to port {port}".format(port=self.port))
            self.shutdown()
            sys.exit(1)

        self._listen()  # Start listening for connections

    def shutdown(self):
        """
        Shuts down the server
        """
        try:
            print("Shutting down server")
            self.s.shutdown(socket.SHUT_RDWR)

        except socket.error:
            pass  # Pass if socket is already closed

    def _listen(self):
        """
        Listens on self.port for any incoming connections
        """
        self.s.listen()
        while True:
            (client, address) = self.s.accept()
            client.settimeout(10)
            print("Received connection from {address}".format(address=address))
            threading.Thread(target=self._handle_client, args=(client,)).start()

    def _handle_client(self, client):
        """
        Main loop for handling connecting clients, serving files from content_dir and modifying files
        Parameters:
            - client: socket client from accept()
        """
        PACKET_SIZE = 1024
        while True:
            try:
                data = client.recv(PACKET_SIZE).decode()  # Receive data packet from client and decode
                if not data:
                    break
                request_method = data.split(' ')[0]
                print("Method: {m}".format(m=request_method))
                if request_method == "GET" or request_method == "HEAD":
                    headers = parse_headers(data, client=False, server=True)

                    if 'Host' not in headers or self.host not in headers['Host']:
                        if 'HTTP/1.1' in data:
                            response_data = b""
                            if request_method == "GET":  # Temporary 404 Response Page
                                response_data = b"<html><body><center><h1>Error 400: Bad Request</h1><img " \
                                                b"src='https://http.cat/400'></center></body></html> "
                            response_header = generate_headers(400, len(response_data))
                            response = response_header.encode()
                            response += response_data
                            client.send(response)
                            break

                    file_requested = data.split(' ')[1]
                    file_requested = file_requested.split('?')[0]

                    if file_requested == "/":
                        file_requested = "/index.html"
                    elif '.' not in file_requested:
                        file_requested += '.html'

                    filepath_to_serve = self.content_dir + file_requested
                    print("Serving web page [{fp}]".format(fp=filepath_to_serve))
                    print(threading.current_thread().name)
                    # Check modified since header
                    if 'If-Modified-Since' in headers.keys():
                        last_m_time = path.getmtime('./web' + file_requested)
                        utc_time = datetime.strptime(headers['If-Modified-Since'][2:], "%a, %d %b %Y %H:%M:%S GMT")
                        required_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
                        if last_m_time <= required_time:
                            response_header = generate_headers(304)
                            client.send(response_header.encode())
                            break
                    # Load and Serve files content
                    response_data = b""
                    response_length = 0
                    try:
                        f = open(filepath_to_serve, 'rb')
                        if request_method == "GET":  # Read only for GET
                            response_data = f.read()
                            response_length = len(response_data)
                        f.close()
                        response_header = generate_headers(200, response_length)

                    except FileNotFoundError:
                        print("File not found. Serving 404 page.")
                        response_header = generate_headers(404, 119)
                        if request_method == "GET":  # Temporary 404 Response Page
                            response_data = b"<html><body><center><h1>Error 404: File not found</h1><img " \
                                            b"src='http://localhost:8000/404.jpg'></center></body></html> "
                    response = response_header.encode()
                    if request_method == "GET":
                        response += response_data
                    client.send(response)
                elif request_method == "POST":
                    body = data.split('\r\n\r\n')[1]
                    file_requested = data.split(' ')[1]
                    if file_requested == "/":
                        file_requested = "/index.txt"
                    filepath_to_serve = self.content_dir + file_requested
                    try:
                        f = open(filepath_to_serve, 'a')
                        f.write(body)
                        f.close()
                        response_header = generate_headers(200)
                        client.send(response_header.encode())
                        break
                    except Exception as e:
                        response_data = b"<html><body><center><h1>Error 500: Server Error</h1>" + b"<h2>" +\
                                        str(e).encode() + b"</h2><img src='https://http.cat/500'></center></body" \
                                        b"></html> "
                        response_header = generate_headers(500, len(response_data))
                        response = response_header.encode() + response_data
                        client.send(response)
                        print(e)
                        break
                elif request_method == "PUT":
                    body = data.split('\r\n\r\n')[1]
                    name = time.strftime("%d %b %Y %H-%M-%S", time.localtime())
                    filepath_to_serve = self.content_dir + '/' + name + '.txt'
                    try:
                        f = open(filepath_to_serve, 'w')
                        f.write(body)
                        f.close()
                        response_header = generate_headers(200)
                    except Exception as e:
                        response_data = b"<html><body><center><h1>Error 500: Server Error</h1>" + b"<h2>" + \
                                        str(e).encode() + b"</h2><img src='https://http.cat/500'></center></body" \
                                                          b"></html> "
                        response_header = generate_headers(500, len(response_data))
                        response = response_header.encode() + response_data
                        client.send(response)
                        print(e)
                        break
                    client.send(response_header.encode())
                else:
                    response_data = b"<html><body><center><h1>Error 400: Bad Request</h1><img " \
                                    b"src='https://http.cat/400'></center></body></html> "
                    response_header = generate_headers(400, len(response_data))
                    response = response_header.encode()
                    response += response_data
                    client.send(response)
                    break
            except socket.error as error:
                e = str(error)
                response_data = b"<html><body><center><h1>Error 500: Server Error</h1>" + b"<h2>" + e.encode() + \
                                b"</h2><img src='https://http.cat/500'></center></body></html> "
                response_header = generate_headers(500, len(response_data))
                response = response_header.encode() + response_data
                client.send(response)
                break


if __name__ == '__main__':
    server = WebServer()
    server.start()
