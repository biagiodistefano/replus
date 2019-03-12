replus
======

A wrapper for Python's re library for advanced regex pattern management

Installation
-----------

``pip install replus``

or clone this repo

``git@github.com:raptored01/replus.git``

and then run

``python setup.py install``

Basic usage
-----------

The Engine loads Regular Expression **pattern templates** written in
\*.json files from the provided directory, builds and compiles them in
the following fashion:

example of template ``models/dates.json``:

::

    {
      "day": [
        "3[01]",
        "[12][0-9]",
        "0?[1-9]"
      ],
      "month": [
        "0?[1-9]",
        "1[012]"
      ],
      "year": [
        "\\d{4}"
      ],
      "date": [
        "{{day}}/{{month}}/{{year}}",
        "{{year}}-{{month}}-{{day}}"
      ],
      "patterns": [
        "{{date}}"
      ]
    }

will result in the following regex:

``(?P<date_0>(?P<day_0>[12][0-9]|0?[1-9]|3[01])/(?P<month_0>0?[1-9]|1[012])/(?P<year_0>\d{4})|(?P<year_1>\d{4})-(?P<month_1>0?[1-9]|1[012])-(?P<day_1>[12][0-9]|0?[1-9]|3[01]))``

It is possible to query as follows:

::
    from replus import Engine
    
    engine = Engine('models')
    for match in engine.parse("Look at this date: 2012-20-10"):
        print(match)
        # <[Match date] span(19, 29): 2012-12-10>

        date = match.group('date')
        print(date)
        # <[Group date_0] span(19, 29): 2012-12-10>

        day = date.group('day')
        print(day)
        # <[Group day_1] span(27, 29): 10>

        month = date.group('month')
        print(month)
        # <[Group month_1] span(24, 26): 12>

        year = date.group('year')
        print(year)
        # [Group year_1] span(19, 23): 2012>

Match objects have the following attributes:

- type: the type of match (e.g. "dates");
- match: the re.match object;
- re: the regex pattern;
- all\_group\_names: the name of all the children groups;

Both Match and Group objects have the following attributes:

- value: the string value of the match/group
- start: the beginning of the match/group relative to the input string
- end: the end of the group relative to the input string
- offset (start, end)
- length (end-start)

Group objects have the following attributes:

- name: the actual group name (e.g. date\_1);
- key: the group key (e.g. date);

Both Match and Group objects can be serialized in dicts with the ``serialize()`` method and
to a json string with the ``json`` attribute

Secondary features
~~~~~~~~~~~~~~~~~~

There are two useful secondary features:

-  ``non-capturing groups``: these are specified by using the "!" prefix
   in the group name
-  ``dynamic backreferences``: use ``#`` to reference a previous group
   and ``@<n>`` to specify how many groups behind

template:

::

    {
      "!number": [
        "\\d"
      ],
      "abg": [
        "alpha",
        "beta",
        "gamma"
      ],
      "patterns": [
        "This is an unnamed number group: {{number}}.",
        "I can match {{abg}} and {{abg}}, and then re-match the last {{#abg}} or the second last {{#abg@2}}"
      ]
    }

It will generate the following regexs:

``This is an unnamed number group: (?:\d).``

``I can match (?P<abg_0>alpha|gamma|beta) and (?P<abg_1>alpha|gamma|beta), and then re-match the last (?P=abg_1) or the second last (?P=abg_0)``

**N.B.**: in order to obtain an escape char, such as ``\d``, in the
pattern's model it **must** be double escaped: ``\\d``

Current limitations
~~~~~~~~~~~~~~~~~~~

None known
