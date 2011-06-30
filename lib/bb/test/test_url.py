try:
    import unittest2 as unittest
except ImportError:
    import unittest

from bb.fetch2.url import parse_url, Url

default = Url("", "", "", {}, {}, "")
def new_url(**kwargs):
    return default._replace(**kwargs)

class TestURIs(unittest.TestCase):
    uris = {
        "file://defconfig": new_url(scheme="file", path="defconfig"),
        "file://foo/defconfig": new_url(scheme="file", path="foo/defconfig"),
        "file:///defconfig": new_url(scheme="file", path="/defconfig"),
        "file:///foo/defconfig": new_url(scheme="file", path="/foo/defconfig"),
        "file://foo/defconfig;patch=1;alpha=beta": new_url(scheme="file", path="foo/defconfig",
                                                           params={"patch": "1", "alpha": "beta"}),
        "http://foo.com/bar/defconfig;patch=1;alpha=beta": new_url(scheme="http", path="/bar/defconfig",
                                                                   netloc="foo.com",
                                                                   params={"patch": "1", "alpha": "beta"}),
        "git://github.com/kergoth/homefiles.git": new_url(scheme="git", netloc="github.com",
                                                          path="/kergoth/homefiles.git"),
        "svn://clarson@kergoth.com/;module=homefiles;protocol=http": new_url(scheme="svn", netloc="clarson@kergoth.com",
                                                                             path="/", params={"module": "homefiles",
                                                                                               "protocol": "http"}),
        "svn://svn.enlightenment.org/svn/e/trunk;module=E-MODULES-EXTRA/elfe;scmdata=keep;proto=http":
            new_url(scheme="svn", netloc="svn.enlightenment.org", path="/svn/e/trunk",
                    params={"module": "E-MODULES-EXTRA/elfe", "scmdata": "keep", "proto": "http"}),
    }

    def test_uris(self):
        for url, compareto in self.uris.iteritems():
            parsed = parse_url(url)
            self.assertEqual(parsed, compareto)

    def test_file_uri_rejoin(self):
        url = parse_url("file://defconfig")
        self.assertEqual(str(url), "file://defconfig")

    def test_file_uri_rejoin_abs(self):
        url = parse_url("file:///foo/defconfig")
        self.assertEqual(str(url), "file:///foo/defconfig")
