"""This module contains code to build and use table of contents of OpenITI texts.

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

The module also contains some functions that use the table of contents:

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
import os
import re

from openiti.helper.funcs import get_all_text_files_in_folder

HEADING_RE = re.compile(r"^### (\|+) +(.+?)\s*$")
MILESTONE_RE = re.compile(r"\bms(\d+)")

##########
# HELPER #
##########

def _dump_json_compact_int_lists(obj, file, indent=2, ensure_ascii=False):
    """keep lists of integers compact by not indenting every item in the list"""
    text = json.dumps(obj, indent=indent, ensure_ascii=ensure_ascii)

    def compact_int_list(match):
        items = re.findall(r"-?\d+", match.group(0))
        return "[" + ", ".join(items) + "]"

    # Match lists that contain only integers, spread across lines
    text = re.sub(
        r"\[\s*-?\d+(?:\s*,\s*-?\d+)*\s*\]",
        compact_int_list,
        text,
        flags=re.MULTILINE
    )

    file.write(text)

#############################
# BUILDING TABLE OF CONTENT #
#############################

def build_toc(path, heading_re=HEADING_RE, milestone_re=MILESTONE_RE, outfp=None, indent=2):
    """Build a table of contents for an OpenITI text file

    The table of contents has the following keys:
        * "sections" dictionary:
            <numeric_id>: {
              "title": <str>,
              "level": <int>,
              "parent": <int>,
              "start_ms": <int>,
              "end_ms": <int>
            }
        * "starts" list (sorted list, for binary search): each item is a list:
            [<start_ms>, <list_of_section_ids_that_start_in_that_milestone>]
        * "last_ms": milestone number of the last milestone in the text file
        * "filename": name of the text file

    Returns: dict {"sections": {}, "starts": {}, "last_ms": int}
    """
    sections = {}
    starts = {}

    stack = []          # active section IDs by level
    current_ms = 1
    section_count = 0

    with open(path, encoding="utf-8") as f:
        for line in f:
            # Update current milestone if this line contains one
            m = milestone_re.search(line)
            if m:
                current_ms = int(m.group(1)) + 1  # milestone marker is at end of the milestone
                line_contains_milestone = True
            else:
                line_contains_milestone = False
                

            # Detect heading
            h = heading_re.match(line)
            if not h:
                continue

            # if the heading starts does not start in the line of the new milestone,
            # the previous section continues in the current milestone:
            if not line_contains_milestone:
                previous_open = stack[-1] if stack else None
            else:
                previous_open = None

            pipes, title = h.groups()
            level = len(pipes)
            title = re.sub(" *ms\d+ *", " ", title).strip()

            section_count += 1
            section_id = section_count

            if level > 1 and len(stack) >= level - 1:
                parent_id = stack[level - 2]
            else:
                parent_id = None

            sections[section_id] = {
                "title": title,
                "level": level,
                "parent": parent_id,
                "start_ms": current_ms,
                "end_ms": None
            }

            # New heading closes any active section at this level or below
            for old_section_id in stack[level - 1:]:
                sections[old_section_id]["end_ms"] = current_ms

            # Trim stack to parent level, then add this heading
            stack = stack[:level - 1]
            stack.append(section_id)

            # add to the starts dictionary
            #if current_ms not in starts:
            #    starts[current_ms] = []
            #starts[current_ms].append(section_id)
            if current_ms not in starts:
                starts[current_ms] = {
                    "sections": [],
                    "previous_open": previous_open
                }
            starts[current_ms]["sections"].append(section_id)

    toc = {
        "filename": os.path.split(path)[-1],
        "sections": sections,
        "starts": [[start, data["sections"], data["previous_open"]] for start, data in starts.items()],
        "last_ms": current_ms-1
    }

    if outfp:
        with open(outfp, "w", encoding="utf-8") as file:
            _dump_json_compact_int_lists(toc, file, indent=indent, ensure_ascii=False)

    return toc

def build_tocs_for_folder(folder, outfolder, indent=2, overwrite=False,
                          heading_re=HEADING_RE, milestone_re=MILESTONE_RE):
    for fp in get_all_text_files_in_folder(folder):
        fn = os.path.split(fp)[-1]
        outfn = fn.split(".")[2].split("-")[0] + "_TOC.json"
        outfp = os.path.join(outfolder, outfn)
        print(outfn)
        if overwrite or not os.path.exists(outfp):
            build_toc(fp, outfp=outfp, indent=indent,
                      heading_re=heading_re, milestone_re=milestone_re)


##########################
# USING TABLE OF CONTENT #
##########################

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

    Two possible output formats:
    * as an indented bullet-list string (`output_format="bullets"`). Example:
        '''
        h1
          * h2
          * h3
        '''
    * breadcrumbs-style (output_format="breadcrumbs"). Example:
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
    corpus_folder = "/home/admin-kitab/Documents/OpenITI/RELEASE_git/RELEASE/data"
    corpus_folder = "../corpus/RELEASE_private/data"
    build_tocs_for_folder(corpus_folder, "../tocs")
    
    
##    fp = r"C:\Users\peter.verkinderen\Documents\OpenITI\all_repos\25Y_repos\0325AH\data\0310Tabari\0310Tabari.Tarikh\0310Tabari.Tarikh.Shamela0009783BK1-ara1.mARkdown"
##    toc_fp = "tabari_toc_w_spaces.json"
##    #toc = build_toc(fp, outfp=toc_fp)
##    toc = load_toc(toc_fp)
##
##    bc = get_milestone_headings(toc, 4, output_format="breadcrumbs", breadcrumbs_sep="\n")
##    for b in bc:
##        print(b)
##        print("---------")
##        
##    print("=============")
##
##    print(get_milestone_headings(toc, 4831, output_format="bullets"))
##    
##    print("=============")
##    
##    print(get_section_milestone_range(toc, 1234))
