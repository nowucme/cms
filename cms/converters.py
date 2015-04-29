# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2015 Eyeo GmbH
#
# Adblock Plus is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# Adblock Plus is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Adblock Plus.  If not, see <http://www.gnu.org/licenses/>.

import os
import HTMLParser
import imp
import re

import jinja2
import markdown


# Monkey-patch Markdown's isBlockLevel function to ensure that no paragraphs are
# inserted into the <head> tag
orig_isBlockLevel = markdown.util.isBlockLevel
def isBlockLevel(tag):
  if tag == "head":
    return True
  else:
    return orig_isBlockLevel(tag)
markdown.util.isBlockLevel = isBlockLevel

html_escapes = {
  "<": "&lt;",
  ">": "&gt;",
  "&": "&amp;",
  "\"": "&quot;",
  "'": "&#39;",
}

class AttributeParser(HTMLParser.HTMLParser):
  _string = None
  _inside_fixed = False
  _fixed_strings = None
  _attrs = None

  def __init__(self, whitelist):
    self._whitelist = whitelist

  def parse(self, text, pagename):
    self.reset()
    self._string = []
    self._fixed_strings = []
    self._inside_fixed = False
    self._attrs = {}
    self._pagename = pagename

    try:
      self.feed(text)
      return "".join(self._string), self._attrs, ["".join(s) for s in self._fixed_strings]
    finally:
      self._string = None
      self._attrs = None
      self._pagename = None
      self._inside_fixed = False
      self._fixed_strings = None

  def handle_starttag(self, tag, attrs):
    if self._inside_fixed:
      raise Exception("Unexpected HTML tag '%s' inside a fixed string on page %s" % (tag, self._pagename))
    elif tag == "fix":
      self._inside_fixed = True
      self._fixed_strings.append([])
    elif tag in self._whitelist:
      self._attrs.setdefault(tag, []).append(attrs)
      self._string.append("<%s>" % tag)
    else:
      raise Exception("Unexpected HTML tag '%s' in localizable string on page %s" % (tag, self._pagename))

  def handle_endtag(self, tag):
    if tag == "fix":
      self._string.append("{%d}" % len(self._fixed_strings))
      self._inside_fixed = False
    else:
      self._string.append("</%s>" % tag)

  def _append_text(self, s):
    if self._inside_fixed:
      self._fixed_strings[-1].append(s)
    else:
      self._string.append(s)

  def handle_data(self, data):
    # Note: lack of escaping here is intentional. The result is a locale string,
    # HTML escaping is applied when this string is inserted into the document.
    self._append_text(data)

  def handle_entityref(self, name):
    self._append_text(self.unescape("&%s;" % name))

  def handle_charref(self, name):
    self._append_text(self.unescape("&#%s;" % name))

