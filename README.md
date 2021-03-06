# CMS #

We use this CMS for [adblockplus.org](https://github.com/adblockplus/web.adblockplus.org/)
and related websites. It converts a directory with content data into static
files. You are free to use it for other projects but please keep in mind that we
make no stability guarantees whatsoever and might change functionality any time.

## How to use ##

### Running the test server ###

The test server will convert your content directory on the fly, your changes
will become visible immediately. To run it you need:

* Python 2.7
* [Jinja2](http://jinja.pocoo.org/) and
  [Markdown](https://pypi.python.org/pypi/Markdown) modules (can be installed by
  running `easy_install Jinja2 Markdown` from the command line)
* A current copy of the
  [cms repository](https://github.com/adblockplus/cms/) (can be
  [downloaded as ZIP file](https://github.com/adblockplus/cms/archive/master.zip)
  or cloned via `git clone https://github.com/adblockplus/cms.git`)

Optionally, the [Werkzeug](http://werkzeug.pocoo.org/) module can be installed
as well, this will provide some developer features.

Run the `runserver.py` script from your content directory, e.g.:

    python ../cms/runserver.py

Alternatively, the content directory could also be specified as command line
parameter of `runserver.py`. This will start a local web server on port 5000,
e.g. the page the page `pages/example.md` will be accessible under
`http://localhost:5000/en/example`.

Note that the test server is inefficient and shouldn't be run in production.
There you should generate static files as explained below.

### Generating the standalone test server ###

The standalone test server is a single binary, without any further dependencies.
It can be copied to another system and will no longer require Python or any of
its modules. In order to generate the standalone test server you need all the
prerequisites required to run the test server and
[PyInstaller](https://github.com/pyinstaller/pyinstaller/wiki). PyInstaller can
be installed by running `easy_install pyinstaller`.

Run the following command from the directory of the `cms` repository:

    pyinstaller runserver.spec

If successful, this will put the standalone test server into the `dist`
directory.

### Generating static files ###

On your production server you should convert the content directory into static
files. To do that you need:

* Python 2.7
* [Jinja2](http://jinja.pocoo.org/) and
  [Markdown](https://pypi.python.org/pypi/Markdown) modules (can be installed by
  running `easy_install Jinja2 Markdown` from the command line)
* A current copy of the
  [cms repository](https://github.com/adblockplus/cms/) (can be
  [downloaded as ZIP file](https://github.com/adblockplus/cms/archive/master.zip)
  or cloned via `git clone https://github.com/adblockplus/cms.git`)

Run the following command from the directory of the `cms` repository:

    python -m cms.bin.generate_static_pages www_directory target_directory

Here `www_directory` should be replaced by the path to your content directory.
`target_directory` is the path where static files will be placed.

Note: Localized versions of pages will only be generated when their translations
are at least 30% complete. (Measured by comparing the total number
of translatable strings on a page to the number of strings that have been
translated for a given locale.) This is different from the test server which
will include less complete translations.

### Syncing translations ###

Before syncing translations ensure the following:

- The `crowdin-project-name` setting has been set in the site's configuration.
- The `urllib3` Python module is installed.

Now to sync with Crowdin type the following:

    python -m cms.bin.translate www_directory crowdin_project_api_key [logging_level]

The script might take a while to run, it does the following things:

1. Requests information about your Crowdin project
2. Checks all local locales are supported by Crowdin and enabled for your project
3. Renders all pages in your default language and extracts all page strings
4. Creates any required directories in your Crowdin project
5. Uploads any new page strings and updates any existing page strings
6. Uploads any pre-existing translation files for any newly uploaded pages
7. Requests Crowdin generate a fresh translations export archive
8. Downloads the archive of translations and extracts it replacing all local
   translation files

Notes:

- You have to use the Crowdin project's API key, not your account API key
- You should probably enable "Skip untranslated strings" under your
  project settings.
- Translations are only _uploaded_ for new files. If you are syncing with
  Crowdin for the first time, and you have existing translation files pay
  attention to any warnings. If there are any problems it is recommended
  you re-create another fresh Crowdin project and try again. (Otherwise
  translations for the pages already uploaded could be lost!)
- If you are running the script from a cronjob or similar you will probably
  want to set the logging level to `ERROR` or similar

## Content structure ##

Currently, the following directories of your content directory will be
considered:

* `filters`: Custom Jinja2 filters
* `globals`: Custom Jinja2 global functions and variables
* `includes`: Various include files
* `locales`: Localization files
* `pages`: User-visible pages
* `static`: Static content
* `templates`: Page layout templates

There should also be a `settings.ini` file with configuration.

All of these are explained in more detail below.

### Configuration (settings.ini) ###

The following sections can be defined in `settings.ini`:

* `[general]`: following settings should be listed here:
  * `defaultlocale`: The fallback locale, to be used whenever no localized
    page/strings can be found for a locale.
  * `defaultpage`: the default page which is displayed by the server if the URL
    doesn't contain a page name. Note that while the test server will consider
    that setting automatically, the real server might need to be configured
    accordingly.
  * `crowdin-project-name`: The Crowdin project name, this must be set for if
    you intend to use the cms.bin.translate script to update the Crowdin
    translations.
* `[langnames]`: defines the language names correspoding to particular language
  codes.
* `[rtl]`: any language codes listed here are treated as right-to-left languages.
  The values of the settings are ignored.
* `[locale_overrides]`: every entry defines that a page should use a different
  locale file, not the one matching its name (to be used when multiple pages
  share localization data).

### Localization files ###

The language-specific data is stored in the `locales` directory. Each language
(identified by its locale code) is given a subdirectory here. The `.json` files
contain localizable strings using the following format:

    {
      "stringid": {
        "message": "Translated string",
        "description": "Optional string description"
      },
      ...
    }

Any other files are considered localizable files and will be available on the
server unchanged. This is useful for images for example: a language-dependent
image can be placed into the `locales/en` directory and a German version
of the same image into the `locales/de` directory. E.g. the file
`locales/en/foo.png` will be available on the server under the URL `/en/foo.png`.

### Pages ###

The pages are defined in the `pages` directory. The file extension defines the
format in which a page is specified and won't be visible on the web server.
The page name is prepended by the locale code in the URL, e.g. `pages/foo.md`
can be available under the URLs `/en/foo` and `/de/foo` (the English and German
versions respectively). Regardless of the format, a page can define a number of
settings using the following format:

    setting = value

Note that the settings have to placed at the beginning of the file, before the
actual content.  The following settings can be changed:

* `template`: This defines the template to be used for this page (without the
  file extension). By default the `default` template is used for all pages.
* `title`: The locale string to be used as page title. By default the `title`
  string is used.
* `noheading`: Setting this to any value will make sure no heading is displayed.
  By default a `<h1>` tag with the page title is added above the content.
* `notoc`: Setting this to any value will prevent a table of contents from being
  generated. By default a table of contents is always generated if the page
  contains any headers with an `id` attribute.

The following tag inserts an include file into the page (can be in a different
format):

    <? include foo ?>

Include files should be placed into the `includes` directory of the repository.
In the case above the contents of `includes/foo.md` or `includes/foo.tmpl` will
be inserted (whichever is present).

#### Markdown format (md) ####

This format should normally be used, it allows the pages to be defined using the
[Markdown](http://daringfireball.net/projects/markdown/syntax) syntax. Raw HTML
tags are allowed and can be used where Markdown syntax isn't sufficient. The
[Python-Markdown Extra](https://pythonhosted.org/Markdown/extensions/extra.html)
extension is active and allows specifying custom attributes for the generated
HTML tags, HTML block elements that contain Markdown and more.

Any content between `<head>` and `</head>` tags will be inserted into the head
of the generated web page, this is meant for styles, scripts and the like.
Other pages should be linked by using their name as link target (relative links),
these links will be resolved to point to the most appropriate page language.
Embedding localizable images works the same, use the image name as image source.

Localizable strings can be specified inline with the following syntax:

    {{string_name String contents in default language}}

Try to give the string a descriptive name as it will help translators.
Optionally you can add a description for strings as well to provide even more
context:

    {{string_name[The string description] String contents}}

_Note: String names and descriptions have no effect on the generated page,
assuming string name is unique to the page. The name and description are just
used to provide translators with additional context about the string._

Finally if you find yourself using the same string multiple times in a page
you can reduce duplication by simply omitting the description and contents
after the first use. For example:

    {{title[Title of the page] Adblock Plus - Home}}
    {{title}}

#### Raw HTML format (html) ####

This format is similar to the Markdown format but uses regular HTML syntax.
No processing is performed beyond inserting localized strings and resolving
links to pages and images. This format is mainly meant for legacy content.
The syntax for localizable strings documented above can be used as with
Markdown.

#### Jinja2 format (tmpl) ####

Complicated pages can be defined using the
[Jinja2 template format](http://jinja.pocoo.org/docs/templates/). Automatic
escaping is active so by default values inserted into the page cannot contain
any HTML code. Any content between `<head>` and `</head>` tags will be inserted
into the head of the generated web page, everything else defined the content of
the page.

The following variables can be used:

* `page`: The page name
* `config`: Contents of the `settings.ini` file in this repository (a
  [configparser object](http://docs.python.org/2/library/configparser.html))
* `locale`: Locale code of the page language
* `available_locales`: Locale codes of all languages available for this page

Following custom filters can be used:

* `translate(default, name, comment=None)`: translates the given default string
   and string name for the current page and locale. The string name should be
   unique for the page but otherwise is only seen by the translators. Optionally
   a comment (description) can be specified to help provide the translators with
   additional context.
* `linkify(url, locale=None, **attrs)`: generates an `<a href="...">` tag for
   the URL. If the URL is a page name it will be converted into a link to the
   most appropriate page language. The language used can also be specified
   manually with the locale parameter. Any further keyword arguments passed
   are turned into additional HTML attributes for the tag.
* `toclist(html)`: extracts a list of headings from HTML code, this can be used
  to generate a table of contents.

The following global functions can be used:

* `get_string(name, page=None)`: retrieves a string from a locale file.
  Unless a page is specified the locale file matching the name of the current
  page is used.
* `get_page_content(page, locale=None)`: returns a dictionary of the content
  and params for the given page and locale. Locale defaults to the current one
  if not specified. Provided keys include `head`, `body`, `available_locales`
  and `translation_ratio`.

### Static files ###

Any files located in the `static` directory will be available on the server
unchanged. The file `static/css/foo.css` will be available under the URL
`/css/foo.css`.

### Templates ###

The templates specified in the `templates` directory specify the overall
structure that is common for all pages. These templates should have the file
extension `tmpl` and use the [Jinja2 template format](http://jinja.pocoo.org/docs/templates/).
The differences to pages using the same format are:

* No special treatment of the `<head>` tag.
* Additional variables `head` and `body` are defined with the HTML code that
  should be added to the head and content of the page respectively.

By default, `default.tmpl` will be used for all pages. If other templates are
defined, the pages need to choose them explicitly using the `template` setting.

### Custom filters ###

The `filters` directory can define custom Jinja2 filters which will be available
in all Jinja2 templates. The file name defines the filter name, e.g.
`filters/myfilter.py` will define a filter named `myfilter`. This file should
also contain a function called `myfilter`, this one will be called when the
filter is invoked. For more information on Jinja2 filters see
[official documentation](http://jinja.pocoo.org/docs/dev/api/#writing-filters).

### Custom functions and variables ###

The `globals` directory can define custom Jinja2 globals which will be available
in all Jinja2 templates. Typically, this is used for custom functions. The file
name should match the name of the function or variable to be defined, and export
a variable with that name. E.g. `globals/myfunction.py` can define a function
called `myfunction` that will become available to all Jinja2 templates.
