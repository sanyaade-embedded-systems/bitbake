"""Enhance urlparse for OpenEmbedded's needs

- Handles OpenEmbedded's odd file urls.
  OE uses file://foo/bar.patch as relative, file:///foo/bar.patch as absolute,
  but '//' following the scheme implies the existance of an authority, aka
  a hostname, and urlparse handles it in that way.
- Allows url params for all schemes.
- Pre-parses the params and query string for convenience.

Portions of the Url class were copied directly from the urlparse source tree.

The encodeurl and decodeurl functions are still provided, for compatibility reasons.
"""

import urlparse


def parse_url(url):
    url = url.replace('file://', 'file:')
    if ';' in url:
        url, params = url.split(';', 1)
        params = parse_params(params)
    else:
        params = {}

    scheme, netloc, path, _, query, fragment = urlparse.urlparse(url)
    query = urlparse.parse_qs(query)

    return Url(scheme, netloc, path, params, query, fragment)

def parse_params(params):
    values = {}
    if params:
        for param in params.split(';'):
            try:
                key, value = param.split('=', 1)
            except ValueError:
                key, value = param, True
            values[key] = value
    return values

#noinspection PyUnresolvedReferences
class Url(urlparse.ParseResult):
    """Representation of a Uniform Resource Identifier"""

    __slots__ = ()

    @property
    def querystring(self):
        """Reassembled query string"""
        query = ';'.join('%s=%s' % (key, v)
                         for key, value in self.query.iteritems()
                         for v in value)
        return query

    @property
    def parameterstring(self):
        """Reassembled parameter string"""
        parameters = ';'.join('%s=%s' % (key, value)
                              for key, value in self.params.iteritems())
        return parameters

    def join(self, otherurl):
        """Join this url to a possibly relative URL to form an absolute
        interpretation of the latter."""
        return parse_url(urlparse.urljoin(str(self), str(otherurl)))

    def unsplit(self):
        """String version of URL without parameters"""
        url = self.path
        if self.netloc or (self.scheme and self.scheme in urlparse.uses_netloc and
                           url[:2] != '//'):
            url = '//' + (self.netloc or '') + url
        if self.scheme:
            url = self.scheme + ':' + url
        if self.query:
            url += '?' + self.querystring
        if self.fragment:
            url += '#' + self.fragment
        return url

    def geturl(self):
        url = self.unsplit()
        if self.params:
            url += ';' + self.parameterstring
        return url

    def __str__(self):
        return self.geturl()


def decodeurl(url):
    """Decodes an URL into the tokens (scheme, network location, path,
    user, password, parameters).
    """
    from . import MalformedUrl
    uri = parse_url(url)

    if not uri.scheme or not uri.path:
        raise MalformedUrl(url)

    return uri.scheme, uri.hostname or '', uri.path, uri.username or '', uri.password or '', uri.params

def encodeurl(decoded):
    """Encodes a URL from tokens (scheme, network location, path,
    user, password, parameters).
    """
    from . import MissingParameterError

    type, host, path, user, pswd, p = decoded

    if not type or not path:
        raise MissingParameterError("Type or path url components missing when encoding %s" % decoded)

    url = '%s://' % type
    if user:
        url += "%s" % user
        if pswd:
            url += ":%s" % pswd
        url += "@"

    if host:
        url += "%s" % host

    url += "%s" % path

    if p:
        for parm in p:
            url += ";%s=%s" % (parm, p[parm])

    return url

#  vim: set et fenc=utf-8 sts=4 sw=4 :