class Converter:
  whitelist = set(["a", "em", "strong", "code"])

  def __init__(self, params, key="pagedata"):
    self._params = params
    self._key = key
    self._attribute_parser = AttributeParser(self.whitelist)

    # Read in any parameters specified at the beginning of the file
    lines = params[key].splitlines(True)
    while lines and re.search(r"^\s*[\w\-]+\s*=", lines[0]):
      name, value = lines.pop(0).split("=", 1)
      params[name.strip()] = value.strip()
    params[key] = "".join(lines)

  def localize_string(self, name, default, localedata, escapes):
    def escape(s):
      return re.sub(r".",
        lambda match: escapes.get(match.group(0), match.group(0)),
        s, flags=re.S)
    def re_escape(s):
      return re.escape(escape(s))

    # Extract tag attributes from default string
    default, saved_attributes, fixed_strings = self._attribute_parser.parse(default, self._params["page"])

    # Get translation
    if self._params["locale"] != self._params["defaultlocale"] and name in localedata:
      result = localedata[name].strip()
    else:
      result = default

    # Insert fixed strings
    for i in range(len(fixed_strings)):
      result = re.sub(r"\{%d\}" % (i + 1), fixed_strings[i], result, 1)

    # Insert attributes
    result = escape(result)
    def stringify_attribute((name, value)):
      return '%s="%s"' % (
        escape(name),
        escape(self.insert_localized_strings(value, escapes))
      )

    for tag in self.whitelist:
      saved = saved_attributes.get(tag, [])
      for attrs in saved:
        attrs = map(stringify_attribute, attrs)
        result = re.sub(
          r"%s([^<>]*?)%s" % (re_escape("<%s>" % tag), re_escape("</%s>" % tag)),
          r'<%s%s>\1</%s>' % (tag, " " + " ".join(attrs) if attrs else "", tag),
          result, 1, flags=re.S
        )
      result = re.sub(
        r"%s([^<>]*?)%s" % (re_escape("<%s>" % tag), re_escape("</%s>" % tag)),
        r"<%s>\1</%s>" % (tag, tag),
        result, flags=re.S
      )
    return result

  def insert_localized_strings(self, text, escapes, to_html=lambda s: s):
    def lookup_string(match):
      name, comment, default = match.groups()
      default = to_html(default).strip()

      # Note: We currently ignore the comment, it is only relevant when
      # generating the master translation.
      return self.localize_string(name, default, self._params["localedata"], escapes)

    return re.sub(
      r"{{\s*"
      r"([\w\-]+)" # String ID
      r"(?:\[(.*?)\])?" # Optional comment
      r"\s+"
      r"((?:(?!{{).|" # Translatable text
        r"{{(?:(?!}}).)*}}" # Nested translation
      r")*?)"
      r"}}",
      lookup_string,
      text,
      flags=re.S
    )

  def process_links(self, text):
    def process_link(match):
      pre, attr, url, post = match.groups()
      url = jinja2.Markup(url).unescape()

      locale, new_url = self._params["source"].resolve_link(url, self._params["locale"])
      if new_url != None:
        url = new_url
        if attr == "href":
          post += ' hreflang="%s"' % jinja2.Markup.escape(locale)

      return "".join((pre, jinja2.Markup.escape(url), post))

    text = re.sub(r"(<a\s[^<>]*\b(href)=\")([^<>\"]+)(\")", process_link, text)
    text = re.sub(r"(<img\s[^<>]*\b(src)=\")([^<>\"]+)(\")", process_link, text)
    return text

  include_start_regex = '<'
  include_end_regex = '>'

  def resolve_includes(self, text):
    def resolve_include(match):
      global converters
      name = match.group(1)
      for format, converter_class in converters.iteritems():
        if self._params["source"].has_include(name, format):
          self._params["includedata"] = self._params["source"].read_include(name, format)
          converter = converter_class(self._params, key="includedata")
          return converter()
      raise Exception("Failed to resolve include %s on page %s" % (name, self._params["page"]))

    return re.sub(
      r'%s\?\s*include\s+([^\s<>"]+)\s*\?%s' % (
        self.include_start_regex,
        self.include_end_regex
      ),
      resolve_include,
      text
    )

  def __call__(self):
    result = self.get_html(self._params[self._key])
    result = self.resolve_includes(result)
    if self._key == "pagedata":
      head = []
      def add_to_head(match):
        head.append(match.group(1))
        return ""
      body = re.sub(r"<head>(.*?)</head>", add_to_head, result, flags=re.S)
      return "".join(head), body
    else:
      return result

class RawConverter(Converter):
  def get_html(self, source):
    result = self.insert_localized_strings(source, html_escapes)
    result = self.process_links(result)
    return result

class MarkdownConverter(Converter):
  include_start_regex = r'(?:%s|%s)' % (
    Converter.include_start_regex,
    re.escape(jinja2.escape(Converter.include_start_regex))
  )
  include_end_regex = r'(?:%s|%s)' % (
    Converter.include_end_regex,
    re.escape(jinja2.escape(Converter.include_end_regex))
  )

  def get_html(self, source):
    def remove_unnecessary_entities(match):
      char = unichr(int(match.group(1)))
      if char in html_escapes:
        return match.group(0)
      else:
        return char

    escapes = {}
    for char in markdown.Markdown.ESCAPED_CHARS:
      escapes[char] = "&#" + str(ord(char)) + ";"
    for key, value in html_escapes.iteritems():
      escapes[key] = value

    md = markdown.Markdown(output="html5", extensions=["attr_list"])
    md.preprocessors["html_block"].markdown_in_raw = True

    def to_html(s):
      return re.sub(r'</?p>', '', md.convert(s))

    result = self.insert_localized_strings(source, escapes, to_html)
    result = md.convert(result)
    result = re.sub(r"&#(\d+);", remove_unnecessary_entities, result)
    result = self.process_links(result)
    return result

