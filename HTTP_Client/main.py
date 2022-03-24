import sys
import socket


# Checks for chunked encoding
def parse_headers(resp: str):
    headers_dict = dict()
    http_resp, crlf, http_rheaders = resp.partition('\r\n')
    if http_resp[-6] == '2':
        http_headers = http_rheaders.split('\r\n')
        for header in http_headers:
            if header != '':
                key, content = header.split(':', 1)
                headers_dict.update({key: content})
        return headers_dict


def is_chunk_based(headers):
    if 'Transfer-Encoding' in headers:
        if headers['Transfer-Encoding'] == ' chunked':
            return True
    return False


# HEAD Request
def head(s, host):
    request = 'HEAD / HTTP/1.1\r\nHost: ' + host + '\r\n\r\n'
    s.send(request.encode())
    response = s.recv(1024).decode()
    print(response)
    headers = parse_headers(response)
    print(is_chunk_based(headers))


# GET Request
def get(s, host):
    request = 'GET / HTTP/1.1\r\nHost: ' + host + '\r\n\r\n'
    s.send(request.encode())
    response = s.recv(1024).decode().split('\r\n\r\n')
    headers = parse_headers(response[0])
    chunk_length = response[1].splitlines()[0]
    body = response[1].splitlines()[1]
    if is_chunk_based(headers):
        while True:
            chunk = s.recv(1024)
            if len(chunk) == 0:  # No more data received, quitting
                break
            body = body + chunk


def post(arg: list):
    pass


def put(arg: list):
    pass


def run(arg: list):
    (host, port) = (arg[1], int(arg[2]))
    # Notice user optional arguments are ignored
    if len(arg) > 3:
        print('Ignoring optional arguments: ' + str(arg[3:]))
    if arguments[0] == 'HEAD':
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            head(s, host)
    elif arguments[0] == 'GET':
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            get(s, host)
    elif arguments[0] == 'POST':
        post(arg)
    elif arguments[0] == 'PUT':
        put(arg)
    else:
        raise Exception('Unknown method: \'' + arguments[0] + '\'')


if __name__ == '__main__':
    arguments = sys.argv[1:]
    # custom port
    if len(arguments) == 2:
        PORT = arguments.append(str(80))
        run(arguments)
    elif len(arguments) < 2:
        raise Exception('Host or method not described')
    else:
        run(arguments)
