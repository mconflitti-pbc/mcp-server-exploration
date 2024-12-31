import re
from pathlib import Path

import yaml


def find_value(root, path):
    """
    Find a value in an object graph.

    This function is used to follow the specified path through the object graph at root
    and return the item in the graph, if any, that the path refers to.

    :param root: the root of the object graph to traverse.
    :param path: the path through the graph to take.
    :return: the resulting value or None.
    """
    if isinstance(path, str):
        path = path.split("/")
    parent = root
    for part in path:
        if part in parent:
            parent = parent[part]
        else:
            return None
    return parent


def expand_refs(document, obj):
    """
    Expands `ref`s in the given object.

    Returns an object semantically equivalent to the original but with references expanded.

    Parameters
    ----------
    document
        the master swagger document containing the responses and definitions.
    obj
        is either a normal swagger object, a ref object, or a swagger object with a schema.
    """
    if isinstance(obj, list):
        return [expand_refs(document, item) for item in obj]
    elif isinstance(obj, dict):
        if "$ref" in obj:
            ref_path = obj["$ref"].strip("#/").split("/")
            ref_value = find_value(document, ref_path)
            if ref_value is None:
                raise RuntimeError(f"Reference {obj['$ref']} not found in the document.")
            return expand_refs(document, ref_value)
        else:
            return {key: expand_refs(document, value) for key, value in obj.items()}
    else:
        return obj


def expand_all_references(document):
    """
    Expands all JSON references.

    Expands all references ($ref) in the merged swagger document by replacing them with
    their full definitions. This modifies the document in place.

    Args:
        document: The dictionary representing the Swagger document to process
    """
    # List of error response keys to ignore
    error_responses = [
        "BadRequest",
        "Unauthorized",
        "PaymentRequired",
        "Forbidden",
        "NotFound",
        "Conflict",
        "APIError",
        "InternalServerError",
    ]

    # We need to expand refs in paths
    if "paths" in document:
        for _path, operations in document["paths"].items():
            for _method, operation in operations.items():
                # Expand refs in parameters
                if "parameters" in operation:
                    operation["parameters"] = expand_refs(document, operation["parameters"])

                # Expand refs in responses
                if "responses" in operation:
                    for code, response in operation["responses"].items():
                        if "schema" in response and code not in error_responses:
                            response["schema"] = expand_refs(document, response["schema"])

    # Expand refs in top-level parameters
    if "parameters" in document:
        document["parameters"] = expand_refs(document, document["parameters"])

    # Expand refs in top-level responses, ignoring error responses
    if "responses" in document:
        for response_key, response_value in document["responses"].items():
            if response_key not in error_responses:
                document["responses"][response_key] = expand_refs(document, response_value)

    # Expand refs in definitions
    if "definitions" in document:
        document["definitions"] = expand_refs(document, document["definitions"])


def clean_whitespace(obj):
    """
    Format white space.

    Recursively go through all values in the object, strip whitespace, and replace all sequences of
    new line with a single space.

    Args:
        obj: The object to process.

    Returns
    -------
    :
        The cleaned object.
    """
    if isinstance(obj, str):
        return re.sub(r"\s+", " ", obj).strip()
    elif isinstance(obj, list):
        return [clean_whitespace(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: clean_whitespace(value) for key, value in obj.items()}
    else:
        return obj


def expand_swagger(doc):
    # Expand all references
    expand_all_references(doc)

    # Clean whitespace
    cleaned_document = clean_whitespace(doc)

    return cleaned_document


def expand_and_save_yaml(input_yaml_path, output_yaml_path):
    """
    Reads a YAML file, expands all references ($ref), cleans whitespace, and saves the expanded document to a new YAML file.

    Args:
        input_yaml_path: The path to the input YAML file.
        output_yaml_path: The path to the output YAML file where the expanded document will be saved.
    """
    # Read the YAML file
    with open(Path(input_yaml_path).expanduser(), "r", encoding="utf-8") as file:
        document = yaml.safe_load(file)

    document = expand_swagger(document)

    # Save the expanded and cleaned document back to a new YAML file
    with open(Path(output_yaml_path).expanduser(), "w", encoding="utf-8") as file:
        yaml.dump(document, file, default_flow_style=False, sort_keys=False)


def transform_swagger_to_operation_dict(swagger_dict):
    """
    Swagger to operation dictionary transformation.

    Transforms the structure of a Swagger dictionary to create a dictionary where each entry key is
    the operation ID and the value is the definition for that operation, including the HTTP verb
    and the route.

    Args:
        swagger_dict: The dictionary representing the Swagger document.

    Returns
    -------
    :
        A dictionary where each key is an operation ID and the value is the operation definition.
    """
    operation_dict = {}

    if "paths" in swagger_dict:
        for route, operations in swagger_dict["paths"].items():
            for method, operation in operations.items():
                if "operationId" in operation:
                    operation_id = operation["operationId"]
                    operation_dict[operation_id] = {
                        "name": operation["operationId"],
                        "tags": operation["tags"],
                        "method": method,
                        "route": route,
                        "definition": operation,
                    }

    return operation_dict


if __name__ == "__main__":
    expand_and_save_yaml("swagger.yaml", "swagger-deref.yaml")
