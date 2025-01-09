from dataclasses import dataclass

from fastapi import FastAPI
from typing_extensions import Literal

from .starwars_data import starwars_data, starwars_relationships

app = FastAPI()


@dataclass
class Entity:
    name: str
    height: int
    mass: int
    hair_color: str
    skin_color: str
    eye_color: str
    birth_year: float
    # sex: str
    # gender: str
    homeworld: str
    species: str
    # films: list[str]
    # vehicles: list[str]
    # starships: list[str]


entities: dict[str, Entity] = {
    row["name"]: Entity(
        name=row["name"],
        height=row["height"],
        mass=row["mass"],
        hair_color=row["hair_color"],
        skin_color=row["skin_color"],
        eye_color=row["eye_color"],
        birth_year=row["birth_year"],
        homeworld=row["homeworld"],
        species=row["species"],
    )
    for row in starwars_data.iter_rows(named=True)
}

EpisodeMap = {
    1: "A New Hope",
    2: "The Empire Strikes Back",
    3: "Return of the Jedi",
    4: "The Phantom Menace",
    5: "Attack of the Clones",
    6: "Revenge of the Sith",
    7: "The Force Awakens",
}


@app.get("/names")
def get_names() -> list[str]:
    """
    Endpoint to retrieve a list of starwars character names.

    Returns
    -------
    :
        List of character
    """
    return [entity.name for entity in entities.values()]


@app.get("/character")
def get_character(name: str) -> Entity:
    """
    Endpoint to retrieve character details.

    Parameters
    ----------
    name : str
        Name of the character to retrieve

    Returns
    -------
    :
        Character details. If the character is not found, returns None.
        Character details include:
        - name: Name of the character
        - height: Height in centimeters
        - mass: Mass in kilograms
        - hair_color: Hair color
        - skin: Skin color
        - eye_color: Eye color
        - birth_year: Year of birth
        - homeworld: Name of the planet
        - species: Name of the species
    """
    for entity in entities.values():
        if entity.name == name:
            return entity
    return None


@dataclass
class Relationship:
    parent: str
    child: str
    relationship: Literal["light", "dark", "blood"]


@app.get("/relationship")
def get_relationships(name: str) -> list[Relationship]:
    """
    Endpoint to retrieve character relationships.

    Parameters
    ----------
    name : str
        Name of the character to retrieve relationships for

    Returns
    -------
    :
        List of relationships for the character. A relationship includes:
        - parent: Name of the parent character
        - child: Name of the child character
        - relationship: Type of relationship (light, dark, blood). `light` represents the Light side of the force. `dark` represents the Dark side of the force. `blood` represents a familial relationship.
    """
    relationships = []
    for relationship in starwars_relationships:
        if relationship["parent"] == name or relationship["child"] == name:
            relationships.append(Relationship(**relationship))
    return relationships
