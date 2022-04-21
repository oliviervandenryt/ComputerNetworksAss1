def parse_headers(resp: str, client=True, server=False) -> dict:
    """
    Parse the headers from an HTTP response
    and put them in a dictionary

    :param resp:        The HTTP response
    :return:            A dictionary with the headers
    """
    headers_dict = dict()
    http_resp, crlf, http_rheaders = resp.partition('\r\n')
    if client:
        if http_resp[-6] == '2':
            http_headers = http_rheaders.split('\r\n')
            for header in http_headers:
                if header != '':
                    key, content = header.split(':', 1)
                    headers_dict.update({key: content})
            return headers_dict
    if server:
        http_headers = http_rheaders.split('\r\n')
        for header in http_headers:
            if header != '':
                key, content = header.split(':', 1)
                headers_dict.update({key: content})
        return headers_dict

