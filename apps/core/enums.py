from enum import Enum


class Roles(str, Enum):
    VIEWER = "Viewer"
    EDITOR = "Editor"

    def __str__(self) -> str: 
        return self.value


