import re


def sanitize(name: str) -> str:
    # Replace hyphens/dots with underscores
    clean = name.replace("-", "_").replace(".", "_")
    # Python identifiers cannot start with a digit
    if clean[0].isdigit():
        clean = f"n_{clean}"
    return clean


def get_code_block(content, code_type=None):
    """
    Parse a code block from the response
    """
    code_type = code_type or r"[\w\+\-\.]*"
    pattern = f"```(?:{code_type})?\n(.*?)```"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    if content.startswith(f"```{code_type}"):
        content = content[len(f"```{code_type}") :]
    if content.startswith("```"):
        content = content[len("```") :]
    if content.endswith("```"):
        content = content[: -len("```")]
    return content.strip()
