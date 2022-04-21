import sys
import socket
import os
from bs4 import BeautifulSoup
import shutil
from func import parse_headers


def create_new_socket() -> socket.socket:
    """
    Return a new socket

    :return:            A new socket
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return s


def connect_socket(s: socket.socket, host: str, port: int):
    """
    Connect to a host on a socket

    :param s:           The socket on which to connect to the host
    :param host:        The host to connect to
    :param port:        The port to connect on
    """
    s.connect((host, port))


def get_encoding(headers: dict, response: str) -> str:
    """
    Parse the encoding from the headers or an HTTP response

    :param headers:     The headers
    :param response:    An HTTP response
    :return:            The charset used for encoding
    """
    if 'charset=' in headers['Content-Type']:
        charset = headers['Content-Type'].rsplit('charset=', 1)[1].lower()
        return charset
    else:
        index = response.find('charset=')
        outdex = response.find('"', index)
        charset = response[index + 8:outdex]
        return charset


def is_chunk_based(headers: dict) -> bool:
    """
    Check if the content is transferred as chunks

    :param headers:     The headers
    :return:            Bool whether the content is transferred as chunks or not
    """
    if 'Transfer-Encoding' in headers:
        if headers['Transfer-Encoding'] == ' chunked':
            return True
    return False


def read_and_decode(s: socket.socket, no_bytes: int, encoding: str) -> str:
    """
    Reads the specified number of bytes on the socket and
    decodes them using the given encoding

    :param s:           The socket on which to read
    :param no_bytes:    The number of bytes to read
    :param encoding:    The encoding in which the bytes should be decoded
    :return:            The decoded text
    """
    body = s.recv(no_bytes).decode(encoding=encoding)
    length = len(body)
    no_bytes -= length
    if no_bytes <= 0:
        return body.strip('\r\n')
    else:
        while no_bytes > 0:
            new_text = s.recv(no_bytes).decode(encoding=encoding)
            body += new_text
            no_bytes -= len(new_text)
        return body


def get_new_chunk_length(s: socket.socket, encoding: str) -> (int, str):
    """
    Check how many bytes the next chunk has and return the extra of the body

    :param s:           The socket on which to read
    :param encoding:    The encoding in which the bytes should be decoded
    :return:            A tuple of the bytes in the next chunk and the extra body
    """
    b = s.recv(6).decode(encoding=encoding)
    a = b.split('\r\n')
    next_length = int(a[0], 16)
    if next_length == 0:
        return 0, ''
    else:
        return next_length - len(a[1]), a[1]


def is_image_local(src: str, host: str) -> bool:
    if ('http://' in src) or ('https://' in src):
        if host in src:
            return True
        else:
            return False
    else:
        return True


def create_dirs(rel_path: str, path: str) -> str:
    new_path = path
    for p in rel_path:
        p = p.replace('%20', ' ')
        new_path = os.path.join(new_path, p + '\\')
        if os.path.exists(new_path):
            pass
        else:
            os.mkdir(new_path)
    return new_path


def fetch_local_image(src: str, host: str, port: int):
    img = b''
    request = 'GET /' + src + ' HTTP/1.1\r\nHost: ' + host + '\r\n' + 'Connection: keep-alive\r\n' + '\r\n'
    # Doesn't seem to work without new socket, could not find my mistake
    s = create_new_socket()
    connect_socket(s, host, port)
    s.send(request.encode())
    while True:
        data = s.recv(4096)
        if data == b'':
            break
        elif b'\x00IEND\xaeB`\x82' in data:
            img = img + data
            break
        else:
            img = img + data
    pos = img.find(b'\r\n\r\n')
    return img[pos + 4:]


def save_local_image(path, name, data, img_element, src):
    img_file = open(path + name, 'wb')
    img_file.write(data)
    img_file.close()
    img_element['src'] = './' + src


def fetch_external_image(src: str, host: str, port: int):
    img = b''
    request = 'GET /' + src + ' HTTP/1.1\r\nHost: ' + host + '\r\n' + 'Connection: keep-alive\r\n' + '\r\n'
    # Doesn't seem to work without new socket, could not find my mistake
    s = create_new_socket()
    connect_socket(s, host, port)
    s.send(request.encode())
    while True:
        data = s.recv(4096)
        if data == b'':
            break
        elif b'\x00IEND\xaeB`\x82' in data:
            img = img + data
            break
        else:
            img = img + data
    pos = img.find(b'\r\n\r\n')
    return img[pos + 4:]


def save_body(body: str, host: str, s: socket.socket, port: int):
    """
    Save the body to index.html and get the included images

    :param body:
    :param host:
    :param s:
    :param port:
    """
    url = host[4:]
    soup = BeautifulSoup(body, 'html.parser')
    parent_dir = os.getcwd()
    path = os.path.join(parent_dir, url)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.mkdir(path)
    get_images(soup, s, path, host, port)
    html_file = open("./" + url + "/index.html", 'w')
    html_file.write(soup.prettify())
    html_file.close()


def get_images(soup: BeautifulSoup, s: socket.socket, path: str, host: str, port: int):
    images = soup.find_all('img')
    for image in images:
        src = image.get('src')
        if is_image_local(src, host):
            if src[0] == '/':
                src = src[1:]
            rel_path, file_name = src.rsplit('/')[0:-1], src.rsplit('/')[-1]
            if len(rel_path) == 0:
                new_path = path + '\\'
            else:
                new_path = create_dirs(rel_path, path)
            data = fetch_local_image(src, host, port)
            save_local_image(new_path, file_name, data, image, src)
        else:
            full_url = src
            if 'https://' in full_url:
                full_url = full_url[8:]
            else:
                full_url = full_url[7:]
            if full_url[0:4] != 'www.':
                full_url = 'www.' + full_url
            host, src = full_url.split('/')[0], full_url.split('/')[1:]
            filter(None, src)
            data = fetch_external_image(''.join(src), host, port)


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
    if is_chunk_based(headers):
        body = response[1].splitlines()[1]
        encoding = get_encoding(headers, body)
        chunk_length = int(response[1].splitlines()[0], 16)
        remaining_bytes = chunk_length - len(body)
        # remaining_bytes + 2 for the \r\n at the end of a chunk
        body += read_and_decode(s, remaining_bytes + 2, encoding)
        next_length, extra_body = get_new_chunk_length(s, encoding)
        body += extra_body
        while next_length != 0:
            body += read_and_decode(s, next_length + 2, encoding)
            next_length, extra_body = get_new_chunk_length(s, encoding)
            body += extra_body
        s.close()
    else:
        body = response[1]
        encoding = get_encoding(headers, body)
        total_length = headers['Content-Length']
        remaining_bytes = int(total_length) - len(body)
        body += read_and_decode(s, remaining_bytes, encoding)
        s.close()
    return body


def post(s: socket.socket, host: str, url: str = '/'):
    body = input('Please input the message you want to send: \n')
    content_length = len(body)
    request = (f"POST {url} HTTP/1.1\r\n"
               f"HOST: {host}\r\n"
               "Content-Type: text/plain; charset=UTF-8\r\n"
               f"Content-Length: {content_length}\r\n"
               "\r\n"
               f"{body}\r\n\r\n")
    message = request.encode('utf-8')
    s.send(message)
    print(s.recv(2048).decode())


def put(s: socket.socket, host: str, url: str = '/'):
    body = input('Please input the message you want to send: \n')
    content_length = len(body)
    request = (f"PUT {url} HTTP/1.1\r\n"
               f"HOST: {host}\r\n"
               "Content-Type: text/plain; charset=UTF-8\r\n"
               f"Content-Length: {content_length}\r\n"
               "\r\n"
               f"{body}\r\n\r\n")
    message = request.encode('utf-8')
    s.send(message)
    print(s.recv(2048).decode())


def run(arg: list):
    (full_url, port) = (arg[1], int(arg[2]))
    if '/' in full_url:
        (host, url) = full_url.split('/', 1)
    else:
        (host, url) = (full_url, '')
    if len(arg) > 3:
        print('Ignoring optional arguments: ' + str(arg[3:]))
    s = create_new_socket()
    s.connect((host, port))
    if arguments[0] == 'HEAD':
        head(s, host)
    elif arguments[0] == 'GET':
        body = get(s, host)
        save_body(body, host, s, port)
    elif arguments[0] == 'POST':
        post(s, host, '/' + url)
    elif arguments[0] == 'PUT':
        put(s, host, '/' + url)
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
