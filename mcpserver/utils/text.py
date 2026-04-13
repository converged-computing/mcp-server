import json
import re


def sanitize(name: str) -> str:
    """
    Sanitize worker ids and arguments for hub properties.
    """
    # Replace hyphens/dots with underscores
    clean = name.replace("-", "_").replace(".", "_")
    # Python identifiers cannot start with a digit
    if clean[0].isdigit():
        clean = f"n_{clean}"
    return clean


def format_calls(calls_block):
    """
    The secretary agent can return calls. We need to ensure we try
    to get and parse them correctly.
    """
    calls = []
    try:
        print(calls_block)
        print(type(calls_block))
        calls = extract_code_block(calls_block)
        print('success to extract calls')
        return calls
    except Exception as e:
        print(f'Issue in format calls: {e}')
        return calls


def extract_code_block(text):
    """
    Match block of code, assuming llm returns as markdown or code block.

    This is (I think) a better variant.
    """
    match = re.search(r"```(?:\w+)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    # Extract content from ```json ... ``` blocks if present
    if match:
        return match.group(1).strip()
    # Fall back to returning stripped text
    return text.strip()


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
