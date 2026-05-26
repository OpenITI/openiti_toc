"""This module contains code query tables of contents of OpenITI texts.

The table of contents has the following keys:
    * "sections" dictionary:
        <numeric_section_id>: {
          "title": <str>,
          "level": <int>,
          "parent": <int>,
          "start_ms": <int>,
          "end_ms": <int>
        }
    * "starts" list (sorted list, for binary search): each item is a list:
        [<start_ms>, <list_of_section_ids_that_start_in_that_milestone>, <previous_open_section>]
        NB: the previous open section is a section that continues into the new milestone,
        before the first section start in that milestone.
    * "last_ms": milestone number of the last milestone in the text file
    * "filename": name of the text file

The module contains some functions that use the table of contents:

* get_section_milestone_range: gets the start and end milestone of a given section
* get_milestone_headings: for a given milestone, get all the sections that at least partially cover it.
    Two possible formats:
    * as an indented bullet-list string (`output_format="bullets"`). Example:
        '''
        h1
          * h2
          * h3
        '''
    * breadcrumbs-style (output_format="breadcrumbs"). Example:
        ["h1 > h2", "h1 > h3"]
"""

import json



def _find_sections(starts, ms):
    """
    Return the active sections for the given milestone.
    `starts` should be sorted on the first item in each member list (the milestone number):
    [[80, [1], None], [83, [2, 3], 1]]
    """
    lo = 0
    hi = len(starts) - 1
    previous_sections  = []

    # binary search of the list of starts:
    while lo <= hi:
        mid = (lo + hi) // 2
        start_ms, section_ids, previous_open = starts[mid]

        if start_ms == ms:
            #print("previous open:", previous_open, "; starting sections:", section_ids)
            if previous_open is None:
                return section_ids
            else:
                return [previous_open] + section_ids

        if start_ms < ms:
            previous_sections = section_ids
            lo = mid + 1
        else:
            hi = mid - 1

    # if the milestone is not found in the starts list,
    # (that is, no new section starts in that milestone),
    # return the last open section: 
    if previous_sections :
        return [previous_sections [-1]]
    else:
        return []


def _walk_tree(toc, section_id, trail=[]):
    """Find the path from the root to the section"""
    title = toc["sections"][section_id]["title"]
    trail.append(title)
    parent = toc["sections"][section_id]["parent"]
    if parent:
        trail = _walk_tree(toc, parent, trail=trail)
    return trail
    

def get_milestone_headings(toc, ms, output_format="bullets", breadcrumbs_sep=" > "): # or "breadcrumbs"
    """
    Return headings for a milestone.

    Args:
        toc (dict): table of contents, loaded from a json file
        ms (int): milestone number 
        output_format (str): either "bullets" or "breadcrumbs"
        breadcrumbs_sep (str): character to use as separator in the breadcrumbs

    Returns: 
        a string or list

    Two possible output formats:
    * as an indented bullet-list string (`output_format="bullets"`). Example:
        '''
        h1
          * h2
          * h3
        '''
    * breadcrumbs-style (`output_format="breadcrumbs"`). Example:
        ["h1 > h2", "h1 > h3"]
    """
    if ms > toc["last_ms"]:
        print("Milestone", ms, "does not exist! Last milestone in the text file is", toc["last_ms"])
        return None
    sections = _find_sections(toc["starts"], ms)
    print("Sections:", sections)

    # Build paths from root to each active section
    paths = []
    for section_id in sections:
        trail = _walk_tree(toc, section_id, trail=[])
        paths.append(list(reversed(trail)))

    if output_format == "breadcrumbs":
        return [breadcrumbs_sep.join(path) for path in paths]
    elif output_format == "bullets":
        # Convert paths into a nested dict
        tree = {}
        for path in paths:
            current = tree
            for title in path:
                #if title not in current:
                #    current[title] = {}
                current = current.setdefault(title, {})

        # Render nested dict
        lines = []

        def render(subtree, level=0):
            for title, children in subtree.items():
                if level == 0:
                    lines.append(title)
                else:
                    lines.append("  " * level + "* " + title)
                render(children, level + 1)

        render(tree)
        return "\n".join(lines)

def get_section_milestone_range(toc, section_id):
    """Get the start and end milestone of each section

    Returns: tup (start_ms, end_ms)
    """
    section = toc["sections"][section_id]
    end_ms = section["end_ms"]

    if end_ms is None:
        end_ms = max_ms

    return section["start_ms"], end_ms

def load_toc(toc_fp):
    with open(toc_fp, encoding="utf-8") as file:
        toc = json.load(file)

    # Turn the section IDs from strings into integers
    # (dictionary keys can't be integers in json)
    toc["sections"] = {int(section_id): d for section_id, d in toc["sections"].items()}

    return toc



if __name__ == "__main__":
    toc_fp = "tocs/Shamela0009783BK1-ara1_TOC.json"
    toc = load_toc(toc_fp)

    bc = get_milestone_headings(toc, 4, output_format="breadcrumbs", breadcrumbs_sep="\n")
    for b in bc:
        print(b)
        print("---------")

    print("=============")

    print(get_milestone_headings(toc, 4831, output_format="bullets"))

    print("=============")

    print(get_section_milestone_range(toc, 1234))
