#!/usr/bin/env python3

import urllib.request
import json
import os
import re
import sys
import subprocess
import tempfile


_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
_START = '<div class="js-store" data-content="'
_END = '"></div>'
_TEX_HEADER = r"""\documentclass{article}
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
_VERBATIM_START = r"\begin{Verbatim}[samepage=true, commandchars=\\\{\}]]"
_VERBATIM_END = r"\end{Verbatim}"

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

  data = data[start + len(_START):]
  end = data.find(_END)

  if start < 0:
    raise ValueError("Couldn't find end token")

  data = data[:end]
  data = data.replace('&quot;', '"').replace('&mdash;', '-')
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


def split_content(content):
  content = content.replace('\r\n', '\n')
  sections = re.split(r"\[/?tab\]|\n\n", content)
  return [section.lstrip('\n').rstrip('\n') for section in sections if section.strip()]


def texify(section):
  section = re.sub("\[ch\]([^\[]+)\[/ch\]", r"\\chord{\1}", section)
  return section


def parse_json_data(json_data):
  content = find_unique_nest(json_data, 'content')
  artist_name = find_unique_nest(json_data, 'artist_name')
  song_name = find_unique_nest(json_data, 'song_name')
  return content, artist_name, song_name


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
    with open(tex_filename, 'w') as f:
      f.write(tex)

    subprocess.run(
      ['pdflatex', '-interaction=batchmode', tex_filename],
      cwd=tmpdirname)

    os.replace(os.path.join(tmpdirname, 'tab.pdf'), filename)
  print("Wrote {}".format(filename))


def main(argv):
  if len(argv) != 2:
    print("Syntax: ug-pdf.py <url>")
    os.exit(1)

  data = fetch_url(argv[1])
  json_data = extract_json_data(data)
  content, artist_name, song_name = parse_json_data(json_data)
  title = '{} - {}'.format(artist_name, song_name)
  tex = generate_tex(content, title)
  compile_tex(tex, '{}.pdf'.format(title))


if __name__ == '__main__':
  main(sys.argv)

