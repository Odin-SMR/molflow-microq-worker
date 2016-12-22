def validate_project_name(project_name):
    """Must be ascii alnum and start with letter"""
    if not project_name:
        return False
    if isinstance(project_name, unicode):
        project_name = project_name.encode('utf-8')
    if not project_name[0].isalpha():
        return False
    if not project_name.isalnum():
        return False
    return True
