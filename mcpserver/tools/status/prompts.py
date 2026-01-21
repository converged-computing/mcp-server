import mcpserver.tools.prompts as prompts

PERSONA = "You are a workflow status expert."

CONTEXT = "We just completed a step in an orchestration. We need to determine the final status. If you see a return code and it is 0, you MUST indicate success."

REQUIRES = [
    "You MUST return a single json structure with a single field 'action'",
    "The 'action' must be 'failure' or 'success'",
]


def get_status_text(content):
    return f"""
### PERSONA
{PERSONA}

### CONTEXT
{CONTEXT}

### GOAL
Look at the step output and determine if the step has failed or succeeded.
{content}

### INSTRUCTIONS
You must adhere to these rules strictly:
{prompts.format_rules(REQUIRES)}
"""
