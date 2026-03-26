from readabilipy.simple_tree import simple_tree_from_html_string
from readabilipy.simple_json import simple_json_from_html_string

IN = "65d3530f61e48a0975a78f33_b69e7e75500473b13d6670ec4ec758af18e816de24bfca9897e9521cc419f88d.html"
OUT = "simplified.html"


def read_file_to_string(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_string_to_file(content: str, path: str):
    with open(path, "w", encoding="utf-8") as file:
        if isinstance(content, dict):
            import json

            file.write(json.dumps(content, indent=2))
        else:
            file.write(content)


as_simple = simple_tree_from_html_string(read_file_to_string(IN))
as_simple = as_simple.prettify()

write_string_to_file(as_simple, OUT)

as_j_simple = simple_json_from_html_string(read_file_to_string(OUT)).to_json()
as_j_complex = simple_json_from_html_string(read_file_to_string(IN)).to_json()

write_string_to_file(as_j_simple, "simplified.json")
write_string_to_file(as_j_complex, "complex.json")
