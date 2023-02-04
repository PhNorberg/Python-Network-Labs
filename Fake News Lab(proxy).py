#!/usr/bin/python3
# -*- coding: UTF-8 -*_

import socket as s
import threading
import re # Regex for pattern matching

SIZE = 4096
PORT = 5105
#HOST = s.gethostbyname(s.gethostname()) # get IP address of the current machine
HOST = '127.0.0.1'
ADDR = (HOST, PORT)
UNICODE = 'utf-8' # encoding format to get string from bytes format

proxy = s.socket(s.AF_INET, s.SOCK_STREAM)
proxy.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
proxy.bind(ADDR) # bind the address ADDR to the socket


""" This is the basic handler when the proxy receives a request. The calling function
provides the socket and connection information so we can receive and intercept the
request and process it in the proxy. """
def request_handler(conn, addr):
    while True:
        result = conn.recv(SIZE).decode(UNICODE) # the proxy intercepts the HTTP request from the client
        client_request = result.split('\n')[0] # get ONLY the first line of the HTTP request containing "GET url.com HTTP/1.x"
        try:
            url = client_request.split(' ')[1] # get the URL part of the first line, which is the second argument (index 1) after "GET"
        except:
            print(f'{result}')
            conn.send(result.encode())
            continue

        """
        This section will dissect the request URL into the sections that we need
        to create a new GET request to be sent from the 'proxy client'

        Example below is based on: http://zebroid.ida.liu.se/fakenews/test1.txt

        1/ the host URL like 'zebroid.ida.liu.se/fakenews/test1.txt'
        2/ the host ip like '130.236.87.3'
        3/ the location of the data we request '/fakenews/test1.txt'
        """
        # step 1.
        url_pos = url.find('://')
        if url_pos == -1: # the substring '://' was not found in the url, take the whole thing as host_url
            host_url = url
        else: # if '://' was found, we want only the part of the url after this substring
            host_url = url[(url_pos + 3):] # offset by +3 to account for the three characters in the substring '://'

        """
        Try/Catch block to avoid error messages on request that proxy can't handle.
        According to pt 13 in debugging list, we simply ignore traffic we cannot handle.
        """
        try:
            # step 2.
            host_ip = s.getaddrinfo(host_url.split('/')[0], PORT)[0][-1][0] # obtain the actual IP where the url can be reached using our proxy port
            host_addr = (host_ip,80) # 80 should be used for the web server

            # step 3.
            path_pos = host_url.find('/')
            host_path = host_url[path_pos:] # take /fakenews/test1.txt

            # Assemble the information obtained in steps 1-3
            proxy_request = f"GET {url} HTTP/1.1\r\nHost:{host_ip}\r\n\r\n"

            # create a socket for the client part of the proxy and assemble the GET request
            client = s.socket(s.AF_INET, s.SOCK_STREAM)
            client.connect(host_addr)
            client.send(proxy_request.encode())
        except:
            print("BAD REQUEST: could not solve IP/getaddrinfo")
            break # break here if we couldn't obtain useable information from header



        """
        This block will fetch and decode the HTTP response from the server in
        chunks and append them to the response string. When all data has been
        fetched, the message will be chopped separated into header and body.
        """
        response = ''
        raw_data = b''
        while True:
            try:
                temp = client.recv(SIZE) # recv allows you to fetch the message in chunks
                if temp:
                    raw_data = raw_data + temp
                    response += temp.decode(UNICODE, 'ignore') # ignore flag added
                    # 'utf-8' codec can't decode byte 0xe2: unexpected end of data
                else:
                    break
            except:
                print("Could not receive data from server.")
                break
        #print(f'{response}')

        (header, body) = split_header_body(response)
        if header == 0:
            print("MISSING HEADER")
            break

        # use custom function to disect header into key-value pairs
        header_params = get_header_params(header)

        """
        If header contains 'Content-Type: image/jpeg' don't decode/encode
        because image data is not in utf-8 and should not be altered anyway.
        """
        if header.find("Content-Type: image/jpeg") != -1:
        #if header_params.get('Content-Type:') == 'image/jpeg':
            print("This is an image.")
            conn.send(raw_data)
            break


        print(f'{header}')
        #print(f'{body}')

        content_length = header_params.get('Content-Length:', -1) # extract value for Content-Length or -1 as default if not found
        if content_length != -1:
            content_length = content_length[0] # the values for content_length is passed as a list element, unless set to -1 by default

        (body, increase) = do_troll(body)
        header = update_header(header, content_length, increase)

        print(f'{header}')

        """ TROLLING GOES HERE """
        conn.send(header.encode())
        conn.send(body.encode())

        break
    conn.close()


""" Takes the header and new value for content length after applying trolly """
def update_header(header, content_length, increase):

    new_length = int(content_length) + increase
    #print(new_length)
    # replace old value for content length
    return header.replace(f'Content-Length: {content_length}',
            f'Content-Length: {new_length}')

""" Breaks the header into a dictionary with header fields as keys and their
    corresponding values """
def get_header_params(header):
    params = {} # declare an empty dictionary to store header parameters like "Content-Length:" -> value
    for line in header.split('\n'):
        if line:
            params[line.split(' ')[0]] = line.split(' ')[1:] # take first element as key and the rest of the line as value
            # for example: Content-Type: text/html; charset=UTF-8 where "Content-Type:" is key, etc.
    return params

""" Takes a HTTP-body and replaces all occurences of Stockholm with Linköping
    and smiley with trolly. Returns the modified body. """
def do_troll(body):
    #print(body)
    troll_body = ''
    occurences = body.count('Linköping')
    replacements = 0


    for section in body.split(' '):
        # Replace smiley with trolly
        section = section.replace('./smiley.jpg', './trolly.jpg')
        section = section.replace('Smiley', 'Trolly')

        # replace instances of Stockholm that are not a part of a src filename
        if not (re.match('src(.*)Stockholm(.*)', section)):
            troll_body += section.replace('Stockholm', 'Linköping')
        else:
            troll_body += section

        troll_body += ' '

    #print(troll_body)
    troll_body = troll_body[:-1] # -1 to skip the last ' ' that doesn't represent a split

    # check how many instances of 'Stockholm' were replaced with 'Linköping' and
    # calculate how much the content-length field of the header should be adjusted
    # NOTE: remove any instances of 'Linköping' that were there originally
    factor = (len('Linköping'.encode()) - len('Stockholm'.encode()))
    replacements = troll_body.count('Linköping') - occurences
    increase = replacements * factor # the increase in content-length by doing the replacements

    #print(increase)
    return (troll_body, increase)


""" Split HTTP response into a tuple with header and body separated. """
def split_header_body(response):
    # find index of delimiter '\r\n\r\n' between header and body section
    try:
        index = response.index('\r\n\r\n')
    except ValueError:
        return (0, 0)
    return (response[:(index + 4)], response[(index + 4):]) # offset by + 4 so that '\r\n\r\n' is included in the header



""" Allows the proxy to handle multiple concurrent requests in threads."""
def run(proxy):
    proxy.listen()
    while True:
        conn, addr = proxy.accept() # addr is the tuple containing IP addr and port - conn is a new socket
        #print(conn, addr)
        thread = threading.Thread(target=request_handler, args=(conn, addr))
        thread.start()
        #conn.close()
    conn.close()


print("ATTEMPTING TO START PROXY SERVER")
run(proxy)
