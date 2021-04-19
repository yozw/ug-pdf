import os
from flask import Flask, make_response, request, make_response
import tempfile
import ug_pdf

app = Flask(__name__)

MAIN_PAGE = """<html>
Type url:
<form method='post'>
<input type='text' name='url' style='width: 100%; margin: 8px 0;'>
<button type="submit" value="Submit">Submit</button>
</html>
"""

@app.route("/", methods=['GET', 'POST'])
def main():
    if request.method == 'GET':
        return MAIN_PAGE
    elif request.method == 'POST':
        url = request.form['url']
        with tempfile.TemporaryDirectory() as path:
            os.chdir(path)
            if not url.startswith('https://tabs.ultimate-guitar.com/') or len(url) > 250:
                raise ValueError('Invalid URL')
            output_path = ug_pdf.convert(url)
            with open(output_path, 'rb') as f:
                content = f.read()
            response = make_response(content)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename={os.path.basename(output_path)}'
            return response
        
if __name__ == "__main__":
    app.run()

    
