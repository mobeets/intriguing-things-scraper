import os
import json
import argparse
from scraper import io, prep_data, RESTART_URL

def write(T, Tp0, outfile):
    Tp1 = prep_data(T)
    print 'Found {0} new entries'.format(len(Tp1))
    inds = [t['index'] for t in Tp0]
    Tp1 = [t for t in Tp1 if t['index'] not in inds]
    print 'Keeping {0} of those new entries'.format(len(Tp1))
    assert not any([t['index'] in inds for t in Tp1]), "Added duplicate inds--whoopsie."
    json.dump(Tp0 + Tp1, open(outfile, 'w'))

def load_old_and_start_url(infile):
    Tp0 = []
    urls = []
    last_url = None
    if os.path.exists(infile):
        with open(infile) as f:
            Tp0 = json.load(f)
            last_url = Tp0[-1][1][0].get('src_url', None)
            print 'Already found {0} entries'.format(len(Tp0))
            urls = [ts[0].get('src_url', None) for dt, ts in Tp0]
    return Tp0, urls, last_url if last_url is not None else RESTART_URL

def main(infile, outfile):
    Tp0, urls, starturl = load_old_and_start_url(infile)
    T = io(starturl, urls)
    write(T, Tp0, outfile)

if __name__ == '__main__':
    psr = argparse.ArgumentParser()
    psr.add_argument('--infile', default='')
    psr.add_argument('--outfile', required=True, default='tmp.json')
    args = psr.parse_args()
    main(args.infile, args.outfile)
