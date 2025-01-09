import os
from pathlib import Path

import polars as pl

csv_file = Path(__file__).parent / "starwars_data.csv"
if not os.path.exists(csv_file):
    import urllib.request

    url = "https://raw.githubusercontent.com/tidyverse/dplyr/fb25640fa1eb74746a7a74a06090045106e5d20f/data-raw/starwars.csv"
    urllib.request.urlretrieve(url, csv_file)


starwars_data = pl.read_csv(
    csv_file,
    dtypes={"height": pl.Int32, "mass": pl.Float32, "birth_year": pl.Float32},  # pyright: ignore[reportCallIssue]
    null_values=["NA"],
)

starwars_relationships = [
    {"parent": "Yoda", "child": "Dooku", "relationship": "light"},
    {"parent": "Dooku", "child": "Qui-Gon Jinn", "relationship": "light"},
    {"parent": "Qui-Gon Jinn", "child": "Obi-Wan Kenobi", "relationship": "light"},
    {"parent": "Obi-Wan Kenobi", "child": "Anakin Skywalker", "relationship": "light"},
    {"parent": "Anakin Skywalker", "child": "Luke Skywalker", "relationship": "blood"},
    {"parent": "Obi-Wan Kenobi", "child": "Luke Skywalker", "relationship": "light"},
    {"parent": "Palpatine", "child": "Dooku", "relationship": "dark"},
    # {"parent": "Dooku", "child": "Anakin Skywalker", "relationship": "dark"},
    # {"parent": "Anakin Skywalker", "child": "Ben Solo", "relationship": "dark"},
    # {"parent": "Ben Solo", "child": "Rey", "relationship": "light"},
    {"parent": "Leia Organa", "child": "Ben Solo", "relationship": "blood"},
    {"parent": "Han Solo", "child": "Ben Solo", "relationship": "blood"},
    {"parent": "Anakin Skywalker", "child": "Leia Organa", "relationship": "blood"},
    {"parent": "Padmé Amidala", "child": "Leia Organa", "relationship": "blood"},
    {"parent": "Padmé Amidala", "child": "Luke Skywalker", "relationship": "blood"},
    {"parent": "Cliegg Lars", "child": "Anakin Skywalker", "relationship": "blood"},
    {"parent": "Shmi Skywalker", "child": "Anakin Skywalker", "relationship": "blood"},
    {"parent": "Owen Lars", "child": "Luke Skywalker", "relationship": "blood"},
    # {"parent": "Beru Whitesun lars", "child": "Luke Skywalker", "relationship": "blood"},
    # {"parent": "C-3PO", "child": "R2-D2", "relationship": "droid"},
    # {"parent": "R2-D2", "child": "C-3PO", "relationship": "droid"},
    {"parent": "Palpatine", "child": "Anakin Skywalker", "relationship": "dark"},
    {"parent": "Leia Organa", "child": "Rey", "relationship": "blood"},
    {"parent": "Luke Skywalker", "child": "Rey", "relationship": "blood"},
    {"parent": "Palpatine", "child": "Darth Maul", "relationship": "dark"},
]

# starwars_parent_child = {
#     "Cliegg Lars": ["Anakin Skywalker"],
#     "Shmi Skywalker": ["Anakin Skywalker"],
#     "Padmé Amidala": ["Luke Skywalker", "Leia Organa"],
#     "Anakin Skywalker": ["Luke Skywalker", "Leia Organa"],
#     "Bail Prestor Organa": ["Leia Organa"],
#     "Han Solo": ["Ben Solo"],
#     "Leia Organa": ["Ben Solo", "Rey"],
#     "C-3PO": ["R2-D2"],
#     "R2-D2": ["C-3PO"],
#     "Owen Lars": ["Luke Skywalker"],
#     "Beru Whitesun lars": ["Luke Skywalker"],
#     "Luke Skywalker": ["Rey"],
# }
