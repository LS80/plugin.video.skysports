from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import base64
import threading
import socket

import livestreamer

SERVER_NAME = "localhost"
SERVER_PORT = 64648
CHUNK_SIZE = 8192

class StreamHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.serve(False)

    def do_GET(self):
        self.serve()

    def serve(self, send_data=True):
        self.send_response(200)
        self.send_header('Content-type', 'video/x-flv')
        self.end_headers()
        if send_data:
            try:
                url = base64.b64decode(self.path.lstrip('/'))
                streams = livestreamer.streams(url)
                stream = streams['best']
            except Exception as e:
                self.send_error(500, str(e))
            else:
                with stream.open() as fd:  
                    data = fd.read(CHUNK_SIZE)
                    while len(data) > 0:
                        try:
                            self.wfile.write(data)
                        except socket.error as e:
                            self.server.stop = True
                            self.wfile.close()
                            self.socket.close()
                        data = fd.read(CHUNK_SIZE)
            self.server.stop = True
        
def run_server():
    try:
        httpd = HTTPServer((SERVER_NAME, SERVER_PORT), StreamHandler)
    except:
        pass
    else:
        httpd.stop = False
        print "Started HTTP Server..."
        while not httpd.stop:
            httpd.handle_request()
        print "Stopped HTTP Server"
    
def run_server_thread():
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    
