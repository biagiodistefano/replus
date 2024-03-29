#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    __init__.py
    ~~~~~~~~~~~

    A wrapper for the regex library for advanced regex pattern management

    :copyright: (c) 2022 by Biagio Distefano.
    :license: MIT
"""

__title__ = 'replus'
__version__ = '0.3.0'
__author__ = 'Biagio Distefano'


import abc
import json
import os
from pathlib import Path
from typing import Any, List, Tuple, Union, Dict, Optional, Generator
from collections import Counter
from collections import defaultdict

import regex

from .exceptions import NoSuchGroup, UnknownTemplateGroup, RepeatedSpecialGroup, PatternBuildException


class Replus:

    """
    The Replus engine class builds and compiles regular expressions based on templates.

    :ivar group_counter: a Counter object to count group name occurrence on each template
    :ivar patterns: a list of tuples made of [(key, pattern, template), ...]
    :ivar patterns_src: a dict containing all of patterns_dir/\\*.json combined together, "patterns" excluded
    :ivar patterns_all: all patterns that can be run, e.g. {"dates": [pattern0, pattern1], ...}
    :ivar all_groups: a dict of list with the templates as keys, e.g. {pattern_template_a: [group_0, group_1],
                    pattern_template_b: [group_0, group_1]}
    :ivar flags: the regex flags to compile the patterns
    :ivar whitespace_noise: a pattern to replace white space in the template
    """

    group_pattern = r"{{((?P<special>#|\?[:>!=]|\?[aimsxl]:|\?<[!=])?(?P<key>[\w_]+)(@(?P<index>\d+))?)}}"  # regex used to match the groups' placeholder  # noqa E501

    def __init__(
            self,
            patterns_dir_or_dict: Union[str, os.PathLike, Dict[str, Dict]],
            whitespace_noise: Optional[str] = None, flags: Optional[int] = regex.V0
    ):
        """
        Instantiates the Replus engine

        :param patterns_dir_or_dict: the path to the directory where the \\*.json pattern templates are stored or a dict
                                    of dicts with the patterns.
        :type patterns_dir_or_dict: Union[os.PathLike, Dict[str, Dict]]

        :param whitespace_noise: a pattern to replace white space in the template
        :type whitespace_noise: str, defaults to None

        :param flags: the regex flags to compile the patterns
        :type flags: int, defaults to regex.V0
        """

        self.group_counter: Counter = Counter()
        self.patterns: List[Tuple[str, regex.Pattern, str]] = []
        self.patterns_src: Dict[str, List[str]] = {}
        self.patterns_all: Dict[str, List[str]] = {}
        self.all_groups: Dict[str, List[str]] = defaultdict(list)
        self.patterns_src, self.patterns_all = self._load_models(patterns_dir_or_dict)
        self.flags = flags
        self.whitespace_noise = whitespace_noise
        self._build_patterns()

    def parse(
        self,
        string: str,
        filters: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        pos: Optional[int] = None,
        endpos: Optional[int] = None,
        flags: Optional[int] = 0,
        overlapped: Optional[bool] = False,
        partial: Optional[bool] = False,
        concurrent: Optional[bool] = None,
        timeout: Optional[float] = None,
        ignore_unused: Optional[bool] = False,
        **kwargs: Any
    ) -> Union[List["Match"], List["Group"]]:
        """
        Returns a list of Match objects

        :param string: the string to parse
        :type string: str

        :param filters: one or more pattern types to parse; if none is provided, all will be used
        :type filters: List[str]

        :param exclude: a list of pattern types to exclude
        :type exclude: List[str], defaults to None

        :param pos: starting position of the matching
        :type pos: int, defaults to None

        :param endpos: ending position of the matching
        :type endpos: int, defaults to None

        :param flags: flags to use while matching
        :type flags: int, defaults to 0

        :param overlapped: if True will allow overlapping matches
        :type overlapped: bool, defaults to False

        :param partial: if True will allow partial matches
        :type partial: bool, defaults to False

        :param concurrent: if True will run concurrently
        :type concurrent: bool, defaults to None

        :param timeout: timeout for matching
        :type partial: float, defaults to None

        :param ignore_unused: ignore unused
        :type ignore_unused: bool, defaults to False

        :return: a list of Match objects
        :rtype: List[Match]
        """

        if filters is None:
            filters = []
        if exclude is None:
            exclude = []
        matches = []
        for k, pattern, template in self.patterns:
            if filters and k not in filters or (k in exclude):
                continue
            for m in regex.finditer(
                pattern=pattern,
                string=string,
                flags=flags,
                pos=pos,
                endpos=endpos,
                overlapped=overlapped,
                partial=partial,
                concurrent=concurrent,
                timeout=timeout,
                ignore_unused=ignore_unused,
                **kwargs
            ):
                match = Match(k, m, self.all_groups[template], pattern)
                matches.append(match)
        if not overlapped:
            return self.purge_overlaps(matches)
        matches.sort(key=lambda x: x._start)
        return matches

    def search(
        self,
        string: str,
        filters: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        pos: Optional[int] = None,
        endpos: Optional[int] = None,
        flags: Optional[int] = 0,
        overlapped: Optional[bool] = False,
        partial: Optional[bool] = False,
        concurrent: Optional[bool] = None,
        timeout: Optional[float] = None,
        ignore_unused: Optional[bool] = False,
        **kwargs: Any
    ) -> Optional[Union["Match", "Group"]]:
        """
        Returns a single Match object

        :param string: the string to parse
        :type string: str

        :param filters: one or more pattern types to parse; if none is provided, all will be used
        :type filters: Tuple[str]

        :param exclude: a list of pattern types to exclude
        :type exclude: List[str], defaults to None

        :param pos: starting position of the matching
        :type pos: int, defaults to None

        :param endpos: ending position of the matching
        :type endpos: int, defaults to None

        :param flags: flags to use while matching
        :type flags: int, defaults to 0

        :param overlapped: if True will allow overlapping matches
        :type overlapped: bool, defaults to False

        :param partial: if True will allow partial matches
        :type partial: bool, defaults to False

        :param concurrent: if True will run concurrently
        :type concurrent: bool, defaults to None

        :param timeout: timeout for matching
        :type partial: float, defaults to None

        :param ignore_unused: ignore unused
        :type ignore_unused: bool, defaults to False

        :return: a Match object
        :rtype: Match
        """

        for m in self.parse(
            string=string,
            filters=filters,
            exclude=exclude,
            flags=flags,
            pos=pos,
            endpos=endpos,
            overlapped=overlapped,
            partial=partial,
            concurrent=concurrent,
            timeout=timeout,
            ignore_unused=ignore_unused,
            **kwargs
        ):
            return m
        return None

    def _build_patterns(self) -> None:
        for key, patterns in self.patterns_all.items():
            for pattern in patterns:
                self.group_counter = Counter()
                try:
                    self.patterns.append(
                        (
                            key,
                            regex.compile(self._build_pattern(pattern, pattern), flags=self.flags),
                            pattern
                        )
                    )
                except Exception as e:
                    raise PatternBuildException(f"Fatal error building patterns in file '{key}.json'", *e.args)

    def _build_pattern(self, pattern: str, template: str) -> str:
        for group_match in regex.finditer(self.group_pattern, pattern):
            return self._build_pattern(self._build_group(group_match, pattern, template), template)
        if self.whitespace_noise is not None:
            pattern = regex.sub(r" +|\\\s+", f"({self.whitespace_noise})", pattern)
        return pattern

    def _build_group(self, group_match: regex.regex.Match, pattern: str, template: str) -> str:
        group_key = group_match.group("key")
        special = group_match.group("special")
        alts = self.patterns_src.get(group_key)
        if alts is not None:
            group_count = self.group_counter[group_key]
            if special is None:
                new_pattern = pattern.replace(
                    f"{{{{{group_key}}}}}",
                    f"(?P<{group_key}_{group_count}>{self._pipe_together(alts)})",
                    1
                )
                self.all_groups[template].append(f"{group_key}_{group_count}")
                self.group_counter[group_key] += 1
            else:
                if special == "#":
                    back_reference_index = int(group_match.group("index")) if group_match.group("index") else 1
                    assert group_count >= back_reference_index, f"Attempting to reference non-existing group: " \
                                                                f"{group_key}_{group_count - back_reference_index}"
                    new_pattern = pattern.replace(
                        f"{{{{{group_match.group(1)}}}}}",
                        f"(?P={group_key}_{group_count - back_reference_index})",
                        1
                    )
                else:
                    new_pattern = pattern.replace(
                        f"{{{{{special+group_key}}}}}",
                        f"({special}{self._pipe_together(alts)})",
                        1
                    )
                    self.group_counter[group_key] += 1
        else:
            if special:
                raise Exception(f"`{special}{group_key}` does not exist. Template: {template!r}")
            for sk in ["?:", "?>", "?!", "?=", "?<=", "?<!", "?a:", "?i:", "?m:", "?s:", "?x:", "?l:"]:
                alts = self.patterns_src.get(f"{sk}{group_key}")
                if alts is not None:
                    new_pattern = pattern.replace(
                        f"{{{{{group_key}}}}}",
                        f"({sk}{self._pipe_together(alts)})"
                    )
                    assert new_pattern != pattern, f"Could not build pattern '{group_key}'"
                    return new_pattern
            raise UnknownTemplateGroup(group_key)
        return new_pattern

    @staticmethod
    def _pipe_together(alts: List[str]) -> str:
        return "|".join(alts)

    @staticmethod
    def purge_overlaps(matches: Union[List["Match"], List["Group"]]) -> Union[List["Match"], List["Group"]]:
        """
        Purge the list of Match and Group objects from overlapping instances

        :param matches: a list of Match or Group objects
        :type matches: Union[List[Match], List[Group]]

        :return: a list of Match or Group objects
        :rtype: Union[List[Match], List[Group]]
        """

        matches.sort(key=lambda x: x._start)
        purged: Union[List["Match"], List["Group"]] = []  # type: ignore
        if len(matches) <= 1:
            return matches
        purged.append(matches[0])  # type: ignore
        for m in matches[1:]:
            if m._start >= purged[-1]._end:
                purged.append(m)  # type: ignore
            else:
                if m._end >= purged[-1]._end:
                    if m.length > purged[-1].length:
                        purged.pop()
                        purged.append(m)  # type: ignore
        return purged

    @staticmethod
    def _load_models(
            patterns: Union[str, os.PathLike, Dict[str, Dict[str, List[str]]]]
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        def _iter_from_path(patterns_path: Union[str, os.PathLike]) -> Generator[Tuple[Path, str, Dict[str, List[str]]], None, None]:  # noqa E501
            patterns_path = Path(patterns_path).absolute()
            for pattern_filepath_ in patterns_path.iterdir():
                if not (pattern_filepath_.is_file() and pattern_filepath_.suffix == ".json"):
                    continue
                patterns_name_ = pattern_filepath_.stem
                with pattern_filepath_.open("r") as f:
                    config_obj_ = json.load(f)
                yield pattern_filepath_, patterns_name_, config_obj_

        def _iter_from_dict(patterns_dict: Dict[str, Dict]) -> Generator[Tuple[str, str, Dict[str, List[str]]], None, None]:  # noqa E501]:
            for patterns_name_, config_obj_ in patterns_dict.items():
                yield patterns_name_, patterns_name_, config_obj_

        if isinstance(patterns, (str, os.PathLike)):
            patterns_iterator = _iter_from_path(patterns)
        elif isinstance(patterns, dict):
            patterns_iterator = _iter_from_dict(patterns)  # type: ignore
        else:
            raise TypeError(f"'patterns' must be of type str, os.PathLike or dict, got {type(patterns)} instead")
        patterns_src: Dict[str, List[str]] = {}
        patterns_all: Dict[str, List[str]] = {}
        loaded: Dict[str, str] = {}
        for pattern_filepath, patterns_name, config_obj in patterns_iterator:
            if run_patterns := config_obj.pop("$PATTERNS", None):
                patterns_all[patterns_name] = run_patterns
            for k in config_obj:
                if k in loaded:
                    raise KeyError(
                        f"Duplicated pattern name \"{k}\" in {str(pattern_filepath)} "
                        f"already loaded from {loaded[k]}"
                    )
                else:
                    loaded[k] = str(pattern_filepath)
            patterns_src.update(config_obj)
        return patterns_src, patterns_all


class AbstractMatch(abc.ABC):

    def serialize(self) -> dict:
        """
        Returns a dict representation of the Match object structured as follows

        .. code-block::

            o = {
                "key": self.key,
                "name": self.name,
                "offset": self.offset,
                "value": self.value,
                "groups": {subgroup_0: [group_object.serialize()]}
            }

        :return: a dict representation of the Match object
        :rtype: dict
        """

        if type(self) is Group:
            o = {"key": self.key, "name": self.name}  # type: ignore
        else:
            o = {"type": self.type}  # type: ignore
        o.update({
            "offset": self.offset,  # type: ignore
            "value": self.value,  # type: ignore
            "groups": defaultdict(list)
        })
        for g in self.groups(root=True):
            o["groups"][g.key].append(g.serialize())
        o["groups"] = dict(o["groups"])
        return o

    @abc.abstractmethod
    def groups(self, group_query: Optional[str] = None, root: bool = False) -> List["Group"]:
        """"""

    def start(self, group_name: Optional[str] = None, rep_index: Optional[int] = None) -> int:
        """
        Returns the start character index of self or of Group with group_name

        :param group_name: the name of the group
        :type group_name: str, defaults to None

        :param rep_index: the repetition index of the group
        :type rep_index: int, defaults to 0

        :return: the start index of the Match
        :rtype: int
        """

        if rep_index is None:
            rep_index = getattr(self, "rep_index", 0)

        if group_name is not None:
            if group := self.group(group_name):
                return group.start(rep_index=rep_index)
            raise NoSuchGroup(group_name)
        if type(self) is Group:
            return self.match.starts(self.name)[rep_index]  # type: ignore
        return self.match.start()  # type: ignore

    def end(self, group_name: Optional[str] = None, rep_index: Optional[int] = None) -> int:
        """
        Returns the end character index of self or of Group with group_name

        :param group_name: the name of the group
        :type group_name: str, defaults to None

        :param rep_index: the repetition index of the group
        :type rep_index: int, defaults to 0

        :return: the end index of the Match
        :rtype: int
        """

        if rep_index is None:
            rep_index = getattr(self, "rep_index", 0)

        if group_name is not None:
            if group := self.group(group_name):
                return group.end(rep_index=rep_index)
            raise NoSuchGroup(group_name)
        if type(self) is Group:
            return self.match.ends(self.name)[rep_index]  # type: ignore
        return self.match.end()  # type: ignore

    def span(self, group_name: Optional[str] = None, rep_index: Optional[int] = None) -> Tuple[int, int]:
        """
        Returns the span of self or of Group with group_name

        :param group_name: the name of the group
        :type group_name: str, defaults to None

        :param rep_index: the repetition index of the group
        :type rep_index: int, defaults to 0

        :return: the span of the Match
        :rtype: Tuple[int]
        """

        if rep_index is None:
            rep_index = getattr(self, "rep_index", 0)

        if group_name is not None:
            if group := self.group(group_name):
                return group.span(rep_index=rep_index)
            raise NoSuchGroup(group_name)
        if type(self) is Group:
            return self.match.spans(self.name)[rep_index]  # type: ignore
        return self.match.span()  # type: ignore

    def group(self, group_name: str) -> Optional["Group"]:
        """
        Returns a Group object with the given group_name or None

        :param group_name: the name of the group
        :type group_name: str

        :return: a Group object
        :rtype: Optional[Group]
        """

        for group in self.groups(group_name):
            return group
        return None

    def first(self) -> Optional["Group"]:
        """
        Returns the first Group object or None

        :return: the first Group object
        :rtype: Union[Group, None]
        """

        for group in self.groups():
            return group
        return None

    def last(self) -> Optional["Group"]:
        """
        Returns the last Group object or None

        :return: the last Group object
        :rtype: Union[Group, None]
        """

        for group in reversed(self.groups()):
            return group
        return None

    def json(self, *args: Any, **kwargs: Any) -> str:
        """
        Returns a json-string of the serialized object

        :return: a json-string of the serialized object
        :rtype: str
        """

        return json.dumps(self.serialize(), *args, **kwargs)


class Match(AbstractMatch):

    """
    A Match object is an abstract and expanded representation of a regex.regex.Match

    :ivar type: the type of the match, corresponding to the stem of the file of the pattern's template
    :ivar match: a regex.regex.Match object
    :ivar partial: if it's a partial match
    :ivar value: the string value of the match
    :ivar offset: the offset of the match ``{"start": int, "end": int}``
    :ivar pattern: the string representation of the pattern that matched
    :ivar length: the length of the match (no. of characters)
    :ivar all_group_names: all the names of all the groups for the corresponding pattern for this match
    :ivar _start: the start offset of the Match
    :ivar _end: the end offset Match
    :ivar _span: the span of the Match (_start, _end)
    """

    def __init__(
            self,
            match_type: str,
            match: regex.regex.Match,
            all_groups_names: List[str],
            pattern: regex.regex.Pattern
    ):
        """
        Instantiates a Match object

        :param match_type: the type of the match, corresponding to the stem of the file of the pattern's template
        :type match_type: str

        :param match: a regex.regex.Match object
        :type match: regex.regex.Match

        :param all_groups_names: all the names of all the groups for the corresponding pattern for this match
        :type all_groups_names: List[str]

        :param pattern: the pattern that matched
        :type: pattern: regex.regex.Pattern
        """

        self.type = match_type
        self.match = match
        self.partial = match.partial
        self.value = match.group()
        self.offset = {"start": self.start(), "end": self.end()}
        self.pattern = pattern.pattern
        self.length = self.end() - self.start()
        self.all_group_names = all_groups_names
        self._start = self.start()
        self._end = self.end()
        self._span = self.span()

    def groups(self, group_query: Optional[str] = None, root: bool = False) -> List["Group"]:
        """
        Returns a list of repeated Group objects that belong to the Match object

        :param group_query: the name of the group to find repetitions of
        :type group_query: str, defaults to None

        :param root: includes the root if True
        :type root: bool, defaults to False

        :return: a list of Group objects
        :rtype: List[Group]
        """

        groups = []
        all_groups = [group_query] if group_query is not None else self.all_group_names
        for group_name in all_groups:
            i = 0
            group_i = group_name
            while True:
                if group_query is not None:
                    group_i = f"{group_name}_{i}"
                try:
                    g = self.match.group(group_i)
                    if g is not None:
                        for j, (start, end) in enumerate(self.match.spans(group_i)):
                            if self._start <= start and end <= self._end:
                                groups.append(Group(self.match, group_i, self, rep_index=j))
                except IndexError:
                    break
                if group_query is None:
                    break
                i += 1
        groups.sort(key=lambda x: x._start)
        if root:
            return Replus.purge_overlaps(groups)  # type: ignore
        return groups
    
    def __repr__(self) -> str:
        return f"<[Match {self.type}] span{self._span}: {self.value}>"

    
class Group(AbstractMatch):

    """
    A Group object is an abstract and expanded representation of a regex.regex.Match

    :ivar root: the root Match object
    :ivar match: a regex.regex.Match object
    :ivar name: the name of the group, including its rep_index. E.g.: date_0
    :ivar key: the key of the group, i.e. the name without the rep_index
    :ivar value: the string value of the match
    :ivar offset: the offset of the match ``{"start": int, "end": int}``
    :ivar length: the length of the match (no. of characters)
    :ivar rep_index: the repetition index
    :ivar _start: the start offset of the Match
    :ivar _end: the end offset Match
    :ivar _span: the span of the Match (_start, _end)
    """

    def __init__(self, match: regex.regex.Match, group_name: str, root: Match, rep_index: int = 0):
        self.root = root
        self.match = match
        self.name = group_name
        self.key = regex.sub(r"_\d+$", r"", self.name)
        self.value = match.captures(group_name)[rep_index]
        self.rep_index = rep_index
        self.offset = {"start": self.start(), "end": self.end()}
        self.length = self.end() - self.start()
        self._start = self.start()
        self._end = self.end()
        self._span = self.span()

    def groups(self, group_query: Optional[str] = None, root: bool = False) -> List["Group"]:
        """
        Returns a list of repeated Group objects that belong to the Group object

        :param group_query: the name of the group to find repetitions of
        :type group_query: str, defaults to None

        :param root: includes the root if True
        :type root: bool, defaults to False

        :return: a list of Group objects
        :rtype: List[Group]
        """

        def is_next(g1: str, g2: str) -> bool:
            return self.root.all_group_names.index(g1) > self.root.all_group_names.index(g2)

        groups = []
        all_groups = [group_query] if group_query is not None else self.root.all_group_names
        for group_name in all_groups:
            i = 0
            group_i = group_name
            while True:
                if group_query is not None:
                    group_i = f"{group_name}_{i}"
                if self.name != group_i:  # doesn't return itself, just its children
                    try:
                        g = self.match.group(group_i)
                        if g is not None and is_next(group_i, self.name):  # returning just its children
                            for j, (start, end) in enumerate(self.match.spans(group_i)):
                                if self._start <= start and end <= self._end:
                                    groups.append(self.__class__(self.match, group_i, self.root, rep_index=j))
                    except IndexError:
                        break
                if group_query is None:
                    break
                i += 1
        groups.sort(key=lambda x: x._start)
        if root:
            return Replus.purge_overlaps(groups)  # type: ignore
        return groups

    def reps(self) -> List["Group"]:
        """
        Returns a list of the Group object's repetitions

        :return: a list of the Group object's repetitions
        :rtype: List[Group]
        """

        if len(self.match.starts(self.name)) > 1:
            return [
                self.__class__(self.match, self.name, self.root, rep_index=i)
                for i in range(len(self.match.starts(self.name)))
            ]
        return []

    def __repr__(self) -> str:
        return f"<Group {self.name} span{self._span} @{self.rep_index}: '{self.value}'>"
