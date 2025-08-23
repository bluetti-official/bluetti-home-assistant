from bluetti import Bluetti

class BluettiApi(Bluetti):
    """Class describing the Tesla Fleet API."""

    async def userProducts(self) -> str:
        """returns user's power station."""