import os

import yaml


class SyntaxErrorYAML(Exception):
    pass


class IncludeTag(yaml.YAMLObject):
    """Add an !include yaml tag

    Allows referencing yaml files from definitions
    Usage:
        my_value: !include extra.yml     # whole file
        my_value: !include extra.yml#key # just key (assuming obj is dict)
    """

    yaml_tag = "!include"

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "IncludeTag({self.value})"

    @classmethod
    def from_yaml(cls, loader, node):
        parts = node.value.split("#")
        ref = parts[1] if len(parts) > 1 else None
        root = loader.stream.name
        reference = f"in !include '{root}', line {node.start_mark.line}, column {node.start_mark.column}"

        filename = os.path.abspath(
            os.path.join(os.path.dirname(loader.stream.name), parts[0])
        )
        extension = os.path.splitext(filename)[1][1:]
        if extension not in ("yaml", "yml"):
            raise SyntaxErrorYAML(
                {
                    "error": f"!include file must have extension 'yml' or 'yaml'\n  extension was {extension}\n{reference}"
                }
            )

        with open(filename, "r") as f:
            try:
                contents = yaml.safe_load(f)
            except yaml.YAMLError as ex:
                print("yaml error")
                raise SyntaxErrorYAML({"error": ex}) from None

            else:
                if ref is not None:
                    if not isinstance(contents, dict):
                        raise SyntaxErrorYAML(
                            {
                                "error": f"!include has #{ref}, but contents of {filename} is not an object\n  type was {type(contents)}\n{reference}"
                            }
                        )

                    try:
                        return contents[ref]
                    except KeyError:
                        raise SyntaxErrorYAML(
                            {
                                "error": f"no such key '{ref}' in '{filename}'\n{reference}"
                            }
                        )

                else:
                    return contents

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, data.value)


yaml.SafeLoader.add_constructor("!include", IncludeTag.from_yaml)
