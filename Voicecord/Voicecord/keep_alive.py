from flask import Flask, Response
from threading import Thread

app = Flask('')

@app.route('/')
def main():
    return 'rao sahab'

# Add this route for robots.txt
@app.route('/robots.txt')
def robots_txt():
    content = """
    User-agent: *
    Disallow:
    """
    return Response(content, mimetype="text/plain")

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    server = Thread(target=run)
    server.start()
