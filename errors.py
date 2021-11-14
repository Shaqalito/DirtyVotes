class GuildErrors:

    class AuthRoleAlreadyAdded(Exception):

        def __init__(self, message: str):
            self.message = message

            super().__init__(self.message)

        def __str__(self):
            return f'{self.message}'

    class AuthRoleNotInList(Exception):

        def __init__(self, message: str):
            self.message = message

            super().__init__(self.message)

        def __str__(self):
            return f'{self.message}'
