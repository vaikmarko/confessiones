from markdown_it import MarkdownIt

md = MarkdownIt()

def replace_placeholder(markdown_text: str, placeholder: str, value: str) -> str:
    """Replace the FIRST occurrence of placeholder string with value.
    Uses a simple str.replace after verifying the placeholder appears exactly.
    Returns the updated markdown if found, otherwise returns original text.
    """
    # Build variant patterns (with * or ** or _ wrappers)
    variants = [placeholder,
                f"*{placeholder}*",
                f"**{placeholder}**",
                f"_{placeholder}_",
                f"*{placeholder}*",
                f" {placeholder} "]
    safe_value = value.replace("|", "\\|").replace("\n", " ").strip()
    for var in variants:
        if var in markdown_text:
            return markdown_text.replace(var, safe_value, 1)
    return markdown_text  # no variant found 