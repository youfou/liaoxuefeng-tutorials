# coding: utf8

import re
import os
import requests
from urlparse import urlparse
from lxml import html, cssselect


'''
# 实现步骤
1. 从左侧菜单栏获取需要抓取的页面，以及各标题
2. 抓取页面
    1. 将H标签降低n级(取决于目录中的最深层级和页面中的初始层级)
    2. 下载所有提及的图片
3. 将各标题以及获取到的页面内容组合起来
4. 保存为一个html
'''


CS_TOC = 'ul.uk-nav.uk-nav-side'
CS_CONTENT = 'div.x-wiki-content'
PAGE_IDENT_BASE = 3


def run(result_dir, index_url):

    url_base = '%s://%s' % (urlparse(index_url)[:2])

    s = requests.session()
    s.headers.update(
        {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; '
            '+http://www.google.com/bot.html)'})

    def parse(url):
        print 'Fetching %s' % url
        r = s.get(url)
        return html.fromstring(r.content)
        # return html.parse(url, html.HTMLParser())

    def select(tree, cs):
        s = cssselect.CSSSelector(cs)
        return s(tree)

    def download(path):
        path_splited = path.split('/')
        save_dir_layers = [result_dir] + path_splited[:-1]
        save_dir = ''
        for layer in save_dir_layers:
            save_dir = os.path.join(save_dir, layer)
            if not os.path.exists(save_dir):
                os.mkdir(save_dir)

        url = url_base + '/' + path
        print 'Downloading %s' % url
        r = s.get(url, stream=True)
        r.raise_for_status()

        save_path = os.path.join(save_dir, path_splited[-1])
        img_type = None

        has_ext = re.search(r'(?<=\.)\w{2,5}$', path)
        if not has_ext:
            img_type = r.headers['content-type'].split('/')[-1]
            save_path = '%s.%s' % (save_path, img_type)

        with open(save_path, 'wb') as f:
            f.write(r.raw.read())

        return img_type

    def get_content(tree):
        content = select(tree, CS_CONTENT)[0]

        for img in content.iter('img'):
            src = img.get('src')
            src = re.sub(r'(^/|/\w?$)', '', src)

            img_type = download(src)
            if img_type:
                src = '%s.%s' % (src, img_type)

            img.set('src', src)

        return content

    def ph(tree):
        print html.tostring(tree)

    toc = select(parse(index_url), CS_TOC)[1]

    pages = list()
    max_page_ident = 0

    # 获取内容
    for i in toc.iterfind('./li[@style]'):
        title = i.findtext('a')
        ident = int(re.search(r'(?<=:)\d+(?=em)', i.get('style')).group(0))
        if ident > max_page_ident:
            max_page_ident = ident
        path = i.find('a').get('href')
        tree = parse(url_base + path)
        content = get_content(tree)
        pages.append(dict(
            title=title,
            ident=ident,
            path=path,
            content=content))

        # break

    print 'max_idnet: %d' % max_page_ident
    page_ident_offset = max_page_ident - PAGE_IDENT_BASE + 1
    print 'page_ident_offset: %d' % page_ident_offset

    # 调整页面内容
    for p in pages:
        for el in p['content']:
            if isinstance(el.tag, str):
                m = re.match(r'h(\d+)', el.tag)
                if m:
                    el.tag = 'h%d' % (int(m.group(1)) + page_ident_offset)

        # for img in p['content'].iter('img'):
        #     img.set('src', img.get('src')[1:])

    # 组合内容

    # 添加字符编码声明
    result = '<head><meta charset="utf-8"/></head>\n'

    for p in pages:
        page_heading = html.Element('h%d' % p['ident'])
        page_heading.text = p['title']
        result += html.tostring(page_heading, encoding='utf8') + '\n'
        result += '\n'.join([html.tostring(i, encoding='utf8').strip()
                             for i in p['content']]) + '\n'

    # result = re.sub(r'(^|<code>)#', r'\1\\#', result, 0, re.M)

    with open(os.path.join(result_dir, 'result.html'), 'w') as f:
        f.write(result)


# ---------------------------- CONFIG START ------------------------------

js = ('js',
      'http://www.liaoxuefeng.com/'
      'wiki/001434446689867b27157e896e74d51a89c25cc8b43bdb3000')

py2 = ('py2',
       'http://www.liaoxuefeng.com/'
       'wiki/001374738125095c955c1e6d8bb493182103fac9270762a000')

py3 = ('py3',
       'http://www.liaoxuefeng.com/'
       'wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000')

git = ('git',
       'http://www.liaoxuefeng.com/'
       'wiki/0013739516305929606dd18361248578c67b8067c8c017b000')

# ----------------------------- CONFIG END -------------------------------


if __name__ == '__main__':
    for result_dir, index_url in js, py2, py3, git:
        run(result_dir, index_url)