class TemplateConverter(Converter):
  class _SourceLoader(jinja2.BaseLoader):
    def __init__(self, source):
      self.source = source

    def get_source(self, environment, template):
      try:
        return self.source.read_file(template + ".tmpl"), None, None
      except Exception:
        raise jinja2.TemplateNotFound(template)

  def __init__(self, *args, **kwargs):
    Converter.__init__(self, *args, **kwargs)

    filters = {
      "translate": self.translate,
      "linkify": self.linkify,
      "toclist": self.toclist,
    }

    globals = {
      "get_string": self.get_string,
      "get_page_content": self.get_page_content,
    }

    self._module_refs = []
    for dirname, dictionary in [("filters", filters), ("globals", globals)]:
      for filename in self._params["source"].list_files(dirname):
        root, ext = os.path.splitext(filename)
        if ext.lower() != ".py":
          continue

        path = "%s/%s" % (dirname, filename)
        code = self._params["source"].read_file(path)
        module = imp.new_module(root.replace("/", "."))
        exec code in module.__dict__

        name = os.path.basename(root)
        if not hasattr(module, name):
          raise Exception("Expected symbol %s not found in %s file %s" % (name, dirname, filename))
        dictionary[name] = getattr(module, name)

        # HACK: The module we created here can be garbage collected because it
        # isn't added to sys.modules. If a function is called and its module is
        # gone it might cause weird errors (imports and module variables
        # unavailable). We avoid this situation by keeping a reference.
        self._module_refs.append(module)

    self._env = jinja2.Environment(loader=self._SourceLoader(self._params["source"]), autoescape=True)
    self._env.filters.update(filters)
    self._env.globals.update(globals)

  def get_html(self, source):
    template = self._env.from_string(source)
    module = template.make_module(self._params)
    for key, value in module.__dict__.iteritems():
      if not key.startswith("_"):
        self._params[key] = value

    result = unicode(module)
    result = self.process_links(result)
    return result

  def translate(self, default, name, comment=None):
    # Note: We currently ignore the comment, it is only relevant when
    # generating the master translation.
    localedata = self._params["localedata"]
    return jinja2.Markup(self.localize_string(name, default, localedata, html_escapes))

  def get_string(self, name, page):
    localedata = self._params["source"].read_locale(self._params["locale"], page)
    default = localedata[name]
    return jinja2.Markup(self.localize_string(name, default, localedata, html_escapes))

  def get_page_content(self, page, locale=None):
    from cms.utils import get_page_params

    if locale is None:
      locale = self._params["locale"]
    return get_page_params(self._params["source"], locale, page)

  def linkify(self, page, locale=None, **attrs):
    if locale is None:
      locale = self._params["locale"]

    locale, url = self._params["source"].resolve_link(page, locale)
    return jinja2.Markup('<a%s>' % ''.join(
      ' %s="%s"' % (name, jinja2.escape(value)) for name, value in [
        ('href', url),
        ('hreflang', locale)
      ] + attrs.items()
    ))

  def toclist(self, content):
    flat = []
    for match in re.finditer(r'<h(\d)\s[^<>]*\bid="([^<>"]+)"[^<>]*>(.*?)</h\1>', content, re.S):
      flat.append({
        "level": int(match.group(1)),
        "anchor": jinja2.Markup(match.group(2)).unescape(),
        "title": jinja2.Markup(match.group(3)).unescape(),
        "subitems": [],
      })

    structured = []
    stack = [{"level": 0, "subitems": structured}]
    for item in flat:
      while stack[-1]["level"] >= item["level"]:
        stack.pop()
      stack[-1]["subitems"].append(item)
      stack.append(item)
    return structured

converters = {
  "html": RawConverter,
  "md": MarkdownConverter,
  "tmpl": TemplateConverter,
}
