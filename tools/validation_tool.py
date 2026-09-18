def validate_python(code: str) -> tuple[bool, str]:
    try:
        compile(code, "<generated_code>", "exec")
        return True, "Python syntax is valid."

    except SyntaxError as error:
        message = (
            f"SyntaxError at line {error.lineno}: "
            f"{error.msg}"
        )

        return False, message
