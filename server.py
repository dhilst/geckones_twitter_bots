from http.server import HTTPServer, BaseHTTPRequestHandler


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(301)
        self.send_header('Location', 'https://twitter.com/kiitensupport')
        self.end_headers()


PORT = 80
httpd = HTTPServer(('0.0.0.0', PORT), SimpleHTTPRequestHandler)
print(f"Serving at {PORT}")
httpd.serve_forever()
