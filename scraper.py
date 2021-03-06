import glob
import json
import os.path
import urllib2
import datetime
import scraperwiki
from time import mktime
from dateutil import parser
from unidecode import unidecode
from BeautifulSoup import BeautifulSoup

BASE_URL = 'http://tinyletter.com/realfuture/letters/'
RESTART_URL = 'http://tinyletter.com/realfuture/letters/5-intriguing-things-like-a-dog-in-an-mri-machine'
# RESTART_URL = 'http://tinyletter.com/realfuture/letters/a-range-of-synthetic-smog-recipes'
# RESTART_URL = 'http://tinyletter.com/realfuture/letters/5-intriguing-things-150'

class Thing:
    def __init__(self, dt, number, title, url, src_url):
        self.dt = dt
        self.number = number
        self.title = title
        self.url = url
        self.src_url = src_url
        self.ps = []

    def __str__(self):
        ps = u'\n<br>'.join([p.decode('utf-8') for p in self.ps])
        return u'<a href="{0}">{1}</a>: {2}'.format(self.url, self.title, ps)

def read(url):
    response = urllib2.urlopen(url)
    return response.read()

def parse(html):
    obj = BeautifulSoup(html).body
    dt = parser.parse(obj.find('div', attrs={'class': 'date'}).text.strip())
    contents = obj.find('div', attrs={'class': 'message-body'})
    next_url = obj.find('a', attrs={'class': 'paging-button prev'})
    next_url = next_url.get('href') if next_url is not None else next_url
    return dt, contents, next_url

def things(obj, dt, src_url):
    breaks = ["""Subscribe to The Newsletter""", """1957 American English""", """Today's 1957""", """Tell Your Friends: Subscribe to 5 Intri""", """Did some good soul forward you this email?""", """Were you forwarded this email?""", """1957 English Usage""", """Subscribe to 5 Intriguing Things"""]
    num = 1
    thing = None
    items = []
    found_number = lambda i, val: val.startswith('{0}.'.format(i))
    has_number = lambda i, p: (p.strong is not None and found_number(i, p.strong.text)) or found_number(i, p.text)
    has_url = lambda p: p.a is not None and p.a.has_key('href')
    for p in obj.findChildren('p'):
        if p.text is None:
            continue
        if any([has_number(j, p) for j in xrange(num, num+2)]) and has_url(p): # for various numbering errors
            if thing is not None:
                items.append(thing)
                thing = None
            thing = Thing(dt, num, p.a.text if p.a is not None else p.text.partition('. ')[-1], p.a.get('href'), src_url)
            num += 1
        elif thing is not None:
            if [brk for brk in breaks if brk in p.text]:
                if thing is not None:
                    items.append(thing)
                    thing = None
            else:
                thing.ps.append(str(p))
    if thing is not None:
        items.append(thing)
    return items

def fix_2014_06_06(html):
    html = html.replace('<div class="message-body">', '<div class="message-body"><p>')
    html = html.replace('<p>"Eating too fast', '</p><p>"Eating too fast')
    return parse(html)[1]

def load(url):
    dt, contents, next_url = parse(read(url))
    if dt.strftime('%Y-%m-%d') == '2014-06-06':
        contents = fix_2014_06_06(read(url))
    return dt, things(contents, dt, url), next_url

def prep_data(T, inds):
    data = []
    cnv = lambda x: x.decode('utf-8') if type(x) is str else x
    cnv2 = lambda x: unidecode(x) if type(x) is unicode else x
    for dt, ts in T:
        for t in ts:
            t.index = '{0}-{1}-{2}.{3}'.format(dt.year, dt.month, dt.day, t.number)
            t.dt = '{0}-{1}-{2}'.format(dt.year, dt.month, dt.day)
            t.ps = ''.join(t.ps)
            t_dict = {cnv2(cnv(k)): cnv2(cnv(v)) for k, v in t.__dict__.items()}
            if t.index not in inds:
                data.append(t_dict)
    return data

def scraper_sqlite(T, inds):
    data = prep_data(T, inds)
    scraperwiki.sqlite.save(['index'], data, table_name='data')

def io(starturl, urls, inds):
    T = []
    next_url = starturl
    print 'Starting at {0}'.format(next_url)
    while next_url and next_url != 'javascript:void(0)':
        next_url = BASE_URL + next_url.split('letters/')[1]
        print next_url
        dt, ts, new_url = load(next_url)
        if len(ts) == 0:
            print 'ERROR: {0}'.format(dt)
        if next_url not in urls:
            T.append((dt, ts))
        next_url = new_url
    print 'Writing {0} new entries'.format(len(T))
    scraper_sqlite(T, inds)
    return T

def load_old_and_start_url():
    scraperwiki.sqlite.execute("""CREATE TABLE IF NOT EXISTS data (ps TEXT, "index" TEXT, url TEXT, title TEXT, number INTEGER, src_url TEXT, dt TEXT)""")
    try:
        urls_q = scraperwiki.sqlite.select("* from data")
    except Exception, err:
        print err
        return [], RESTART_URL, []
    urls = []
    max_dt = None
    lasturl = None
    inds = [row['index'] for row in urls_q]
    for row in urls_q:
        dtc = parser.parse(row['dt'])
        if max_dt is None or dtc > max_dt:
            max_dt = dtc
            lasturl = row['src_url']
        urls.append(row['url'])
    return urls, (lasturl if lasturl is not None else RESTART_URL), inds

def main():
    print 'Loading previous entries...'
    urls, starturl, inds = load_old_and_start_url()
    print 'Found {0} urls'.format(len(urls))
    print 'Starting at ' + starturl
    print 'Currently have {0} entries'.format(len(urls))
    io(starturl, urls, inds)

if __name__ == '__main__':
    main()
