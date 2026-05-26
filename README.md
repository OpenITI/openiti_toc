# openiti_toc : Tables of contents for OpenITI texts

This repo contains tables of contents for each OpenITI text, 
and code to generate and use these tables of contents.

The repo has a branch for each OpenITI release:

* https://github.com/OpenITI.openiti_toc/tree/v2025.1.9



## repo structure

```
|- tocs/ : all tables of contents
|- scripts/
|    |- build_toc.py : script to build OpenITI Tables of Contents
|    |- query_toc.py : Python functions to query OpenIT Tables of Contents
|- README.md : this file
```

## Structure of the TOCs

The Table of Contents are built to minimise storage 
and maximize lookup speed. 

The table of contents json files have the following keys:
    * "sections" dictionary:
        ```
        <numeric_section_id>: {
          "title": <str>,
          "level": <int>,
          "parent": <int>,
          "start_ms": <int>,
          "end_ms": <int>
        }
        ````
    * "starts" list (sorted list, for binary search): each item is a list:
        ```
        [<start_ms>, <list_of_section_ids_that_start_in_that_milestone>, <previous_open_section>]
        ```
        NB: the previous open section is a section that continues into the new milestone,
        before the first section start in that milestone.
    * "last_ms": milestone number of the last milestone in the text file
    * "filename": name of the text file

## Lookup functions

The `scripts/build_toc.py` module contains some functions that use the table of contents:

### Look up which section(s) a milestone is in: `get_milestone_headings`
For a given milestone, get all the sections that at least partially cover it.

Args:
    toc (dict): table of contents, loaded from a json file
    ms (int): milestone number
    output_format (str): either "bullets" or "breadcrumbs"
    breadcrumbs_sep (str): character to use as separator in the breadcrumbs

Two possible output formats:
    * as an indented bullet-list string (`output_format="bullets"`). Example:
        '''
        h1
          * h2
          * h3
        '''
    * breadcrumbs-style (`output_format="breadcrumbs"`). Example:
        ["h1 > h2", "h1 > h3"]


### Get the start and end milestone of a given section:

For a given section ID, get the milestone numberss where the section starts and ends.
