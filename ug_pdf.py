#!/usr/bin/env python3

import codecs
import urllib.request
import html
import json
import os
import re
import shutil
import sys
import subprocess
import tempfile


_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
_START = '<div class="js-store" data-content="'
_END = '"></div>'
_TEX_HEADER = r"""\documentclass[10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage{fancyvrb}
\usepackage{fullpage}
\usepackage{xcolor}
\parindent=0pt
\parskip=0pt
\newcommand\chord[1]{{\fboxsep=2pt\hspace{-\fboxsep}\colorbox{black!10}{#1}\hspace{-\fboxsep}}}
\newcommand\doctitle[1]{\textbf{\sffamily\large #1}\\}
\begin{document}
"""
_TEX_FOOTER = r"""
\end{document}
"""
_VERBATIM_START = r"\begin{Verbatim}[samepage=true, commandchars=\\\{\}]"
_VERBATIM_END = r"\end{Verbatim}"
_DEBUG_OUTPUT = '/tmp/ug-pdf.tex'

def fetch_url(url):
  request = urllib.request.Request(
      url, 
      data=None, 
      headers={
          'User-Agent': _USER_AGENT
     }
  )
  return urllib.request.urlopen(request).read().decode('utf-8')


def extract_json_data(data):
  start = data.find(_START)
  if start < 0:
    raise ValueError("Couldn't find start token")

  end = data.find(_END, start)
  if end < 0:
    raise ValueError("Couldn't find end token")

  data = html.unescape(data[start + len(_START):end])
  return json.loads(data)


def find_nest(data, key):
  for k, v in data.items():
    if k == key:
      yield v
    elif isinstance(v, dict):
      for rv in find_nest(v, key):
        yield rv


def find_unique_nest(data, key):
  results = list(find_nest(data, key))
  if len(results) == 0:
    raise ValueError("Page layout not recognised: Could not find key '{}'".format(key))
  elif len(results) > 1:
    raise ValueError("Page layout not recognised: Multiple nodes called '{}'".format(key))
  return results[0]


def parse_json_data(json_data):
  content = find_unique_nest(json_data, 'content')
  artist_name = find_unique_nest(json_data, 'artist_name')
  song_name = find_unique_nest(json_data, 'song_name')
  return content, artist_name, song_name


def split_content(content):
  content = content.replace('\r\n', '\n')
  sections = re.split(r"\[/?tab\]|\n\n", content)
  return [section.lstrip('\n').rstrip('\n') for section in sections if section.strip()]


def texify(section):
  section = section.replace('\\', '\\symbol{92}')
  section = re.sub("\[ch\]([^\[]+)\[/ch\]", r"\\chord{\1}", section)
  return section


def generate_tex(content, title):
  lines = []
  lines.append(_TEX_HEADER)
  lines.append('\\doctitle{%s}' % title)
  lines.append('')
  for section in split_content(content):
    lines.append(_VERBATIM_START)
    lines.append(texify(section))
    lines.append(_VERBATIM_END)
    lines.append('')
  
  lines.append(_TEX_FOOTER)
  return "\n".join(lines)


def compile_tex(tex, filename):
  with tempfile.TemporaryDirectory() as tmpdirname:
    tex_filename = os.path.join(tmpdirname, 'tab.tex')
    with codecs.open(tex_filename, 'w', encoding='utf8') as f:
      f.write(tex)

    cp = subprocess.run(
      ['pdflatex', '-interaction=batchmode', tex_filename],
      cwd=tmpdirname)
    if cp.returncode != 0:
      shutil.move(tex_filename, _DEBUG_OUTPUT)
      debug_log = tex_filename.replace('.tex', '.log')
      raise RuntimeError("pdflatex returned non-zero error code {}. See {} for input. Ouput:\n{}".format(
        cp.returncode, _DEBUG_OUTPUT, "\n".join(open(debug_log).readlines())))

    shutil.move(os.path.join(tmpdirname, 'tab.pdf'), filename)


def convert(url):
  data = fetch_url(url)
  json_data = extract_json_data(data)
  content, artist_name, song_name = parse_json_data(json_data)
  title = '{} - {}'.format(artist_name, song_name)
  filename = '{}.pdf'.format(title)
  tex = generate_tex(content, title)
  compile_tex(tex, filename)
  return filename


def main(argv):
  if len(argv) != 2:
    print("Syntax: ug_pdf.py <url>")
    os.exit(1)
  output = convert(argv[1])
  print("Wrote {}".format(output))


if __name__ == '__main__':
  main(sys.argv)

