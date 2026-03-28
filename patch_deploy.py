import re

html = open('index.html', 'r', encoding='utf-8').read()

target = "const API_BASE = 'http://localhost:8000';"
repl = '''// Auto-detect environment: use Render URL if not on localhost
const RENDER_URL = 'https://[YOUR-RENDER-APP-NAME].onrender.com';
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') 
  ? 'http://localhost:8000' 
  : RENDER_URL;'''

html = html.replace(target, repl)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
