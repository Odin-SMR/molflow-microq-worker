def validate_project_name(project_name):
    """Must be ascii alnum and start with letter"""
    if not project_name or not isinstance(project_name, str):
        return False
    if not project_name[0].isalpha():
        return False
    if not project_name.isalnum():
        return False
    return True
